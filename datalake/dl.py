#!/usr/bin/env python3
"""dl — the datalake manager.

A DuckDB-backed control surface over the Parquet datalake under
`staging/<dataset>/…`. DuckDB reads Parquet directly (SQL over files, no
import step) which is the right engine for this lake — the data is columnar
Parquet, not rows in a SQL server.

Commands
    dl list                       datasets + file counts
    dl stats [--rows]             per-dataset size / files / freshness (+rows)
    dl schema <dataset>           columns and types
    dl coverage [--stale-days N]  freshness report, flag stale datasets
    dl query "<SQL>"              run SQL over the lake (every dataset is a view)
    dl sources                    registered collectors + whether their key is set
    dl catalog [--json]           dump the full catalog

Root defaults to /opt/collectors/staging; override with DATALAKE_ROOT.
Every dataset directory becomes a DuckDB view named after the directory, so
`dl query 'SELECT * FROM twelvedata LIMIT 5'` just works.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys
import time

ROOT = pathlib.Path(os.environ.get("DATALAKE_ROOT", "/opt/collectors/staging"))


def _duckdb():
    try:
        import duckdb
        return duckdb
    except ImportError:
        sys.exit("duckdb not installed — run: pip install duckdb  "
                 "(or use datalake/deploy.sh)")


def scan(root: pathlib.Path = ROOT) -> list[dict]:
    """Find every dataset: a directory that contains at least one .parquet
    somewhere beneath it. Records file count, byte size, newest mtime."""
    datasets = []
    if not root.exists():
        return datasets
    for d in sorted(p for p in root.iterdir() if p.is_dir()):
        files = list(d.rglob("*.parquet"))
        if not files:
            continue
        size = sum(f.stat().st_size for f in files)
        newest = max(f.stat().st_mtime for f in files)
        datasets.append({
            "dataset": d.name,
            "path": str(d),
            "files": len(files),
            "bytes": size,
            "newest_mtime": newest,
            "glob": str(d / "**" / "*.parquet"),
        })
    return datasets


def _register(con, datasets: list[dict]) -> list[str]:
    """Create a view per dataset. Returns names that registered cleanly."""
    ok = []
    for ds in datasets:
        name = ds["dataset"]
        # CREATE VIEW can't take a bound parameter, so inline the glob as a
        # quoted string literal (single quotes doubled to stay safe).
        glob_lit = "'" + ds["glob"].replace("'", "''") + "'"
        try:
            con.execute(
                f'CREATE OR REPLACE VIEW "{name}" AS '
                f"SELECT * FROM read_parquet({glob_lit}, union_by_name=true, "
                f"hive_partitioning=1, filename=1)")
            ok.append(name)
        except Exception as e:  # noqa: BLE001 - a bad dataset shouldn't kill all
            print(f"  ! skip view {name}: {str(e)[:70]}", file=sys.stderr)
    return ok


def cmd_list(args):
    ds = scan()
    print(f"{'dataset':<28}{'files':>8}{'size':>12}")
    print("-" * 48)
    for d in ds:
        print(f"{d['dataset']:<28}{d['files']:>8}{_h(d['bytes']):>12}")
    print("-" * 48)
    print(f"{len(ds)} datasets, "
          f"{sum(d['files'] for d in ds):,} files, "
          f"{_h(sum(d['bytes'] for d in ds))}")


def cmd_stats(args):
    duckdb = _duckdb()
    ds = scan()
    con = duckdb.connect()
    now = time.time()
    print(f"{'dataset':<26}{'files':>7}{'size':>11}{'age':>8}"
          + ("{:>14}".format("rows") if args.rows else ""))
    print("-" * (52 + (14 if args.rows else 0)))
    total_rows = 0
    for d in ds:
        age = _age(now - d["newest_mtime"])
        rows = ""
        if args.rows:
            try:
                n = con.execute(
                    "SELECT count(*) FROM read_parquet(?, union_by_name=true)",
                    [d["glob"]]).fetchone()[0]
                total_rows += n
                rows = f"{n:,}"
            except Exception:
                rows = "ERR"
        print(f"{d['dataset']:<26}{d['files']:>7}{_h(d['bytes']):>11}{age:>8}"
              + (f"{rows:>14}" if args.rows else ""))
    print("-" * (52 + (14 if args.rows else 0)))
    tail = f"   rows={total_rows:,}" if args.rows else ""
    print(f"{len(ds)} datasets   files={sum(d['files'] for d in ds):,}   "
          f"size={_h(sum(d['bytes'] for d in ds))}{tail}")


def cmd_schema(args):
    duckdb = _duckdb()
    ds = {d["dataset"]: d for d in scan()}
    if args.dataset not in ds:
        sys.exit(f"no such dataset: {args.dataset}")
    con = duckdb.connect()
    rows = con.execute(
        "DESCRIBE SELECT * FROM read_parquet(?, union_by_name=true) LIMIT 1",
        [ds[args.dataset]["glob"]]).fetchall()
    print(f"{args.dataset}:")
    for name, typ, *_ in rows:
        print(f"  {name:<32} {typ}")


def cmd_coverage(args):
    ds = scan()
    now = time.time()
    stale = []
    print(f"{'dataset':<26}{'newest':>20}{'age':>8}")
    print("-" * 54)
    for d in sorted(ds, key=lambda x: x["newest_mtime"]):
        age_days = (now - d["newest_mtime"]) / 86400
        mark = "  STALE" if age_days > args.stale_days else ""
        if age_days > args.stale_days:
            stale.append(d["dataset"])
        when = time.strftime("%Y-%m-%d %H:%M",
                             time.localtime(d["newest_mtime"]))
        print(f"{d['dataset']:<26}{when:>20}{_age(now - d['newest_mtime']):>8}{mark}")
    print("-" * 54)
    print(f"{len(stale)}/{len(ds)} datasets stale (> {args.stale_days}d): "
          + (", ".join(stale) if stale else "none"))


def cmd_query(args):
    duckdb = _duckdb()
    con = duckdb.connect()
    names = _register(con, scan())
    try:
        con.execute(args.sql)
        cols = [c[0] for c in con.description] if con.description else []
        rows = con.fetchall()
    except Exception as e:  # noqa: BLE001
        sys.exit(f"query error: {e}")
    if args.csv:
        import csv
        w = csv.writer(sys.stdout)
        if cols:
            w.writerow(cols)
        w.writerows(rows)
    else:
        if cols:
            print(" | ".join(cols))
            print("-" * 60)
        for r in rows[:args.limit]:
            print(" | ".join("" if v is None else str(v) for v in r))
        if len(rows) > args.limit:
            print(f"... {len(rows) - args.limit} more rows "
                  f"({len(names)} views available)")


def cmd_sources(args):
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
    from datalake import collector
    collector.load_sources()
    reg = collector.REGISTRY
    print(f"{'source':<22}{'domain':<16}{'key':<22}{'ready'}")
    print("-" * 66)
    for name in sorted(reg):
        _, domain, key = reg[name]
        ready = "yes" if (not key or os.environ.get(key)) else "NO"
        print(f"{name:<22}{domain:<16}{(key or '-'):<22}{ready}")
    print("-" * 66)
    print(f"{len(reg)} registered collectors")


def cmd_catalog(args):
    ds = scan()
    for d in ds:
        d["size_h"] = _h(d["bytes"])
        d["newest"] = time.strftime("%Y-%m-%dT%H:%M:%S",
                                    time.localtime(d["newest_mtime"]))
    if args.json:
        print(json.dumps(ds, indent=2))
    else:
        for d in ds:
            print(f"{d['dataset']:<28} {d['files']:>6} files  "
                  f"{d['size_h']:>10}  {d['newest']}")


def _h(n: float) -> str:
    for unit in ("B", "K", "M", "G", "T"):
        if n < 1024:
            return f"{n:.0f}{unit}" if unit == "B" else f"{n:.1f}{unit}"
        n /= 1024
    return f"{n:.1f}P"


def _age(seconds: float) -> str:
    d = seconds / 86400
    if d < 1:
        return f"{seconds / 3600:.0f}h"
    if d < 30:
        return f"{d:.0f}d"
    return f"{d / 30:.0f}mo"


def main(argv=None):
    p = argparse.ArgumentParser(prog="dl", description="datalake manager")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("list", help="datasets + file counts").set_defaults(fn=cmd_list)

    s = sub.add_parser("stats", help="size/files/freshness per dataset")
    s.add_argument("--rows", action="store_true", help="also count rows (slower)")
    s.set_defaults(fn=cmd_stats)

    s = sub.add_parser("schema", help="columns and types for a dataset")
    s.add_argument("dataset")
    s.set_defaults(fn=cmd_schema)

    s = sub.add_parser("coverage", help="freshness report")
    s.add_argument("--stale-days", type=float, default=3)
    s.set_defaults(fn=cmd_coverage)

    s = sub.add_parser("query", help="run SQL over the lake")
    s.add_argument("sql")
    s.add_argument("--limit", type=int, default=50)
    s.add_argument("--csv", action="store_true")
    s.set_defaults(fn=cmd_query)

    sub.add_parser("sources", help="registered collectors").set_defaults(fn=cmd_sources)

    s = sub.add_parser("catalog", help="dump catalog")
    s.add_argument("--json", action="store_true")
    s.set_defaults(fn=cmd_catalog)

    args = p.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
