#!/usr/bin/env python3
"""STOCKMIND — autonomous hourly paper-trader.  *** SIMULATION ONLY ***

Each cycle: read the datalake -> build a market snapshot -> ask the AI brain
(local freellmapi gateway, ~115 free models) for target weights -> rebalance a
virtual book with costs & risk caps -> journal everything. No real broker is
ever contacted; positions are virtual. Long/short allowed up to a gross cap.

Run one cycle:   python3 stockmind_trader.py --once
Loop:            python3 stockmind_trader.py --loop 3600
Config:          config.json (+ secrets.env for GATEWAY_KEY / STORJ_*)
"""
import os, sys, json, glob, time, datetime as dt, urllib.request, urllib.error
import pandas as pd

SIMULATION_ONLY = True                       # hard guard — never place real orders
HERE = os.path.dirname(os.path.abspath(__file__))

def _load_env(p):
    if os.path.exists(p):
        for ln in open(p):
            ln = ln.strip()
            if ln and not ln.startswith('#') and '=' in ln:
                k, v = ln.split('=', 1); os.environ.setdefault(k, v.strip())
_load_env(os.path.join(HERE, 'secrets.env'))

CFG      = json.load(open(os.path.join(HERE, 'config.json')))
DATA_DIR = CFG.get('data_dir', '/opt/bucket_restore')
STATE    = os.path.join(HERE, 'state.json')
JOURNAL  = os.path.join(HERE, 'journal.jsonl')
GATEWAY  = os.environ.get('GATEWAY_URL', CFG.get('gateway_url'))
GKEY     = os.environ.get('GATEWAY_KEY', '')
MODEL    = CFG.get('model', 'auto')
COST     = CFG.get('cost_bps', 5) / 1e4
MAX_GROSS= CFG.get('max_gross', 1.5)
MAX_NAME = CFG.get('max_name', 0.25)
CAPITAL  = CFG.get('capital', 100000)
UNIVERSE = CFG['universe']                   # {ticker: [dataset, symbol]}

def log(m): print(f"[{dt.datetime.utcnow().isoformat(timespec='seconds')}Z] {m}", flush=True)

# ---------------- datalake ----------------
def series(ds, sym):
    fs = glob.glob(f'{DATA_DIR}/{ds}/**/symbol={sym}/*.parquet', recursive=True)
    if not fs: return None
    d = pd.read_parquet(fs[0]); d['date'] = pd.to_datetime(d['date']).dt.tz_localize(None).dt.normalize()
    s = d.set_index('date')['close'].astype(float).sort_index()
    return s[~s.index.duplicated(keep='last')]

def _rp(s, n):
    return round((s.iloc[-1] / s.iloc[-1-n] - 1) * 100, 2) if len(s) > n else None

def snapshot():
    snap, prices, above, n, asof = {}, {}, 0, 0, None
    for tkr, (ds, sym) in UNIVERSE.items():
        s = series(ds, sym)
        if s is None or len(s) < 160: continue
        last = float(s.iloc[-1]); prices[tkr] = last; asof = s.index[-1].date()
        ma150 = s.rolling(150).mean().iloc[-1]; ma50 = s.rolling(50).mean().iloc[-1]
        snap[tkr] = {'px': round(last, 2), 'r1': _rp(s,1), 'r5': _rp(s,5), 'r20': _rp(s,20),
                     'vs50': round((last/ma50-1)*100,1), 'vs150': round((last/ma150-1)*100,1),
                     'vol20': round(s.pct_change().tail(20).std()*100,2)}
        n += 1; above += 1 if last > ma150 else 0
    ctx = {'asof': str(asof), 'universe': n, 'breadth_pct_above150': round(100*above/max(n,1))}
    vix = series('vix_complex', 'vix')
    if vix is not None: ctx['VIX'] = round(float(vix.iloc[-1]), 2)
    hyg = series('bonds_credit', 'hyg_high_yield')
    if hyg is not None:
        ctx['HYG_vs150'] = round((hyg.iloc[-1]/hyg.rolling(150).mean().iloc[-1]-1)*100, 1)
    return snap, prices, ctx

# ---------------- paper broker ----------------
def load_state():
    if os.path.exists(STATE): return json.load(open(STATE))
    return {'cash': CAPITAL, 'positions': {}, 'equity0': CAPITAL, 'cycles': 0, 'created': dt.datetime.utcnow().isoformat()}

def equity(st, prices):
    v = st['cash']
    for t, p in st['positions'].items():
        px = prices.get(t, p['avg']); v += p['qty'] * px
    return v

def rebalance(st, targets, prices):
    """targets: {ticker: weight}. Rebalance virtual book to target $ = weight*equity."""
    eq = equity(st, prices); fills = []
    # sanitize weights: clip per-name, scale to gross cap
    tw = {t: max(-MAX_NAME, min(MAX_NAME, float(w))) for t, w in targets.items() if t in prices}
    gross = sum(abs(w) for w in tw.values())
    if gross > MAX_GROSS:
        tw = {t: w*MAX_GROSS/gross for t, w in tw.items()}
    for t in list(st['positions']) + list(tw):
        if t not in prices: continue
        px = prices[t]; cur_qty = st['positions'].get(t, {}).get('qty', 0.0)
        tgt_val = tw.get(t, 0.0) * eq; tgt_qty = tgt_val / px
        dq = tgt_qty - cur_qty
        if abs(dq*px) < eq*0.005: continue                      # ignore dust (<0.5%)
        st['cash'] -= dq*px + abs(dq*px)*COST                   # pay for shares + cost
        if abs(tgt_qty) < 1e-9: st['positions'].pop(t, None)
        else: st['positions'][t] = {'qty': tgt_qty, 'avg': px}
        fills.append({'t': t, 'dqty': round(dq, 4), 'px': px, 'side': 'BUY' if dq>0 else 'SELL'})
    return fills, eq

