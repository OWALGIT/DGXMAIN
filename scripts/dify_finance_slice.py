#!/usr/bin/env python3
"""Derive a finance-relevant slice from the full marketplace dump.

Reads research/dify-marketplace/plugins.jsonl and writes:
  research/dify-marketplace/FINANCE.md   ranked finance/market/data plugins

The keyword filter is intentionally broad (market data, sentiment, SEC, crypto,
FX, research) so the BITFIN team can eyeball the long tail, not just obvious hits.
"""
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "research", "dify-marketplace", "plugins.jsonl")
OUT = os.path.join(ROOT, "research", "dify-marketplace", "FINANCE.md")

KW = re.compile(
    r"financ|stock|equit|trading|market data|\binvest|crypto|forex|\bfx\b|"
    r"sec edgar|edgar|sentiment|ticker|earnings|nasdaq|\bquote|portfolio|"
    r"economic|dividend|valuation|hedge|commodit|bond|treasury|macro",
    re.I,
)


def main():
    rows = [json.loads(line) for line in open(SRC)]
    hits = [r for r in rows
            if KW.search(" ".join([r["label"], r["brief"], r["tags"]]))]
    hits.sort(key=lambda r: r["install_count"], reverse=True)

    lines = [
        "# Dify Marketplace — Finance / Market-Data Slice",
        "",
        f"Derived from the full dump ({len(rows)} plugins). "
        f"**{len(hits)}** match finance/market/data keywords.",
        "",
        "> Keyword filter is broad on purpose (market data, sentiment, SEC/EDGAR,",
        "> crypto, FX, research, macro). Relevance to BITFIN is a human call —",
        "> this is the candidate pool, ranked by install_count.",
        "",
        "| plugin_id | installs | ver | verified | brief |",
        "|-----------|---------:|-----|:--------:|-------|",
    ]
    for r in hits:
        brief = r["brief"][:130].replace("|", "\\|")
        v = "✓" if r["verified"] else ""
        lines.append(
            f"| `{r['plugin_id']}` | {r['install_count']:,} | "
            f"{r['latest_version']} | {v} | {brief} |")
    lines.append("")
    with open(OUT, "w") as f:
        f.write("\n".join(lines))
    print(f"{len(hits)} finance-relevant plugins -> {OUT}")


if __name__ == "__main__":
    main()
