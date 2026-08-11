"""Wikipedia pageviews — keyless proxy for human attention.

Daily pageviews per article from the Wikimedia REST API. Attention on
tickers, macro terms, fear/greed words and event pages is a leading,
crowd-psychology signal (the "נפש האדם" layer). One Parquet per article
under staging/attention_wikipedia_pv/.
"""
from __future__ import annotations

import datetime as dt
import os

import pandas as pd

from ..collector import Collector, source

API = ("https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/"
       "en.wikipedia/all-access/all-agents/{article}/daily/{start}/{end}")

DEFAULT_ARTICLES = [
    "Stock_market", "Recession", "Inflation", "Federal_Reserve",
    "Bitcoin", "Ethereum", "S%26P_500", "Gold_as_an_investment",
    "Stock_market_crash", "Bear_market", "Bull_market", "Volatility_(finance)",
    "Gambling", "Sports_betting", "Cryptocurrency", "Interest_rate",
    "Nvidia", "Tesla,_Inc.", "OpenAI", "Artificial_intelligence",
]


@source("attention_wikipedia_pv", domain="attention", requires_key=None)
class WikiPageviews(Collector):
    rate_limit_s = 0.3

    def collect(self):
        start = "20150701"
        end = dt.datetime.utcnow().strftime("%Y%m%d")
        override = os.environ.get("WIKI_ARTICLES")
        articles = ([a.strip() for a in override.split(",")] if override
                    else DEFAULT_ARTICLES)
        for art in articles:
            try:
                data = self.get_json(
                    API.format(article=art, start=start, end=end), timeout=45)
                items = data.get("items", [])
                if not items:
                    self.stats["fail"] += 1
                    continue
                df = pd.DataFrame(items)
                df["date"] = pd.to_datetime(df["timestamp"].str[:8],
                                            format="%Y%m%d")
                self.write("daily", df, key=art, overwrite=True)
                self.log(f"{art}: {len(df)} days")
            except Exception as e:  # noqa: BLE001
                self.stats["fail"] += 1
                self.log(f"FAIL {art}: {str(e)[:70]}")
            self.sleep()
