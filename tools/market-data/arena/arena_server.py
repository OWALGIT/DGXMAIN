#!/usr/bin/env python3
"""BITFIN Arena web server — accounts, sessions, encrypted keys, rate-limits,
per-user books, leaderboard, and an admin panel. Behind Cloudflare Tunnel.
"""
import os, sys, json, urllib.parse, http.cookies
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import arena, auth, learn
BIND = os.environ.get('DASH_BIND', '100.78.185.72'); PORT = int(os.environ.get('DASH_PORT', '8790'))
PAGE = open(os.path.join(HERE, 'arena.html')).read() if os.path.exists(os.path.join(HERE, 'arena.html')) else '<h1>arena.html missing</h1>'
PAGE_LEARN = open(os.path.join(HERE, 'learn.html')).read() if os.path.exists(os.path.join(HERE, 'learn.html')) else '<h1>learn.html missing</h1>'

def book(tid):
    snap, prices, ctx = arena.snapshot()
    c = arena.db(); t = c.execute("SELECT * FROM tenants WHERE id=?", (tid,)).fetchone()
    if not t: c.close(); return {'error': 'no such tenant'}
    t = dict(t); st = json.loads(t['state']); eq = arena.equity(st, prices)
    pos = [{'t': k, 'qty': round(p['qty'], 4), 'px': round(prices.get(k, p['avg']), 2), 'avg': round(p['avg'], 2),
            'value': round(p['qty']*prices.get(k, p['avg']), 2), 'weight': round(100*p['qty']*prices.get(k, p['avg'])/max(eq, 1), 1),
            'upnl': round((prices.get(k, p['avg'])/p['avg']-1)*100, 2)} for k, p in st['positions'].items()]
    pos.sort(key=lambda x: -abs(x['value']))
    jr = [dict(r) for r in c.execute("SELECT ts,equity,ret_pct,cycle_pnl,brain,fills,thesis,reflection FROM journal WHERE tenant_id=? ORDER BY id DESC LIMIT 20", (tid,))]
    c.close()  # NOTE: never expose api_key
    return {'id': tid, 'name': t['name'], 'mode': t['mode'], 'capital': t['capital'], 'house': bool(t['is_house']),
            'equity': round(eq, 2), 'ret_pct': round((eq/st['equity0']-1)*100, 2), 'cash_pct': round(100*st['cash']/max(eq, 1)),
            'positions': pos, 'journal': jr, 'tickers': list(prices), 'asof': ctx.get('asof')}

def my_tenant(uid):
    c = arena.db(); r = c.execute("SELECT id FROM tenants WHERE user_id=? ORDER BY id DESC LIMIT 1", (uid,)).fetchone(); c.close()
    return r['id'] if r else None

