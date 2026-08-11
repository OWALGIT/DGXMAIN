"""Stooq — free, keyless global end-of-day history.

Covers US/EU/Asia equities, indices, FX and commodities as daily OHLCV back
to inception. One Parquet per symbol under staging/stooq/<group>/.
Universe is a broad default; extend DEFAULT_UNIVERSE or set STOOQ_SYMBOLS
(comma-separated) to pull more.
"""
from __future__ import annotations

import io
import os

import pandas as pd

from ..collector import Collector, source

# group -> list of stooq symbols. Stooq suffixes: .us equities, ^ indices,
# fx pairs as e.g. eurusd, commodities as e.g. cl.f (crude), gc.f (gold).
DEFAULT_UNIVERSE = {
    "index": ["^spx", "^ndx", "^dji", "^vix", "^rut", "^ftse", "^dax",
              "^nkx", "^hsi", "^ta125"],
    "fx": ["eurusd", "usdjpy", "gbpusd", "usdils", "usdchf", "usdcny",
           "audusd", "usdcad"],
    "commodity": ["cl.f", "gc.f", "si.f", "ng.f", "hg.f", "zc.f", "zw.f",
                  "zs.f"],
    "mega_cap_us": ["aapl.us", "msft.us", "nvda.us", "amzn.us", "googl.us",
                    "meta.us", "tsla.us", "brk-b.us", "jpm.us", "xom.us"],
}


@source("stooq", domain="market", requires_key=None)
class Stooq(Collector):
    rate_limit_s = 0.4

    def universe(self):
        override = os.environ.get("STOOQ_SYMBOLS")
        if override:
            return {"custom": [s.strip() for s in override.split(",") if s.strip()]}
        return DEFAULT_UNIVERSE

    def collect(self):
        for group, symbols in self.universe().items():
            for sym in symbols:
                try:
                    raw = self._get(
                        f"https://stooq.com/q/d/l/?s={sym}&i=d", timeout=45)
                    df = pd.read_csv(io.BytesIO(raw))
                    if df.empty or "Date" not in df.columns:
                        self.stats["fail"] += 1
                        self.log(f"empty {sym}")
                        continue
                    df.columns = [c.lower() for c in df.columns]
                    df["symbol"] = sym
                    df["group"] = group
                    self.write(group, df, key=sym, overwrite=True)
                    self.log(f"{group}/{sym}: {len(df)} rows")
                except Exception as e:  # noqa: BLE001
                    self.stats["fail"] += 1
                    self.log(f"FAIL {sym}: {str(e)[:70]}")
                self.sleep()
