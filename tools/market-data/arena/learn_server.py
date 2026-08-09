#!/usr/bin/env python3
"""BITFIN Academy — PRIVATE server. Bound to the Tailscale IP only (no tunnel,
no public URL). Only reachable from the 100.x tailnet — the operator's own tool.
Uses the house gateway key, so it is NOT exposed to signed-up customers.
    DASH_BIND=100.78.185.72 DASH_PORT=8791 python3 learn_server.py
"""
import os, sys, json, urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import learn
BIND = os.environ.get('DASH_BIND', '100.78.185.72'); PORT = int(os.environ.get('DASH_PORT', '8791'))
PAGE = open(os.path.join(HERE, 'learn.html')).read() if os.path.exists(os.path.join(HERE, 'learn.html')) else '<h1>learn.html missing</h1>'

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
            if u.path in ('/', '/learn', '/index.html'): self._s(200, PAGE, 'text/html; charset=utf-8')
            elif u.path == '/api/catalog': self._s(200, learn.catalog())
            elif u.path == '/api/series':
                ds = q.get('dataset', [''])[0]; sym = q.get('symbol', [''])[0]
                self._s(200, (learn._series(ds, sym) or {'error': 'no data'}) if sym else {'symbols': learn.symbols(ds)})
            else: self._s(404, {'error': 'not found'})
        except Exception as e: self._s(500, {'error': str(e)})
    def do_POST(self):
        try:
            if self.path == '/api/explain':
                self._s(200, learn.explain((self._body().get('question') or '')[:400]))
            else: self._s(404, {'error': 'not found'})
        except Exception as e: self._s(500, {'error': str(e)})

if __name__ == '__main__':
    print(f"BITFIN Academy (PRIVATE) http://{BIND}:{PORT} — tailnet only", flush=True)
    ThreadingHTTPServer((BIND, PORT), H).serve_forever()
