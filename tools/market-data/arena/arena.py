#!/usr/bin/env python3
"""BITFIN Arena — multi-tenant paper-trading simulation.  *** SIMULATION ONLY ***

Each tenant picks a starting capital and a mode:
  • manual — they place target weights themselves (via the web UI / manual_trade)
  • ai     — they bring their own OpenAI-compatible BASE_URL + KEY (cloud or local);
             every step we call THEIR model with the market snapshot to get targets
They all compete against the house algorithm (BITFIN) on a leaderboard.
Every decision, fill and P&L is logged per-tenant (the operator's analytics).

Transparency: tenants are told (in the UI/terms) that runs are logged for
analytics — no covert data collection.

CLI:  arena.py init | register ... | step | leaderboard | demo
"""
import os, sys, json, sqlite3, urllib.request, datetime as dt
HERE = os.path.dirname(os.path.abspath(__file__))
AGENT = os.environ.get('BITFIN_AGENT_DIR') or next(
    (d for d in [os.path.join(os.path.dirname(HERE), 'agent'), '/opt/quant/agent_trader', os.path.dirname(HERE)]
     if os.path.exists(os.path.join(d, 'stockmind_trader.py'))), HERE)
sys.path.insert(0, AGENT)                       # reuse the trader's datalake + book logic
from stockmind_trader import snapshot, rebalance, equity, GATEWAY, GKEY, MAX_NAME, MAX_GROSS  # noqa
DB = os.path.join(HERE, 'arena.db')
def now(): return dt.datetime.now(dt.UTC).isoformat(timespec='seconds').replace('+00:00', 'Z')

def db():
    c = sqlite3.connect(DB); c.row_factory = sqlite3.Row; return c

def init():
    c = db(); c.executescript("""
    CREATE TABLE IF NOT EXISTS tenants(
      id INTEGER PRIMARY KEY, name TEXT, capital REAL, mode TEXT,
      base_url TEXT, api_key TEXT, model TEXT, is_house INTEGER DEFAULT 0,
      state TEXT, created TEXT);
    CREATE TABLE IF NOT EXISTS journal(
      id INTEGER PRIMARY KEY, tenant_id INTEGER, ts TEXT, equity REAL,
      ret_pct REAL, cycle_pnl REAL, n_pos INTEGER, brain TEXT, fills INTEGER,
      thesis TEXT, reflection TEXT);
    """); c.commit(); c.close()

def register(name, capital, mode='ai', base_url=None, api_key=None, model='auto', is_house=0):
    st = {'cash': float(capital), 'positions': {}, 'equity0': float(capital), 'cycles': 0}
    c = db(); cur = c.execute(
        "INSERT INTO tenants(name,capital,mode,base_url,api_key,model,is_house,state,created) VALUES(?,?,?,?,?,?,?,?,?)",
        (name, float(capital), mode, base_url, api_key, model, is_house, json.dumps(st), now()))
    c.commit(); tid = cur.lastrowid; c.close(); return tid

SYS = ("You are a systematic PM on a LONG/SHORT paper book that LEARNS from its own P&L. "
       f"|per-name|<={MAX_NAME}; sum|weights|<={MAX_GROSS} (rest cash). Prefer names above 150d MA; de-risk on weak breadth/high VIX/HYG<150d MA. "
       "Avoid needless churn (5bp/trade). Return STRICT JSON only: "
       "{\"targets\":{\"TICKER\":weight},\"thesis\":\"...\",\"reflection\":\"...\",\"risk\":\"...\"}. No prose.")

