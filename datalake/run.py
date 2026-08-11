#!/usr/bin/env python3
"""run — execute datalake collectors.

    python -m datalake.run list                  # show registered collectors
    python -m datalake.run all                   # run every ready collector
    python -m datalake.run <name> [<name> ...]   # run specific collectors
    python -m datalake.run --domain crypto       # run every collector in a domain

Keys are read from the environment; source /opt/collectors/.env first so
key-based collectors (fred, …) are "ready". Collectors are resumable — they
skip Parquet that already exists — so re-running only fills gaps.
"""
from __future__ import annotations

import argparse
import os
import sys

from .collector import REGISTRY, load_sources


def _ready(name: str) -> bool:
    _, _, key = REGISTRY[name]
    return not key or bool(os.environ.get(key))


def main(argv=None):
    load_sources()
    p = argparse.ArgumentParser(prog="datalake.run")
    p.add_argument("targets", nargs="*",
                   help="collector names, or 'all', or 'list'")
    p.add_argument("--domain", help="run all collectors in this domain")
    p.add_argument("--force", action="store_true",
                   help="run even if a required key is missing (will error)")
    args = p.parse_args(argv)

    if args.targets == ["list"] or (not args.targets and not args.domain):
        print(f"{'collector':<22}{'domain':<18}{'key':<20}{'ready'}")
        print("-" * 64)
        for name in sorted(REGISTRY):
            _, domain, key = REGISTRY[name]
            print(f"{name:<22}{domain:<18}{(key or '-'):<20}"
                  f"{'yes' if _ready(name) else 'NO'}")
        return

    if args.domain:
        names = [n for n in REGISTRY if REGISTRY[n][1] == args.domain]
    elif args.targets == ["all"]:
        names = list(REGISTRY)
    else:
        names = args.targets
        unknown = [n for n in names if n not in REGISTRY]
        if unknown:
            sys.exit(f"unknown collector(s): {', '.join(unknown)}")

    ran, skipped = [], []
    for name in names:
        if not args.force and not _ready(name):
            skipped.append(name)
            print(f"SKIP {name}: missing key ${REGISTRY[name][2]}")
            continue
        cls = REGISTRY[name][0]
        try:
            stats = cls().run()
            ran.append((name, stats))
        except Exception as e:  # noqa: BLE001
            print(f"ERROR {name}: {e}")
            ran.append((name, {"error": str(e)}))

    print("\n=== summary ===")
    for name, stats in ran:
        print(f"  {name:<22} {stats}")
    if skipped:
        print(f"  skipped (no key): {', '.join(skipped)}")


if __name__ == "__main__":
    main()
