#!/usr/bin/env python3
"""BITFIN live dashboard — tailnet-only (bind to the 100.x Tailscale IP).

Serves a self-refreshing view of the paper book: equity vs benchmark, drawdown,
allocation by asset class, live-marked positions, regime gauges, and the AI
brain's decision feed. Reads state.json + journal.jsonl; no writes, no secrets.
    DASH_BIND=100.78.185.72 DASH_PORT=8787 python3 dashboard_server.py
"""
import os, sys, json, glob, time, datetime as dt
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
try:
    import live                       # live-price overlay (crypto/FX/gold trade weekends & intraday)
except Exception:
    live = None
CFG = json.load(open(os.path.join(HERE, 'config.json')))
UNIVERSE = CFG['universe']; DATA_DIR = CFG.get('data_dir', '/opt/bucket_restore')
CAPITAL = CFG.get('capital', 10000)
STATE = os.path.join(HERE, 'state.json'); JOURNAL = os.path.join(HERE, 'journal.jsonl')
BIND = os.environ.get('DASH_BIND', '100.78.185.72'); PORT = int(os.environ.get('DASH_PORT', '8787'))
CLASS = {**{t: 'Equity' for t in ['SPY','QQQ','IWM','XLK','XLV','XLF','XLE','XLI','XLP','XLU','XLY','XLB','XLRE']},
         'GLD': 'Gold', 'SLV': 'Commodity', 'USO': 'Commodity', 'CPER': 'Commodity',
         'TLT': 'Bonds', 'IEF': 'Bonds', 'HYG': 'Bonds', 'SHY': 'Bonds', 'BTC': 'Crypto'}
_cache = {'t': 0, 'p': {}, 'live_ts': None, 'live_tkrs': []}

def _closes(ds, sym):
    fs = glob.glob(f'{DATA_DIR}/{ds}/**/symbol={sym}/*.parquet', recursive=True)
    if not fs: return None
    try:
        d = pd.read_parquet(fs[0], columns=['date', 'close'])
        d['date'] = pd.to_datetime(d['date']).dt.tz_localize(None).dt.normalize()
        return d.set_index('date')['close'].astype(float).sort_index()
    except Exception: return None

def latest_prices():
    if time.time() - _cache['t'] < 45 and _cache['p']: return _cache['p']
    p = {}; live_ts = None; live_tkrs = []
    for tkr, (ds, sym) in UNIVERSE.items():
        s = _closes(ds, sym)
        if s is None or not len(s): continue
        dl_date, dl_close = s.index[-1], float(s.iloc[-1]); p[tkr] = dl_close
        if live is not None:                          # overlay a real-time mark where one exists
            try:
                ov = live.live_price(tkr, dl_date, dl_close)
            except Exception:
                ov = None
            if ov:
                p[tkr] = ov['px']                          # px==dl_close when not fresher, so harmless
                if pd.Timestamp(ov['ts']) > dl_date:       # only badge as live when genuinely newer than the close
                    live_tkrs.append(tkr)
                    if live_ts is None or ov['ts'] > live_ts: live_ts = ov['ts']
    _cache.update(t=time.time(), p=p, live_ts=live_ts, live_tkrs=sorted(live_tkrs)); return p

def tail(path, n=500):
    if not os.path.exists(path): return []
    out = []
    for ln in open(path):
        ln = ln.strip()
        if ln:
            try: out.append(json.loads(ln))
            except Exception: pass
    return out[-n:]

