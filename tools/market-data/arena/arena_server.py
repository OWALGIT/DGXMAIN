#!/usr/bin/env python3
"""BITFIN Arena web server — registration, personal book, manual trades,
leaderboard. Tailnet-bound for now; front it with nginx+TLS for bitfin.yohay.ai.
    DASH_BIND=100.78.185.72 DASH_PORT=8790 python3 arena_server.py
"""
import os, sys, json, urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import arena
BIND = os.environ.get('DASH_BIND', '100.78.185.72'); PORT = int(os.environ.get('DASH_PORT', '8790'))
PAGE = open(os.path.join(HERE, 'arena.html')).read() if os.path.exists(os.path.join(HERE, 'arena.html')) else '<h1>arena.html missing</h1>'

def book(tid):
    snap, prices, ctx = arena.snapshot()
    c = arena.db(); t = c.execute("SELECT * FROM tenants WHERE id=?", (tid,)).fetchone()
    if not t: c.close(); return {'error': 'no such tenant'}
    t = dict(t); st = json.loads(t['state']); eq = arena.equity(st, prices)
    pos = [{'t': k, 'qty': round(p['qty'], 4), 'px': round(prices.get(k, p['avg']), 2), 'avg': round(p['avg'], 2),
            'value': round(p['qty']*prices.get(k, p['avg']), 2),
            'weight': round(100*p['qty']*prices.get(k, p['avg'])/max(eq, 1), 1),
            'upnl': round((prices.get(k, p['avg'])/p['avg']-1)*100, 2)} for k, p in st['positions'].items()]
    pos.sort(key=lambda x: -abs(x['value']))
    jr = [dict(r) for r in c.execute("SELECT ts,equity,ret_pct,cycle_pnl,brain,fills,thesis,reflection FROM journal WHERE tenant_id=? ORDER BY id DESC LIMIT 20", (tid,))]
    c.close()
    return {'id': tid, 'name': t['name'], 'mode': t['mode'], 'capital': t['capital'], 'house': bool(t['is_house']),
            'equity': round(eq, 2), 'ret_pct': round((eq/st['equity0']-1)*100, 2), 'cash_pct': round(100*st['cash']/max(eq, 1)),
            'positions': pos, 'journal': jr, 'tickers': list(prices), 'asof': ctx.get('asof')}

class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def _s(self, code, body, ctype='application/json'):
        b = body if isinstance(body, bytes) else (body if isinstance(body, str) else json.dumps(body)).encode()
        self.send_response(code); self.send_header('Content-Type', ctype); self.send_header('Cache-Control', 'no-store'); self.end_headers(); self.wfile.write(b)
    def _body(self):
        n = int(self.headers.get('Content-Length', 0) or 0)
        try: return json.loads(self.rfile.read(n) or b'{}')
        except Exception: return {}
    def do_GET(self):
        u = urllib.parse.urlparse(self.path); q = urllib.parse.parse_qs(u.query)
        try:
            if u.path in ('/', '/index.html'): self._s(200, PAGE, 'text/html; charset=utf-8')
            elif u.path == '/api/leaderboard': self._s(200, arena.leaderboard())
            elif u.path == '/api/book': self._s(200, book(int(q.get('id', ['0'])[0])))
            else: self._s(404, {'error': 'not found'})
        except Exception as e: self._s(500, {'error': str(e)})
    def do_POST(self):
        b = self._body()
        try:
            if self.path == '/api/register':
                tid = arena.register(b.get('name', 'anon')[:40], float(b.get('capital', 10000)),
                                     b.get('mode', 'ai'), (b.get('base_url') or None), (b.get('api_key') or None),
                                     b.get('model', 'auto'), 0)
                self._s(200, {'id': tid})
            elif self.path == '/api/trade':
                self._s(200, arena.manual_trade(int(b['id']), {k: float(v) for k, v in b.get('targets', {}).items()}))
            elif self.path == '/api/step':
                if self.headers.get('X-Admin-Token', '') != os.environ.get('ADMIN_TOKEN', '__disabled__'):
                    self._s(403, {'error': 'admin only'})
                else:
                    self._s(200, arena.step_all())
            else: self._s(404, {'error': 'not found'})
        except Exception as e: self._s(500, {'error': str(e)})

if __name__ == '__main__':
    arena.init()
    print(f"BITFIN Arena on http://{BIND}:{PORT} (tailnet)", flush=True)
    ThreadingHTTPServer((BIND, PORT), H).serve_forever()
