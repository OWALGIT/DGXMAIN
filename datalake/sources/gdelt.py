"""GDELT 2.0 — keyless global news volume & tone per theme.

The GDELT Doc API returns a daily timeline of coverage volume and average
tone for any query — geopolitics, conflict, specific tickers, macro fear.
A broad, free news-sentiment/geopolitics feed. One Parquet per theme under
staging/gdelt_tone/.
"""
from __future__ import annotations

import os

import pandas as pd

from ..collector import Collector, source

API = ("https://api.gdeltproject.org/api/v2/doc/doc?query={q}"
       "&mode=timelinevolinfo&timespan=60m&format=json")
# use a long timespan for history
API_HIST = ("https://api.gdeltproject.org/api/v2/doc/doc?query={q}"
            "&mode=timelinevol&STARTDATETIME=20170101000000&format=json")

DEFAULT_THEMES = {
    "recession": "recession",
    "inflation": "inflation",
    "rate_hike": "interest rate hike",
    "geopolitics_war": "war conflict",
    "red_sea": "Red Sea shipping",
    "oil_shock": "oil price shock",
    "bank_crisis": "bank crisis",
    "china_economy": "China economy",
}


@source("gdelt_tone", domain="geopolitics", requires_key=None)
class Gdelt(Collector):
    rate_limit_s = 1.0  # GDELT is sensitive to hammering

    def collect(self):
        override = os.environ.get("GDELT_THEMES")
        themes = (dict(kv.split("=", 1) for kv in override.split(";") if "=" in kv)
                  if override else DEFAULT_THEMES)
        for name, query in themes.items():
            try:
                q = query.replace(" ", "%20")
                data = self.get_json(API_HIST.format(q=q), timeout=60)
                series = (data.get("timeline") or [{}])[0].get("data", [])
                if not series:
                    self.stats["fail"] += 1
                    self.log(f"empty {name}")
                    continue
                df = pd.DataFrame(series)
                df["theme"] = name
                df["query"] = query
                if "date" in df.columns:
                    df["date"] = pd.to_datetime(df["date"], errors="coerce")
                self.write("timeline", df, key=name, overwrite=True)
                self.log(f"{name}: {len(df)} points")
            except Exception as e:  # noqa: BLE001
                self.stats["fail"] += 1
                self.log(f"FAIL {name}: {str(e)[:70]}")
            self.sleep()