def build_state():
    if not os.path.exists(STATE): return {'ready': False, 'msg': 'no state yet — first cycle pending'}
    st = json.load(open(STATE)); prices = latest_prices(); eq0 = st.get('equity0', CAPITAL)
    live_ts = _cache.get('live_ts'); live_tkrs = _cache.get('live_tkrs', [])
    eq = st['cash']
    for t, pd_ in st['positions'].items(): eq += pd_['qty'] * prices.get(t, pd_['avg'])
    pos, cls = [], {}
    for t, pd_ in st['positions'].items():
        px = prices.get(t, pd_['avg']); val = pd_['qty'] * px; w = 100*val/max(eq, 1)
        c = CLASS.get(t, 'Other'); cls[c] = cls.get(c, 0) + w
        pos.append({'t': t, 'cls': c, 'qty': round(pd_['qty'], 4), 'px': round(px, 2), 'avg': round(pd_['avg'], 2),
                    'value': round(val, 2), 'weight': round(w, 1), 'pnl': round(pd_['qty']*(px-pd_['avg']), 2),
                    'upnl': round((px/pd_['avg']-1)*100, 2), 'side': 'LONG' if pd_['qty'] >= 0 else 'SHORT'})
    pos.sort(key=lambda x: -abs(x['value']))
    j = tail(JOURNAL); curve = [{'ts': r['ts'], 'eq': r['equity']} for r in j if 'equity' in r]; last = j[-1] if j else {}
    # benchmark: SPX rebased to equity0, aligned to each cycle's data date
    spx = _closes('world_indices', 'sp500_us'); bench_curve, bench_ret = [], None
    if spx is not None and j:
        def at(dstr):
            try: return float(spx.asof(pd.Timestamp(dstr)))
            except Exception: return None
        b0 = at(j[0].get('asof'))
        if b0:
            for r in j:
                bx = at(r.get('asof'))
                if bx: bench_curve.append({'ts': r['ts'], 'eq': round(eq0*bx/b0, 2)})
            bxn = at(last.get('asof'))
            if bxn: bench_ret = round((bxn/b0-1)*100, 2)
    gross = sum(abs(p['value']) for p in pos); net = sum(p['value'] for p in pos)
    cls['Cash'] = round(100*st['cash']/max(eq, 1), 1)
    ret = round((eq/eq0-1)*100, 2)
    return {'ready': True, 'sim': True, 'brand': CFG.get('name', 'BITFIN'), 'capital': eq0,
            'equity': round(eq, 2), 'equity0': eq0, 'ret_total_pct': ret,
            'bench_ret': bench_ret, 'alpha': (round(ret-bench_ret, 2) if bench_ret is not None else None),
            'cash': round(st['cash'], 2), 'cash_pct': round(100*st['cash']/max(eq, 1)),
            'gross_pct': round(gross/max(eq, 1)*100), 'net_pct': round(net/max(eq, 1)*100),
            'n_pos': len(pos), 'cycles': st.get('cycles', 0), 'positions': pos, 'curve': curve[-300:],
            'bench_curve': bench_curve[-300:], 'exposure': cls,
            'last': {'ts': last.get('ts'), 'brain': last.get('brain'), 'thesis': last.get('thesis'), 'risk': last.get('risk'),
                     'fills': last.get('fills', []), 'asof': last.get('asof'), 'breadth': last.get('breadth'),
                     'VIX': last.get('VIX'), 'HYG_vs150': last.get('HYG_vs150')},
            'feed': [{'ts': r.get('ts'), 'brain': r.get('brain'), 'eq': r.get('equity'), 'ret': r.get('ret_total_pct'),
                      'fills': r.get('fills', []), 'thesis': r.get('thesis')} for r in j[-20:]][::-1],
            'live': {'ts': live_ts, 'tickers': live_tkrs, 'n': len(live_tkrs)},
            'now': dt.datetime.utcnow().isoformat(timespec='seconds')+'Z'}

PAGE = open(os.path.join(HERE, 'dashboard.html')).read() if os.path.exists(os.path.join(HERE, 'dashboard.html')) else '<h1>missing</h1>'

class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def _send(self, code, body, ctype):
        self.send_response(code); self.send_header('Content-Type', ctype); self.send_header('Cache-Control', 'no-store'); self.end_headers()
        self.wfile.write(body if isinstance(body, bytes) else body.encode())
    def do_GET(self):
        if self.path.startswith('/api/state'):
            try: self._send(200, json.dumps(build_state()), 'application/json')
            except Exception as e: self._send(500, json.dumps({'error': str(e)}), 'application/json')
        elif self.path in ('/', '/index.html'): self._send(200, PAGE, 'text/html; charset=utf-8')
        else: self._send(404, 'not found', 'text/plain')

if __name__ == '__main__':
    print(f"BITFIN dashboard on http://{BIND}:{PORT} (tailnet-only)", flush=True)
    ThreadingHTTPServer((BIND, PORT), H).serve_forever()
