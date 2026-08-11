# Datalake toolkit

Tools to **aggregate** market/alt data from many sources and to **manage**
the resulting Parquet datalake. Built to fit the existing convention on the
DGX nodes: everything lands under `staging/<dataset>/…` as Parquet, and the
lake is queried in place — no database server to run or feed.

The DGX cluster has ~4TB of local NVMe per node (8TB across dgxmain + dgxsec),
plus effectively unlimited Storj object storage mounted at `/mnt/storj-*`.

## Two halves

### 1. Aggregation — `run.py` + `sources/`
A uniform collector framework (`collector.py`). Each source subclasses
`Collector`, pulls from an API, and writes partitioned Parquet with atomic
writes, retries, rate-limiting, resume-on-rerun, logging, and a `*_DONE`
marker. Register with the `@source(name, domain, requires_key)` decorator.

```bash
python -m datalake.run list          # every collector + whether its key is set
python -m datalake.run all           # run all ready collectors
python -m datalake.run stooq fred    # run specific ones
python -m datalake.run --domain crypto
```

Collectors shipped (all keyless except `fred`):

| source | domain | data |
|--------|--------|------|
| `stooq` | market | global EOD equities/indices/FX/commodities |
| `binance_klines` | crypto | deep daily crypto OHLCV |
| `us_treasury_yield` | rates | daily par yield curve, 1990→ |
| `sec_companyfacts` | fundamentals | full XBRL fact history per US company |
| `fred` | macro | Fed macro series (needs `FRED_API_KEY`) |
| `attention_wikipedia_pv` | attention | pageviews = crowd attention |
| `polymarket` | prediction_markets | crowd betting odds ("הימורים") |
| `gdelt_tone` | geopolitics | global news volume/tone per theme |

Universes are broad defaults, each overridable by env var (e.g.
`STOOQ_SYMBOLS`, `SEC_TICKERS`, `FRED_SERIES`) — widen them to pull more.

### 2. Management — `dl.py` (DuckDB)
DuckDB reads Parquet directly, so the whole lake is queryable as SQL with
every dataset exposed as a view.

```bash
python datalake/dl.py list                 # datasets + file counts
python datalake/dl.py stats --rows         # size / files / freshness / rows
python datalake/dl.py coverage --stale-days 3   # what's gone stale
python datalake/dl.py schema twelvedata    # columns + types
python datalake/dl.py sources              # collectors + key readiness
python datalake/dl.py query "SELECT symbol, count(*) FROM stooq GROUP BY 1"
```

## Deploy

```bash
./datalake/deploy.sh dgxsec dgxmain        # rsync + pip install on the nodes
```

Then on a node:
```bash
cd /opt/datalake
set -a; . /opt/collectors/.env; set +a     # load keys
python3 -m datalake.run all                # aggregate
python3 datalake/dl.py stats --rows        # inspect
```

## Config

- `DATALAKE_ROOT` — lake location (default `/opt/collectors/staging`).
- `DATALAKE_LOG_DIR` — collector logs (default `<root>/../logs`).
- Per-source universe overrides — see each module's docstring.

## Adding a source

Drop a module in `sources/`:

```python
from ..collector import Collector, source

@source("mysrc", domain="market", requires_key=None)
class MySrc(Collector):
    def collect(self):
        df = self.get_csv("https://…")
        self.write("daily", df, key="AAPL")
```

It's auto-discovered — no registration list to edit.
