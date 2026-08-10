#!/usr/bin/env python3
"""Nightly refresh of the twelvedata DAILY bars for the symbols the BITFIN book
marks live.

Runs on DGXSEC as `/opt/collectors/twelve_refresh.py` (cron: 20 23 * * *). The
original twelve2.py was a one-shot backfill (skip-if-exists), so the daily bars
went stale; this re-fetches them so live.py's return-scaling *reference* tracks
the datalake as it advances. ~14 credits/night. Deploy: copy to /opt/collectors/.
"""
import json, time, urllib.request, urllib.parse, pathlib
import pandas as pd
E = dict(l.strip().split("=", 1) for l in open("/opt/collectors/.env") if "=" in l and not l.startswith("#"))
K = E["TWELVEDATA_API_KEY"]
D = pathlib.Path("/opt/collectors/staging/twelvedata"); D.mkdir(parents=True, exist_ok=True)
UA = {"User-Agent": "Mozilla/5.0"}
SYMS = ["BTC/USD", "ETH/USD", "XAU/USD", "HYG", "TLT", "SPY", "QQQ", "IWM",
        "USO", "SLV", "USD/ILS", "USD/JPY", "USD/CNY", "EUR/USD"]
ok = 0
for s in SYMS:
    fn = "td_%s" % s.replace("/", "_").lower()
    try:
        p = {"symbol": s, "interval": "1day", "outputsize": "5000", "apikey": K}
        j = json.load(urllib.request.urlopen(urllib.request.Request(
            "https://api.twelvedata.com/time_series?" + urllib.parse.urlencode(p), headers=UA), timeout=90))
        v = j.get("values")
        if v:
            df = pd.DataFrame(v); df["symbol"] = s
            m = j.get("meta", {}); df["exchange"] = m.get("exchange"); df["type"] = m.get("type")
            df.astype(str).to_parquet(D / (fn + ".parquet"), index=False); ok += 1
        else:
            print("  -- %-10s %s" % (s, str(j.get("message", ""))[:40]), flush=True)
    except Exception as e:
        print("  -- %-10s %s" % (s, str(e)[:40]), flush=True)
    time.sleep(8.5)
print("REFRESH ok=%d/%d" % (ok, len(SYMS)), flush=True)