# ---------------- AI brain ----------------
def ask_brain(snap, ctx, st, prices):
    if not GKEY: return None, 'no gateway key set'
    port = {t: round(p['qty']*prices.get(t, p['avg'])/max(equity(st,prices),1), 3) for t, p in st['positions'].items()}
    sysmsg = ("You are a disciplined systematic portfolio manager running a LONG/SHORT paper book. "
              "You receive a market snapshot and the current portfolio weights. Decide TARGET WEIGHTS for the next hour. "
              f"Rules: long positive, short negative; |per-name|<= {MAX_NAME}; sum of |weights| <= {MAX_GROSS} (rest is cash). "
              "Respect trend (prefer names above their 150d MA), manage risk when breadth is weak, VIX high, or HYG below its 150d MA. "
              "Return STRICT JSON only: {\"targets\":{\"TICKER\":weight,...},\"thesis\":\"...\",\"risk\":\"...\"}. No prose.")
    usr = json.dumps({'context': ctx, 'assets': snap, 'current_weights': port, 'tickers': list(prices)}, separators=(',',':'))
    body = json.dumps({'model': MODEL, 'temperature': 0.3, 'max_tokens': 700,
                       'messages': [{'role':'system','content':sysmsg},{'role':'user','content':usr}]}).encode()
    req = urllib.request.Request(GATEWAY.rstrip('/')+'/v1/chat/completions', data=body,
                                 headers={'Authorization': f'Bearer {GKEY}', 'Content-Type': 'application/json'})
    try:
        r = urllib.request.urlopen(req, timeout=60)
        txt = json.loads(r.read())['choices'][0]['message']['content']
        i, j = txt.find('{'), txt.rfind('}')
        dec = json.loads(txt[i:j+1])
        if 'targets' in dec and isinstance(dec['targets'], dict):
            return dec, MODEL
    except Exception as e:
        return None, f'brain error: {type(e).__name__}: {str(e)[:80]}'
    return None, 'brain returned no valid targets'

def rule_fallback(snap, ctx):
    """Trend/regime rule so the sim always acts even without the LLM."""
    risk_off = (ctx.get('breadth_pct_above150', 50) < 30) or (ctx.get('VIX', 15) > 25) or (ctx.get('HYG_vs150', 0) < 0)
    picks = {t: d['r20'] for t, d in snap.items() if d.get('vs150', -9) > 0 and (d.get('r20') or 0) > 0}
    tw = {}
    if picks:
        top = sorted(picks, key=picks.get, reverse=True)[:8]
        budget = (0.5 if risk_off else 0.9)
        s = sum(picks[t] for t in top) or 1
        for t in top: tw[t] = round(min(MAX_NAME, budget*picks[t]/s), 3)
    if 'GLD' in snap: tw['GLD'] = round(min(MAX_NAME, tw.get('GLD', 0)+ (0.2 if risk_off else 0.12)), 3)
    return {'targets': tw, 'thesis': f"rule-based ({'risk-off' if risk_off else 'risk-on'} trend-follow)", 'risk': 'fallback brain'}

# ---------------- cycle ----------------
def cycle():
    st = load_state(); snap, prices, ctx = snapshot()
    if not prices: log('no prices — datalake unreachable'); return
    eq0 = equity(st, prices)
    dec, brain = ask_brain(snap, ctx, st, prices)
    if dec is None:
        log(f"AI brain unavailable ({brain}); using rule fallback")
        dec, brain = rule_fallback(snap, ctx), 'rule-fallback'
    fills, _ = rebalance(st, dec.get('targets', {}), prices)
    st['cycles'] += 1; eq1 = equity(st, prices)
    json.dump(st, open(STATE, 'w'), indent=1)
    rec = {'ts': dt.datetime.utcnow().isoformat(timespec='seconds')+'Z', 'asof': ctx.get('asof'),
           'brain': brain, 'equity': round(eq1, 2), 'ret_total_pct': round((eq1/st['equity0']-1)*100, 2),
           'cash_pct': round(100*st['cash']/max(eq1,1)), 'n_pos': len(st['positions']),
           'breadth': ctx.get('breadth_pct_above150'), 'VIX': ctx.get('VIX'), 'HYG_vs150': ctx.get('HYG_vs150'),
           'fills': fills, 'thesis': dec.get('thesis',''), 'risk': dec.get('risk','')}
    open(JOURNAL, 'a').write(json.dumps(rec)+'\n')
    log(f"[SIM] cycle {st['cycles']} | brain={brain} | equity=${eq1:,.0f} "
        f"({rec['ret_total_pct']:+.2f}%) | {len(st['positions'])} pos | cash {rec['cash_pct']}% | "
        f"breadth {ctx.get('breadth_pct_above150')}% | fills {len(fills)}")
    log(f"       thesis: {dec.get('thesis','')[:120]}")

def main():
    assert SIMULATION_ONLY, "refusing to run: SIMULATION_ONLY is off"
    if '--loop' in sys.argv:
        iv = int(sys.argv[sys.argv.index('--loop')+1])
        log(f"STOCKMIND paper-trader loop every {iv}s — SIMULATION ONLY")
        while True:
            try: cycle()
            except Exception as e: log(f"cycle error: {type(e).__name__}: {e}")
            time.sleep(iv)
    else:
        cycle()

if __name__ == '__main__':
    main()