class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def _s(self, code, body, ctype='application/json', cookie=None):
        b = body if isinstance(body, bytes) else (body if isinstance(body, str) else json.dumps(body)).encode()
        self.send_response(code); self.send_header('Content-Type', ctype); self.send_header('Cache-Control', 'no-store')
        if cookie: self.send_header('Set-Cookie', cookie)
        self.end_headers(); self.wfile.write(b)
    def _body(self):
        n = int(self.headers.get('Content-Length', 0) or 0)
        try: return json.loads(self.rfile.read(n) or b'{}')
        except Exception: return {}
    def _ip(self):
        return self.headers.get('CF-Connecting-IP') or self.headers.get('X-Forwarded-For', '').split(',')[0].strip() or self.client_address[0]
    def _sid(self):
        c = http.cookies.SimpleCookie(self.headers.get('Cookie', '')); return c['sid'].value if 'sid' in c else None
    def _user(self): return auth.user_by_session(self._sid())
    def _cookie(self, tok):
        return f'sid={tok}; HttpOnly; Path=/; Max-Age={7*86400}; SameSite=Lax; Secure'

    def do_GET(self):
        u = urllib.parse.urlparse(self.path); q = urllib.parse.parse_qs(u.query)
        try:
            if u.path in ('/', '/index.html'): self._s(200, PAGE, 'text/html; charset=utf-8')
            elif u.path == '/api/leaderboard': self._s(200, arena.leaderboard())
            elif u.path == '/api/book': self._s(200, book(int(q.get('id', ['0'])[0])))
            elif u.path == '/learn':
                if not self._user(): self.send_response(302); self.send_header('Location', '/'); self.end_headers()
                else: self._s(200, PAGE_LEARN, 'text/html; charset=utf-8')
            elif u.path == '/api/catalog':
                if not self._user(): self._s(401, {'error': 'log in first'})
                else: self._s(200, learn.catalog())
            elif u.path == '/api/series':
                if not self._user(): self._s(401, {'error': 'log in first'})
                else:
                    ds = q.get('dataset', [''])[0]; sym = q.get('symbol', [''])[0]
                    self._s(200, (learn._series(ds, sym) or {'error': 'no data'}) if sym else {'symbols': learn.symbols(ds)})
            elif u.path == '/api/me':
                usr = self._user()
                self._s(200, {'user': ({'email': usr['email'], 'role': usr['role'], 'tenant_id': my_tenant(usr['id'])} if usr else None)})
            elif u.path == '/api/admin/users':
                usr = self._user()
                if not usr or usr['role'] != 'admin': self._s(403, {'error': 'admin only'})
                else: self._s(200, {'users': auth.list_users()})
            else: self._s(404, {'error': 'not found'})
        except Exception as e: self._s(500, {'error': str(e)})

    def do_POST(self):
        b = self._body(); ip = self._ip()
        try:
            if self.path == '/api/signup':
                if not auth.rate_ok('auth:'+ip, 10, 300): return self._s(429, {'error': 'too many attempts, wait a few minutes'})
                uid, err = auth.signup(b.get('email'), b.get('password'))
                if err: return self._s(400, {'error': err})
                self._s(200, {'ok': True}, cookie=self._cookie(auth.new_session(uid)))
            elif self.path == '/api/login':
                if not auth.rate_ok('auth:'+ip, 10, 300): return self._s(429, {'error': 'too many attempts, wait a few minutes'})
                uid = auth.login(b.get('email'), b.get('password'))
                if not uid: return self._s(401, {'error': 'wrong email or password'})
                self._s(200, {'ok': True}, cookie=self._cookie(auth.new_session(uid)))
            elif self.path == '/api/logout':
                if self._sid(): auth.logout(self._sid())
                self._s(200, {'ok': True}, cookie='sid=; Path=/; Max-Age=0')
            elif self.path == '/api/register':
                usr = self._user()
                if not usr: return self._s(401, {'error': 'log in first'})
                if not auth.rate_ok('act:'+str(usr['id']), 20, 60): return self._s(429, {'error': 'slow down'})
                c = arena.db(); c.execute("DELETE FROM tenants WHERE user_id=?", (usr['id'],)); c.commit(); c.close()  # one book per user
                tid = arena.register(b.get('name', usr['email'].split('@')[0])[:40], float(b.get('capital', 10000)),
                                     b.get('mode', 'ai'), (b.get('base_url') or None), (b.get('api_key') or None),
                                     b.get('model', 'auto'), 0, usr['id'])
                self._s(200, {'id': tid})
            elif self.path == '/api/trade':
                usr = self._user()
                if not usr: return self._s(401, {'error': 'log in first'})
                if not auth.rate_ok('act:'+str(usr['id']), 20, 60): return self._s(429, {'error': 'slow down'})
                tid = int(b['id'])
                c = arena.db(); own = c.execute("SELECT 1 FROM tenants WHERE id=? AND user_id=?", (tid, usr['id'])).fetchone(); c.close()
                if not own: return self._s(403, {'error': 'not your book'})
                self._s(200, arena.manual_trade(tid, {k: float(v) for k, v in b.get('targets', {}).items()}))
            elif self.path == '/api/admin/user':
                usr = self._user()
                if not usr or usr['role'] != 'admin': return self._s(403, {'error': 'admin only'})
                auth.set_disabled(int(b['id']), bool(b.get('disabled'))); self._s(200, {'ok': True})
            elif self.path == '/api/explain':
                if not self._user(): return self._s(401, {'error': 'log in first'})
                if not auth.rate_ok('explain:'+ip, 20, 300): return self._s(429, {'error': 'slow down — too many questions'})
                self._s(200, learn.explain((b.get('question') or '')[:400]))
            elif self.path == '/api/step':
                usr = self._user()
                if (usr and usr['role'] == 'admin') or self.headers.get('X-Admin-Token', '') == os.environ.get('ADMIN_TOKEN', '__disabled__'):
                    self._s(200, arena.step_all())
                else: self._s(403, {'error': 'admin only'})
            else: self._s(404, {'error': 'not found'})
        except Exception as e: self._s(500, {'error': str(e)})

if __name__ == '__main__':
    arena.init()
    print(f"BITFIN Arena http://{BIND}:{PORT} (behind Cloudflare Tunnel)", flush=True)
    ThreadingHTTPServer((BIND, PORT), H).serve_forever()
