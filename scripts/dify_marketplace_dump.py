#!/usr/bin/env python3
"""
Dify Marketplace catalog dumper.

Pulls the FULL plugin catalog from the public Dify Marketplace search API and
writes it out in several formats:

  research/dify-marketplace/plugins.raw.json   full API objects (everything)
  research/dify-marketplace/plugins.jsonl      one normalized plugin per line
  research/dify-marketplace/plugins.csv        flat table for spreadsheets
  research/dify-marketplace/CATALOG.md         human catalog, grouped + sorted

No auth or API key required. Safe to re-run — it overwrites the outputs.
"""
import csv
import json
import os
import subprocess
import sys
import time

API = "https://marketplace.dify.ai/api/v1/plugins/search/basic"
PAGE_SIZE = 100
OUT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "research", "dify-marketplace",
)


# The empty-query firehose returns an unstable order (dupes + gaps), so we
# page each category separately — those come back in a stable order — and also
# do one plain pass, then union everything by plugin_id.
CATEGORIES = ["tool", "model", "extension", "agent-strategy", "datasource"]


def fetch_page(page, page_size=PAGE_SIZE, query="", category=None):
    payload = {"page": page, "page_size": page_size, "query": query}
    if category:
        payload["category"] = category
    body = json.dumps(payload)
    out = subprocess.run(
        ["curl", "-s", "-m", "30", API,
         "-H", "Content-Type: application/json", "-d", body],
        capture_output=True, text=True, check=True,
    ).stdout
    return json.loads(out)


def fetch_bucket(category=None):
    """Page through one category (or the whole store if None)."""
    label = category or "ALL"
    first = fetch_page(1, category=category)
    total = first["data"]["total"]
    plugins = list(first["data"]["plugins"])
    pages = (total + PAGE_SIZE - 1) // PAGE_SIZE
    print(f"[{label}] total={total} pages={pages}", file=sys.stderr)
    for p in range(2, pages + 1):
        for attempt in range(4):
            try:
                got = fetch_page(p, category=category)["data"]["plugins"]
                plugins.extend(got)
                break
            except Exception as e:  # noqa: BLE001
                wait = 2 ** attempt
                print(f"[{label}] page {p} attempt {attempt} failed: {e}",
                      file=sys.stderr)
                time.sleep(wait)
        else:
            print(f"[{label}] page {p}: GAVE UP", file=sys.stderr)
    return total, plugins


FIREHOSE_SWEEPS = 25


def fetch_all():
    collected = []
    grand_total = 0
    for cat in CATEGORIES:
        _, got = fetch_bucket(cat)
        collected.extend(got)
    # The store order is unstable, so repeated full sweeps surface different
    # items each pass; union them until coverage stops growing.
    seen = {pl.get("plugin_id") for pl in collected}
    zeros = 0
    for i in range(FIREHOSE_SWEEPS):
        grand_total, firehose = fetch_bucket(None)
        before = len(seen)
        for pl in firehose:
            pid = pl.get("plugin_id")
            if pid and pid not in seen:
                seen.add(pid)
                collected.append(pl)
        gained = len(seen) - before
        print(f"sweep {i + 1}/{FIREHOSE_SWEEPS}: +{gained} new "
              f"(coverage {len(seen)}/{grand_total})", file=sys.stderr)
        zeros = zeros + 1 if gained == 0 else 0
        if zeros >= 3:
            break
    out, done = [], set()
    for pl in collected:
        pid = pl.get("plugin_id")
        if not pid or pid in done:
            continue
        done.add(pid)
        out.append(pl)
    print(f"reported={grand_total} unique_collected={len(out)}", file=sys.stderr)
    return grand_total, out


def en(field):
    if isinstance(field, dict):
        return field.get("en_US") or next(iter(field.values()), "")
    return field or ""


def tag_names(tags):
    out = []
    for t in tags or []:
        if isinstance(t, dict):
            out.append(t.get("name") or t.get("label") or "")
        else:
            out.append(str(t))
    return [x for x in out if x]


def normalize(p):
    return {
        "plugin_id": p.get("plugin_id", ""),
        "name": p.get("name", ""),
        "org": p.get("org", ""),
        "label": en(p.get("label")),
        "category": p.get("category", ""),
        "tags": ",".join(tag_names(p.get("tags"))),
        "install_count": p.get("install_count", 0),
        "latest_version": p.get("latest_version", ""),
        "verified": bool((p.get("verification") or {}).get("authorized_category")
                         or p.get("badges")),
        "status": p.get("status", ""),
        "repository": p.get("repository", ""),
        "min_dify": ".".join(str(p.get(k, "") or "") for k in (
            "minimum_dify_version_major",
            "minimum_dify_version_minor",
            "minimum_dify_version_patch")).strip("."),
        "updated_at": p.get("updated_at", ""),
        "brief": en(p.get("brief")).replace("\n", " ").strip(),
    }


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    total, plugins = fetch_all()
    norm = [normalize(p) for p in plugins]
    norm.sort(key=lambda r: r["install_count"], reverse=True)

    with open(os.path.join(OUT_DIR, "plugins.raw.json"), "w") as f:
        json.dump({"total_reported": total, "fetched": len(plugins),
                   "plugins": plugins}, f, ensure_ascii=False, indent=2)

    with open(os.path.join(OUT_DIR, "plugins.jsonl"), "w") as f:
        for r in norm:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    cols = ["plugin_id", "name", "org", "label", "category", "tags",
            "install_count", "latest_version", "verified", "status",
            "min_dify", "repository", "updated_at", "brief"]
    with open(os.path.join(OUT_DIR, "plugins.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in norm:
            w.writerow(r)

    # Markdown catalog grouped by category, sorted by installs within group.
    by_cat = {}
    for r in norm:
        by_cat.setdefault(r["category"] or "uncategorized", []).append(r)
    lines = [
        "# Dify Marketplace — Full Catalog",
        "",
        f"- **Total reported by API:** {total}",
        f"- **Fetched (unique):** {len(norm)}",
        f"- **Source:** `{API}` (install_count-ranked, no auth)",
        "",
        "## Counts by category",
        "",
        "| category | plugins |",
        "|----------|--------:|",
    ]
    for cat in sorted(by_cat, key=lambda c: -len(by_cat[c])):
        lines.append(f"| {cat} | {len(by_cat[cat])} |")
    lines.append("")
    for cat in sorted(by_cat, key=lambda c: -len(by_cat[c])):
        lines.append(f"## {cat} ({len(by_cat[cat])})")
        lines.append("")
        lines.append("| plugin_id | installs | ver | verified | brief |")
        lines.append("|-----------|---------:|-----|:--------:|-------|")
        for r in by_cat[cat]:
            brief = r["brief"][:120].replace("|", "\\|")
            v = "✓" if r["verified"] else ""
            lines.append(
                f"| `{r['plugin_id']}` | {r['install_count']:,} | "
                f"{r['latest_version']} | {v} | {brief} |")
        lines.append("")
    with open(os.path.join(OUT_DIR, "CATALOG.md"), "w") as f:
        f.write("\n".join(lines))

    print(f"WROTE {len(norm)} plugins to {OUT_DIR}", file=sys.stderr)


if __name__ == "__main__":
    main()
