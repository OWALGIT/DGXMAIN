#!/usr/bin/env python3
"""Live-price overlay from the twelvedata collector (crypto/FX/gold trade on
weekends and intraday). To avoid unit mismatches (the book prices GLD as spot
gold ~$4340, not the GLD ETF ~$398), we apply the twelvedata *move* since the
datalake's last close onto the datalake price — unit-agnostic and always correct.
"""
import glob, pandas as pd
TD = '/opt/collectors/staging/twelvedata'
# bot ticker -> twelvedata file symbol, chosen to track the SAME underlying as the datalake series
LIVE_MAP = {'BTC': 'btc_usd', 'ETH': 'eth_usd', 'GLD': 'xau_usd', 'HYG': 'hyg', 'TLT': 'tlt',
            'SPY': 'spy', 'QQQ': 'qqq', 'IWM': 'iwm', 'USO': 'uso', 'SLV': 'slv',
            'USDILS': 'usd_ils', 'USDJPY': 'usd_jpy', 'USDCNY': 'usd_cny', 'USDEUR': 'eur_usd'}
_c = {}
def _td(sym):
    if sym in _c: return _c[sym]
    fs = glob.glob(f'{TD}/td_{sym}.parquet')
    s = None
    if fs:
        try:
            d = pd.read_parquet(fs[0], columns=['datetime', 'close']); d['datetime'] = pd.to_datetime(d['datetime'], errors='coerce')
            s = d.dropna().set_index('datetime')['close'].astype(float).sort_index()
            s = s[~s.index.duplicated(keep='last')]
        except Exception: s = None
    _c[sym] = s; return s

def live_price(tkr, dl_last_date, dl_last_close):
    """Return {'px','ts'} live-scaled, or None if no live source for this ticker."""
    sym = LIVE_MAP.get(tkr)
    if not sym: return None
    s = _td(sym)
    if s is None or not len(s): return None
    ref = s.asof(pd.Timestamp(dl_last_date))
    if ref is None or pd.isna(ref) or ref == 0: return None
    now = float(s.iloc[-1]); nowt = s.index[-1]
    return {'px': round(dl_last_close * now / ref, 4), 'ts': nowt.isoformat()}
