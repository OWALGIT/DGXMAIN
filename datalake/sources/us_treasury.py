"""US Treasury — keyless daily par yield curve (the risk-free backbone).

Pulls the official daily treasury par yield curve CSV per year from
home.treasury.gov. One Parquet per year under staging/us_treasury_yield/.
Rates drive discounting, the VRP work, and every macro model downstream.
"""
from __future__ import annotations

import datetime as dt
import io

import pandas as pd

from ..collector import Collector, source

BASE = ("https://home.treasury.gov/resource-center/data-chart-center/"
        "interest-rates/daily-treasury-rates.csv/{year}/all"
        "?type=daily_treasury_yield_curve&field_tdr_date_value={year}"
        "&page&_format=csv")
FIRST_YEAR = 1990


@source("us_treasury_yield", domain="rates", requires_key=None)
class Treasury(Collector):
    rate_limit_s = 0.5

    def collect(self):
        this_year = _this_year()
        for year in range(FIRST_YEAR, this_year + 1):
            # re-pull only the current year on reruns; past years are final
            overwrite = year == this_year
            dest = self.root / "curve" / f"{year}.parquet"
            if dest.exists() and not overwrite:
                self.stats["skip"] += 1
                continue
            try:
                raw = self._get(BASE.format(year=year), timeout=45)
                df = pd.read_csv(io.BytesIO(raw))
                if df.empty or "Date" not in df.columns:
                    self.stats["fail"] += 1
                    continue
                df["Date"] = pd.to_datetime(df["Date"])
                df["year"] = year
                self.write("curve", df, key=str(year), overwrite=True)
                self.log(f"{year}: {len(df)} days")
            except Exception as e:  # noqa: BLE001
                self.stats["fail"] += 1
                self.log(f"FAIL {year}: {str(e)[:70]}")
            self.sleep()


def _this_year() -> int:
    # Date.now() is fine here (server runtime, not a workflow script).
    return dt.datetime.utcnow().year
