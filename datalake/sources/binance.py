"""Binance — free, keyless deep crypto OHLCV (klines).

Daily candles back to each pair's listing, paged 1000 at a time. One Parquet
per symbol under staging/binance_klines/. Set BINANCE_SYMBOLS to override the
default universe; BINANCE_INTERVAL (default 1d) to change granularity.
"""
from __future__ import annotations

import os

import pandas as pd

from ..collector import Collector, source

DEFAULT_SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT", "ADAUSDT",
    "DOGEUSDT", "AVAXUSDT", "LINKUSDT", "MATICUSDT", "DOTUSDT", "LTCUSDT",
]
COLS = ["open_time", "open", "high", "low", "close", "volume", "close_time",
        "quote_volume", "trades", "taker_buy_base", "taker_buy_quote", "ignore"]


@source("binance_klines", domain="crypto", requires_key=None)
class Binance(Collector):
    rate_limit_s = 0.3

    def collect(self):
        interval = os.environ.get("BINANCE_INTERVAL", "1d")
        override = os.environ.get("BINANCE_SYMBOLS")
        symbols = ([s.strip() for s in override.split(",")] if override
                   else DEFAULT_SYMBOLS)
        for sym in symbols:
            try:
                rows, start = [], 0
                while True:
                    batch = self.get_json(
                        "https://api.binance.com/api/v3/klines"
                        f"?symbol={sym}&interval={interval}"
                        f"&startTime={start}&limit=1000", timeout=45)
                    if not batch:
                        break
                    rows.extend(batch)
                    start = batch[-1][6] + 1  # next after last close_time
                    if len(batch) < 1000:
                        break
                    self.sleep()
                if not rows:
                    self.stats["fail"] += 1
                    self.log(f"empty {sym}")
                    continue
                df = pd.DataFrame(rows, columns=COLS)
                df["symbol"] = sym
                df["date"] = pd.to_datetime(df["open_time"], unit="ms")
                for c in ("open", "high", "low", "close", "volume",
                          "quote_volume"):
                    df[c] = df[c].astype(float)
                self.write(interval, df, key=sym, overwrite=True)
                self.log(f"{sym}: {len(df)} candles")
            except Exception as e:  # noqa: BLE001
                self.stats["fail"] += 1
                self.log(f"FAIL {sym}: {str(e)[:70]}")
            self.sleep()
