#!/usr/bin/env python3
"""Live-price overlay from the twelvedata collector.

Daily bars give the reference; intraday_last.json (real-time /quote) gives the
current mark. We apply the *move* since the datalake's last close onto the
datalake price (return-scaling) — unit-agnostic, so it sidesteps the spot-gold
($4340) vs GLD-ETF ($398) mismatch. Crypto/FX/gold move 24/7; equities go live
at the US open when their intraday quote overtakes the daily bar.
"""
import glob, json, os, pandas as pd
TD = '/opt/collectors/staging/twelvedata'
# bot ticker -> twelvedata file symbol, chosen to track the SAME underlying as the datalake series
LIVE_MAP = {'BTC': 'btc_usd', 'ETH': 'eth_usd', 'GLD': 'xau_usd', 'HYG': 'hyg', 'TLT': 'tlt',
            'SPY': 'spy', 'QQQ': 'qqq', 'IWM': 'iwm', 'USO': 'uso', 'SLV': 'slv',
            'USDILS': 'usd_ils', 'USDJPY': 'usd_jpy', 'USDCNY': 'usd_cny', 'USDEUR': 'eur_usd'}
_c = {}
def _td(sym):
    if sym in _c: return _c[sym]
    fs = glob.glob(f'{TD}/td_{sym}.parquet'); s = None
    if fs:
        try:
            d = pd.read_parquet(fs[0], columns=['datetime', 'close']); d['datetime'] = pd.to_datetime(d['datetime'], errors='coerce')
            s = d.dropna().set_index('datetime')['close'].astype(float).sort_index()
            s = s[~s.index.duplicated(keep='last')]
        except Exception: s = None
    _c[sym] = s; return s

_iq = {'mt': 0, 'q': {}}
def _intraday():
    """intraday_last.json -> {td_sym: {'price','ts'(epoch)}}, re-read on mtime change."""
    p = f'{TD}/intraday_last.json'
    try: mt = os.path.getmtime(p)
    except OSError: return {}
    if mt != _iq['mt']:
        try: _iq['q'] = (json.load(open(p)) or {}).get('quotes', {}); _iq['mt'] = mt
        except Exception: _iq['q'] = {}
    return _iq['q']

def live_price(tkr, dl_last_date, dl_last_close):
    """Return {'px','ts'} live-scaled, or None if no live source for this ticker."""
    sym = LIVE_MAP.get(tkr)
    if not sym: return None
    s = _td(sym)
    if s is None or not len(s): return None
    ref = s.asof(pd.Timestamp(dl_last_date))
    if ref is None or pd.isna(ref) or ref == 0: return None
    now = float(s.iloc[-1]); nowt = s.index[-1]
    iq = _intraday().get(sym)                       # prefer the real-time quote when it's fresher
    if iq and iq.get('price') and iq.get('ts'):
        its = pd.Timestamp(int(iq['ts']), unit='s')
        if its > nowt: now = float(iq['price']); nowt = its
    return {'px': round(dl_last_close * now / ref, 4), 'ts': nowt.isoformat()}
