"""SEC EDGAR — keyless US company fundamentals (XBRL company facts).

Maps tickers -> CIK, then pulls the full standardized XBRL fact history for
each company (revenues, assets, EPS, shares, …) — decades of filings. One
Parquet per ticker under staging/sec_companyfacts/. SEC requires a
descriptive User-Agent (the framework sends one) and ~10 req/s max.

Set SEC_TICKERS to override the universe; default is the ticker map's top
names by market presence (first N in SEC's own list).
"""
from __future__ import annotations

import os

import pandas as pd

from ..collector import Collector, source

TICKER_MAP = "https://www.sec.gov/files/company_tickers.json"
FACTS = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"
DEFAULT_N = 500  # how many companies to walk if no explicit list


@source("sec_companyfacts", domain="fundamentals", requires_key=None)
class SecEdgar(Collector):
    rate_limit_s = 0.2  # stay well under SEC's 10 req/s

    def collect(self):
        cik_by_ticker = self._ticker_map()
        override = os.environ.get("SEC_TICKERS")
        if override:
            wanted = [t.strip().upper() for t in override.split(",")]
            targets = [(t, cik_by_ticker[t]) for t in wanted
                       if t in cik_by_ticker]
        else:
            targets = list(cik_by_ticker.items())[:DEFAULT_N]
        self.log(f"targets: {len(targets)}")
        for ticker, cik in targets:
            fp = self.root / "facts" / f"{ticker}.parquet"
            if fp.exists():
                self.stats["skip"] += 1
                continue
            try:
                data = self.get_json(FACTS.format(cik=cik), timeout=60)
                df = self._flatten(data, ticker, cik)
                if df is not None:
                    self.write("facts", df, key=ticker, overwrite=True)
                    self.log(f"{ticker}: {len(df)} facts")
            except Exception as e:  # noqa: BLE001
                self.stats["fail"] += 1
                self.log(f"FAIL {ticker}: {str(e)[:70]}")
            self.sleep()

    def _ticker_map(self) -> dict[str, int]:
        data = self.get_json(TICKER_MAP, timeout=45)
        return {row["ticker"].upper(): int(row["cik_str"])
                for row in data.values()}

    @staticmethod
    def _flatten(data, ticker, cik):
        recs = []
        for taxonomy, concepts in (data.get("facts") or {}).items():
            for concept, body in concepts.items():
                for unit, points in (body.get("units") or {}).items():
                    for p in points:
                        recs.append({
                            "ticker": ticker, "cik": cik,
                            "taxonomy": taxonomy, "concept": concept,
                            "unit": unit, "val": p.get("val"),
                            "start": p.get("start"), "end": p.get("end"),
                            "fy": p.get("fy"), "fp": p.get("fp"),
                            "form": p.get("form"), "filed": p.get("filed"),
                        })
        if not recs:
            return None
        df = pd.DataFrame(recs)
        # SEC reports some values (share counts, aggregate figures) larger than
        # int64 can hold; coerce the numeric column to float64 so the Parquet
        # write can't overflow and drop the whole company's facts.
        df["val"] = pd.to_numeric(df["val"], errors="coerce")
        return df
