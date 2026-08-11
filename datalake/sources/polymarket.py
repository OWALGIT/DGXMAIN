"""Polymarket — keyless prediction-market odds (crowd probability / betting).

The Gamma API exposes every market with its outcome prices — the crowd's
money-weighted probability on elections, macro prints, rate decisions, wars,
crypto levels. This is the "הימורים / crowd psychology" layer: what people
actually bet, not what they say. Paged 500 at a time into
staging/polymarket/markets/.
"""
from __future__ import annotations

import pandas as pd

from ..collector import Collector, source

GAMMA = "https://gamma-api.polymarket.com/markets?limit={limit}&offset={offset}"


@source("polymarket", domain="prediction_markets", requires_key=None)
class Polymarket(Collector):
    rate_limit_s = 0.4

    def collect(self):
        limit, offset, page = 500, 0, 0
        while True:
            try:
                batch = self.get_json(
                    GAMMA.format(limit=limit, offset=offset), timeout=45)
            except Exception as e:  # noqa: BLE001
                self.stats["fail"] += 1
                self.log(f"FAIL offset={offset}: {str(e)[:70]}")
                break
            if not batch:
                break
            df = pd.json_normalize(batch)
            self.write("markets", df, key=f"page_{page:04d}", overwrite=True)
            self.log(f"page {page}: {len(df)} markets (offset {offset})")
            if len(batch) < limit:
                break
            offset += limit
            page += 1
            self.sleep()
