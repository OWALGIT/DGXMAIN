# market-data — Storj datalake explorer & cross-asset analysis

Tooling to explore and analyse the **`market-data`** bucket on Storj (73 datasets,
~1,683 parquet files, ~2.4 GB of financial/market/alt-data), and to build a
unified daily cross-asset panel for correlation, crisis and lead-lag analysis.

## Why boto3 and not `uplink`

From a proxied/egress-restricted environment (HTTPS-only, like Claude Code on the
web), Storj's **native** protocol is unreachable:

- the satellite speaks DRPC on port **7777** — blocked by an HTTPS-only proxy;
- the `uplink` Go CLI **ignores `HTTPS_PROXY`**, so even `access register` hangs.

The **S3-compatible gateway** (`gateway.storjshare.io`, port 443) works fine
because boto3/urllib honour `HTTPS_PROXY`. So the flow is:

1. take a Storj **access grant** (e.g. rclone's `access_grant = …`),
2. register it with the auth service over HTTPS → S3 keys (`register_access.py`),
3. use those keys with boto3 (`s3lib.py`).

> A truncated grant registers successfully but decrypts **nothing** (all buckets
> list, every object count is 0). Always use the full grant string.

## Setup

```bash
pip install boto3 pyarrow pandas numpy

# Convert your Storj access grant -> S3 creds, then load them into the env:
eval "$(python3 register_access.py "$ACCESS_GRANT")"
# now $STORJ_ENDPOINT / $STORJ_KEY / $STORJ_SECRET are set
```

Credentials are **never** hard-coded — every script reads them from the
`STORJ_ENDPOINT` / `STORJ_KEY` / `STORJ_SECRET` environment variables.

## Scripts

| script | what it does |
|--------|--------------|
| `register_access.py` | access grant → S3 gateway credentials (via HTTPS auth service) |
| `s3lib.py` | boto3 client factory (path-style, payload-signing off, for Storj gateway) |
| `inventory.py` | list every dataset: file counts, sizes, sources |
| `build_panel.py` | assemble a unified **daily panel** (2023→today) of ~60 asset + event-signal series → `panel.parquet` |
| `analyze.py` | correlations, systemic co-movement, crisis timeline, **lead-lag** cross-correlation, event studies → `findings.json` |
| `build_dashboard.py` | render `findings.json` into a self-contained `dashboard.html` |

```bash
python3 inventory.py
python3 build_panel.py       # writes panel.parquet
python3 analyze.py           # writes findings.json
python3 build_dashboard.py   # writes dashboard.html
```

## Data model

Objects are Hive-partitioned: `dataset/source=<src>/symbol=<sym>/<file>.parquet`.
Price series are OHLCV (`date, close, symbol`); event signals include GDELT news
volume by topic, IMF PortWatch chokepoint transits (Bab el-Mandeb = Red Sea,
Suez, Hormuz, Taiwan Strait…), GDELT conflict events, and Wikipedia attention.

## Example output

`examples/dashboard.html` + `examples/findings.json` — a run over 2023-01-01 →
2026-08-08 tracing how external shocks (Red Sea shipping halt, Israel–Hamas war,
SVB, yen-carry unwind) propagate across equities, oil, gold, VIX and China.
The numbers are exploratory, not trading advice.
