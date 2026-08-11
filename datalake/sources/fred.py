"""FRED — St. Louis Fed macro series (key-based).

The canonical macro backbone: GDP, CPI, unemployment, fed funds, yield
spreads, financial-conditions indices, money supply. Needs a free
FRED_API_KEY (in /opt/collectors/.env). One Parquet per series under
staging/fred/. Extend DEFAULT_SERIES or set FRED_SERIES (comma-separated).
"""
from __future__ import annotations

import os

import pandas as pd

from ..collector import Collector, source

OBS = ("https://api.stlouisfed.org/fred/series/observations"
       "?series_id={sid}&api_key={key}&file_type=json&observation_start=1900-01-01")

DEFAULT_SERIES = [
    "GDP", "GDPC1", "CPIAUCSL", "CPILFESL", "UNRATE", "PAYEMS",
    "FEDFUNDS", "DFF", "DGS10", "DGS2", "T10Y2Y", "T10Y3M",
    "BAMLH0A0HYM2", "NFCI", "M2SL", "WALCL", "DTWEXBGS", "VIXCLS",
    "UMCSENT", "INDPRO", "HOUST", "RSAFS", "PCEPI", "DCOILWTICO",
]


@source("fred", domain="macro", requires_key="FRED_API_KEY")
class Fred(Collector):
    rate_limit_s = 0.4

    def collect(self):
        key = self.key()
        override = os.environ.get("FRED_SERIES")
        series = ([s.strip() for s in override.split(",")] if override
                  else DEFAULT_SERIES)
        for sid in series:
            try:
                data = self.get_json(OBS.format(sid=sid, key=key), timeout=45)
                obs = data.get("observations", [])
                if not obs:
                    self.stats["fail"] += 1
                    continue
                df = pd.DataFrame(obs)
                df["date"] = pd.to_datetime(df["date"])
                df["value"] = pd.to_numeric(df["value"], errors="coerce")
                df["series_id"] = sid
                self.write("series", df, key=sid, overwrite=True)
                self.log(f"{sid}: {len(df)} obs")
            except Exception as e:  # noqa: BLE001
                self.stats["fail"] += 1
                self.log(f"FAIL {sid}: {str(e)[:70]}")
            self.sleep()
