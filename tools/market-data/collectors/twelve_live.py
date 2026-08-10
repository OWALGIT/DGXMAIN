#!/usr/bin/env python3
"""Intraday real-time quotes from twelvedata (basic plan: 800/day, 8/min).

Runs on DGXSEC as `/opt/collectors/twelve_live.py` (cron: */20 * * * *). Chunked
/quote calls (<=6 symbols, spaced 65s) respect the 8/min cap. Writes
intraday_last.json, which the dashboard's live.py prefers when a quote is fresher
than the daily bar — so crypto/FX/gold move 24/7 and equities go live at the US
open. Deploy: copy to /opt/collectors/ on DGXSEC.
"""
import json, time, urllib.request, urllib.parse, pathlib
E = dict(l.strip().split("=", 1) for l in open("/opt/collectors/.env") if "=" in l and not l.startswith("#"))
K = E["TWELVEDATA_API_KEY"]
D = pathlib.Path("/opt/collectors/staging/twelvedata"); D.mkdir(parents=True, exist_ok=True)
OUT = D / "intraday_last.json"
# td file-symbol -> twelvedata quote symbol (only what the book overlay uses)
SYMS = {"spy": "SPY", "qqq": "QQQ", "iwm": "IWM", "hyg": "HYG", "tlt": "TLT",
        "slv": "SLV", "uso": "USO", "btc_usd": "BTC/USD", "xau_usd": "XAU/USD"}
UA = {"User-Agent": "Mozilla/5.0"}
CHUNK, GAP = 6, 65   # <=6 credits/min, spaced past the rolling minute window

def fetch(syms):
    url = "https://api.twelvedata.com/quote?" + urllib.parse.urlencode({"symbol": ",".join(syms), "apikey": K})
    for attempt in (1, 2):
        try:
            j = json.load(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60))
            if "symbol" in j: j = {j["symbol"]: j}
            return j
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt == 1: time.sleep(GAP); continue
            raise
    return {}

items = list(SYMS.items())
out, prev = {}, None
for i in range(0, len(items), CHUNK):
    if prev is not None: time.sleep(GAP)
    chunk = items[i:i + CHUNK]; prev = chunk
    j = fetch([sym for _, sym in chunk])
    for fn, sym in chunk:
        q = j.get(sym) or {}
        px = q.get("close"); ts = q.get("last_quote_at") or q.get("timestamp")
        if px:
            try: out[fn] = {"price": float(px), "ts": int(ts) if ts else None, "open": bool(q.get("is_market_open"))}
            except Exception: pass
if out:
    tmp = str(OUT) + ".tmp"
    json.dump({"asof": int(time.time()), "quotes": out}, open(tmp, "w"))
    pathlib.Path(tmp).replace(OUT)
print("LIVE wrote %d/%d quotes" % (len(out), len(SYMS)), flush=True)