def ai_decide(base_url, api_key, model, snap, ctx, book, memory):
    """Call ANY OpenAI-compatible endpoint (the tenant's own AI)."""
    usr = json.dumps({'context': ctx, 'assets': snap, 'current_weights': book, 'recent_history': memory}, separators=(',', ':'))
    body = json.dumps({'model': model or 'auto', 'temperature': 0.3, 'max_tokens': 800, 'stream': False,
                       'messages': [{'role': 'system', 'content': SYS}, {'role': 'user', 'content': usr}]}).encode()
    url = base_url.rstrip('/'); url += '' if url.endswith('/chat/completions') else '/v1/chat/completions'
    req = urllib.request.Request(url, data=body, headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'})
    try:
        raw = urllib.request.urlopen(req, timeout=90).read()
        txt = (json.loads(raw)['choices'][0]['message'].get('content') or '')
        i, j = txt.find('{'), txt.rfind('}')
        if i >= 0:
            dec = json.loads(txt[i:j+1])
            if isinstance(dec.get('targets'), dict): return dec
    except Exception as e:
        return {'error': f'{type(e).__name__}: {str(e)[:60]}'}
    return {'error': 'no valid targets'}

def _mem(tid):
    c = db(); rows = [dict(r) for r in c.execute(
        "SELECT ts,ret_pct,cycle_pnl,thesis FROM journal WHERE tenant_id=? ORDER BY id DESC LIMIT 8", (tid,))]
    c.close(); return rows[::-1]

def step_all():
    snap, prices, ctx = snapshot()
    if not prices: return {'error': 'datalake unreachable'}
    c = db(); tenants = [dict(r) for r in c.execute("SELECT * FROM tenants")]; c.close()
    stepped = 0
    for t in tenants:
        st = json.loads(t['state']); book = {k: round(p['qty']*prices.get(k, p['avg'])/max(equity(st, prices), 1), 3) for k, p in st['positions'].items()}
        if t['mode'] == 'manual':                    # manual tenants act via the UI, not the auto-step
            _log(t, st, prices, ctx, 'manual', '(waiting for manual orders)', '', []); continue
        base = t['base_url'] or GATEWAY; key = t['api_key'] or GKEY
        dec = ai_decide(base, key, t['model'], snap, ctx, book, _mem(t['id']))
        if 'targets' not in dec:                      # tenant AI failed → hold (no churn)
            _log(t, st, prices, ctx, 'AI:'+(dec.get('error', 'fail')[:20]), '(held — AI unavailable)', '', []); continue
        fills, _ = rebalance(st, dec['targets'], prices)
        t['state'] = json.dumps(st)
        _log(t, st, prices, ctx, ('house' if t['is_house'] else 'AI'), dec.get('thesis', ''), dec.get('reflection', ''), fills)
        c = db(); c.execute("UPDATE tenants SET state=? WHERE id=?", (t['state'], t['id'])); c.commit(); c.close()
        stepped += 1
    return {'stepped': stepped, 'asof': ctx.get('asof'), 'ts': now()}

def _log(t, st, prices, ctx, brain, thesis, reflection, fills):
    eq = equity(st, prices)
    c = db(); prev = c.execute("SELECT equity FROM journal WHERE tenant_id=? ORDER BY id DESC LIMIT 1", (t['id'],)).fetchone()
    prev_eq = prev['equity'] if prev else st['equity0']
    c.execute("INSERT INTO journal(tenant_id,ts,equity,ret_pct,cycle_pnl,n_pos,brain,fills,thesis,reflection) VALUES(?,?,?,?,?,?,?,?,?,?)",
              (t['id'], now(), round(eq, 2), round((eq/st['equity0']-1)*100, 2), round(eq-prev_eq, 2),
               len(st['positions']), brain, len(fills), thesis[:400], reflection[:400]))
    c.commit(); c.close()

def manual_trade(tenant_id, targets):
    snap, prices, ctx = snapshot(); c = db(); t = dict(c.execute("SELECT * FROM tenants WHERE id=?", (tenant_id,)).fetchone()); c.close()
    st = json.loads(t['state']); fills, _ = rebalance(st, targets, prices); t['state'] = json.dumps(st)
    c = db(); c.execute("UPDATE tenants SET state=? WHERE id=?", (t['state'], tenant_id)); c.commit(); c.close()
    _log(t, st, prices, ctx, 'manual', 'manual order', '', fills); return {'fills': len(fills)}

def leaderboard():
    snap, prices, ctx = snapshot(); c = db(); rows = [dict(r) for r in c.execute("SELECT * FROM tenants")]; c.close()
    lb = []
    for t in rows:
        st = json.loads(t['state']); eq = equity(st, prices)
        lb.append({'id': t['id'], 'name': t['name'], 'mode': t['mode'], 'house': bool(t['is_house']),
                   'capital': t['capital'], 'equity': round(eq, 2), 'ret_pct': round((eq/st['equity0']-1)*100, 2),
                   'n_pos': len(st['positions']), 'cash_pct': round(100*st['cash']/max(eq, 1))})
    lb.sort(key=lambda x: -x['ret_pct'])
    return {'asof': ctx.get('asof'), 'leaderboard': lb}

if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'leaderboard'
    if cmd == 'init': init(); print('arena.db ready')
    elif cmd == 'step': print(json.dumps(step_all()))
    elif cmd == 'leaderboard': print(json.dumps(leaderboard(), indent=1))
    elif cmd == 'register':
        print('tenant', register(*sys.argv[2:]))
    else: print('usage: init | register <name> <capital> <mode> [base_url] [key] [model] | step | leaderboard')
