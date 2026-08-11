# Dify Marketplace — Full Catalog Dump

A near-complete snapshot of the public [Dify Marketplace](https://marketplace.dify.ai)
plugin catalog, pulled via its public search API (no auth required).

## Files

| file | what it is |
|------|-----------|
| `plugins.raw.json.gz` | Full, untouched API objects for every plugin (all fields). Gzipped. |
| `plugins.jsonl` | One normalized plugin per line — the working dataset. |
| `plugins.csv` | Same normalized rows as a flat table for spreadsheets. |
| `CATALOG.md` | Human-readable catalog, grouped by category, install-count ranked. |
| `FINANCE.md` | Finance / market-data / sentiment slice (derived), ranked. |

Normalized columns: `plugin_id, name, org, label, category, tags,
install_count, latest_version, verified, status, min_dify, repository,
updated_at, brief`. The `repository` field is the plugin's GitHub URL where
published.

## Coverage

The API reports **918** plugins in the store. This dump captures **861**
unique (~94%). The remaining ~57 are counted in the store total but never
returned by the public listing endpoints (deprecated / hidden / unlisted),
so they are not retrievable without authenticated or internal access.

The listing order is **not stable** across pages, which causes both
duplicates and gaps on any single pass. The dumper works around this by
paging each category separately (stable within a category) and then running
repeated full-store sweeps, unioning by `plugin_id` until coverage stops
growing (3 consecutive zero-gain sweeps).

Category totals reported by the API: tool 681, model 143, extension 33,
datasource 29, agent-strategy 11.

## Regenerate

```bash
python3 scripts/dify_marketplace_dump.py   # writes the 4 core files
python3 scripts/dify_finance_slice.py      # writes FINANCE.md
gzip -f research/dify-marketplace/plugins.raw.json
```

Requires `curl` on PATH (outbound HTTPS). No API key. Safe to re-run — it
overwrites the outputs. Counts will drift as the store grows.

## Snapshot date

Captured 2026-08-11.
