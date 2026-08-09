#!/usr/bin/env python3
"""STOCKMIND live dashboard — tailnet-only (bind to the 100.x Tailscale IP).

Serves a self-refreshing view of the paper book: equity curve, live-marked
positions, cash, market regime, and the AI brain's latest decisions. Reads the
trader's state.json + journal.jsonl; no write access, no secrets.

    DASH_BIND=100.78.185.72 DASH_PORT=8787 python3 dashboard_server.py
"""
import os, json, glob, time, datetime as dt
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
CFG = json.load(open(os.path.join(HERE, 'config.json')))
UNIVERSE = CFG['universe']; DATA_DIR = CFG.get('data_dir', '/opt/bucket_restore')
STATE = os.path.join(HERE, 'state.json'); JOURNAL = os.path.join(HERE, 'journal.jsonl')
BIND = os.environ.get('DASH_BIND', '100.78.185.72'); PORT = int(os.environ.get('DASH_PORT', '8787'))
_cache = {'t': 0, 'p': {}}

def latest_prices():
    if time.time() - _cache['t'] < 45 and _cache['p']: return _cache['p']
    p = {}
    for tkr, (ds, sym) in UNIVERSE.items():
        fs = glob.glob(f'{DATA_DIR}/{ds}/**/symbol={sym}/*.parquet', recursive=True)
        if not fs: continue
        try:
            d = pd.read_parquet(fs[0], columns=['date', 'close'])
            p[tkr] = float(pd.to_numeric(d['close'], errors='coerce').dropna().iloc[-1])
        except Exception: pass
    _cache.update(t=time.time(), p=p); return p

def tail(path, n=400):
    if not os.path.exists(path): return []
    out = []
    for ln in open(path):
        ln = ln.strip()
        if ln:
            try: out.append(json.loads(ln))
            except Exception: pass
    return out[-n:]

def build_state():
    if not os.path.exists(STATE):
        return {'ready': False, 'msg': 'no state yet — first cycle pending'}
    st = json.load(open(STATE)); prices = latest_prices()
    eq = st['cash']; pos = []
    for t, pdata in st['positions'].items():
        px = prices.get(t, pdata['avg']); val = pdata['qty'] * px; eq += val
    for t, pdata in st['positions'].items():
        px = prices.get(t, pdata['avg']); val = pdata['qty'] * px
        pos.append({'t': t, 'qty': round(pdata['qty'], 3), 'px': round(px, 2),
                    'avg': round(pdata['avg'], 2), 'value': round(val, 2),
                    'weight': round(100 * val / max(eq, 1), 1),
                    'upnl': round((px / pdata['avg'] - 1) * 100, 2), 'side': 'LONG' if pdata['qty'] >= 0 else 'SHORT'})
    pos.sort(key=lambda x: -abs(x['value']))
    j = tail(JOURNAL)
    curve = [{'ts': r['ts'], 'eq': r['equity']} for r in j if 'equity' in r]
    last = j[-1] if j else {}
    return {'ready': True, 'sim': True,
            'equity': round(eq, 2), 'equity0': st.get('equity0', eq),
            'ret_total_pct': round((eq / st.get('equity0', eq) - 1) * 100, 2),
            'cash': round(st['cash'], 2), 'cash_pct': round(100 * st['cash'] / max(eq, 1)),
            'gross_pct': round(sum(abs(p['value']) for p in pos) / max(eq, 1) * 100),
            'n_pos': len(pos), 'cycles': st.get('cycles', 0),
            'positions': pos, 'curve': curve[-200:],
            'last': {'ts': last.get('ts'), 'brain': last.get('brain'), 'thesis': last.get('thesis'),
                     'risk': last.get('risk'), 'fills': last.get('fills', []), 'asof': last.get('asof'),
                     'breadth': last.get('breadth'), 'VIX': last.get('VIX'), 'HYG_vs150': last.get('HYG_vs150')},
            'feed': [{'ts': r.get('ts'), 'brain': r.get('brain'), 'eq': r.get('equity'),
                      'ret': r.get('ret_total_pct'), 'nf': len(r.get('fills', [])), 'thesis': r.get('thesis')} for r in j[-15:]][::-1],
            'now': dt.datetime.utcnow().isoformat(timespec='seconds') + 'Z'}

PAGE = open(os.path.join(HERE, 'dashboard.html')).read() if os.path.exists(os.path.join(HERE, 'dashboard.html')) else '<h1>dashboard.html missing</h1>'

class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def _send(self, code, body, ctype):
        self.send_response(code); self.send_header('Content-Type', ctype)
        self.send_header('Cache-Control', 'no-store'); self.end_headers()
        self.wfile.write(body if isinstance(body, bytes) else body.encode())
    def do_GET(self):
        if self.path.startswith('/api/state'):
            try: self._send(200, json.dumps(build_state()), 'application/json')
            except Exception as e: self._send(500, json.dumps({'error': str(e)}), 'application/json')
        elif self.path in ('/', '/index.html'):
            self._send(200, PAGE, 'text/html; charset=utf-8')
        else:
            self._send(404, 'not found', 'text/plain')

if __name__ == '__main__':
    print(f"STOCKMIND dashboard on http://{BIND}:{PORT}  (tailnet-only)", flush=True)
    ThreadingHTTPServer((BIND, PORT), H).serve_forever()
