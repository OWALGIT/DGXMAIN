"""Collector framework for the ks7 / BITFIN datalake.

A thin, uniform harness around the pattern the existing /opt/collectors
scripts already use: pull from a source, write partitioned Parquet into
`staging/<source>/<dataset>/`, skip what's already there, rate-limit, log,
and drop a DONE marker. New collectors subclass `Collector` and implement
`collect()`; the framework handles paths, atomic writes, retries, resume,
and the source registry.

Datalake root defaults to /opt/collectors/staging and is overridable with
the DATALAKE_ROOT env var (handy for tests).
"""
from __future__ import annotations

import io
import json
import os
import pathlib
import sys
import time
import urllib.request
import urllib.error
from typing import Callable, Optional

import pandas as pd

LAKE = pathlib.Path(os.environ.get("DATALAKE_ROOT", "/opt/collectors/staging"))
LOG_DIR = pathlib.Path(os.environ.get("DATALAKE_LOG_DIR", str(LAKE.parent / "logs")))
# Some sources (notably SEC EDGAR) reject generic agents and require a real
# contact. Override with DATALAKE_UA to change the declared contact.
USER_AGENT = os.environ.get("DATALAKE_UA", "ks7-datalake/1.0 (bar@yohay.ai)")

# name -> (factory, domain, requires_key)
REGISTRY: dict[str, tuple[Callable[[], "Collector"], str, Optional[str]]] = {}


def source(name: str, domain: str, requires_key: Optional[str] = None):
    """Register a Collector subclass under `name`.

    `requires_key` is the env var the collector needs (or None if keyless);
    the CLI uses it to report which sources are ready to run.
    """
    def deco(cls):
        REGISTRY[name] = (cls, domain, requires_key)
        cls.name = name
        cls.domain = domain
        cls.requires_key = requires_key
        return cls
    return deco


class Collector:
    """Base class. Subclass and implement collect()."""

    name: str = "unnamed"
    domain: str = "misc"
    requires_key: Optional[str] = None
    rate_limit_s: float = 0.5  # polite default between HTTP calls

    def __init__(self, lake: pathlib.Path = LAKE):
        self.root = lake / self.name
        self.root.mkdir(parents=True, exist_ok=True)
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        self._logf = LOG_DIR / f"{self.name}.log"
        self.stats = {"ok": 0, "skip": 0, "fail": 0, "rows": 0}

    # ---- io helpers -----------------------------------------------------
    def log(self, msg: str) -> None:
        line = f"{_ts()} [{self.name}] {msg}"
        print(line, flush=True)
        try:
            with open(self._logf, "a") as f:
                f.write(line + "\n")
        except OSError:
            pass

    def key(self) -> str:
        if not self.requires_key:
            return ""
        val = os.environ.get(self.requires_key, "")
        if not val:
            raise RuntimeError(
                f"{self.name}: missing required key ${self.requires_key}")
        return val

    def _get(self, url: str, timeout: int = 60, retries: int = 3) -> bytes:
        last = None
        for attempt in range(retries):
            try:
                req = urllib.request.Request(
                    url, headers={"User-Agent": USER_AGENT})
                with urllib.request.urlopen(req, timeout=timeout) as r:
                    return r.read()
            except (urllib.error.URLError, TimeoutError, OSError) as e:
                last = e
                time.sleep(2 ** attempt)
        raise RuntimeError(f"GET failed after {retries}: {url[:80]} :: {last}")

    def get_json(self, url: str, **kw):
        return json.loads(self._get(url, **kw))

    def get_csv(self, url: str, **kw) -> pd.DataFrame:
        return pd.read_csv(io.BytesIO(self._get(url, **kw)))

    def sleep(self) -> None:
        if self.rate_limit_s:
            time.sleep(self.rate_limit_s)

    # ---- write ----------------------------------------------------------
    def write(self, dataset: str, df: pd.DataFrame, key: str,
              overwrite: bool = False) -> bool:
        """Write one Parquet file at staging/<source>/<dataset>/<key>.parquet.

        Returns True if written, False if skipped (already present). Writes
        atomically via a temp file + rename so a crash never leaves a
        half-written Parquet in the lake.
        """
        if df is None or len(df) == 0:
            self.stats["fail"] += 1
            self.log(f"EMPTY {dataset}/{key}")
            return False
        dest = self.root / dataset
        dest.mkdir(parents=True, exist_ok=True)
        fp = dest / f"{_safe(key)}.parquet"
        if fp.exists() and not overwrite:
            self.stats["skip"] += 1
            return False
        tmp = fp.with_suffix(".parquet.tmp")
        df.to_parquet(tmp, index=False)
        os.replace(tmp, fp)
        self.stats["ok"] += 1
        self.stats["rows"] += len(df)
        return True

    def done(self) -> None:
        (LAKE.parent / f"{self.name}_DONE").touch()

    # ---- lifecycle ------------------------------------------------------
    def collect(self) -> None:  # pragma: no cover - abstract
        raise NotImplementedError

    def run(self) -> dict:
        t0 = time.time()
        self.log(f"start (domain={self.domain})")
        try:
            self.collect()
        finally:
            dt = time.time() - t0
            self.log(f"DONE ok={self.stats['ok']} skip={self.stats['skip']} "
                     f"fail={self.stats['fail']} rows={self.stats['rows']} "
                     f"in {dt:.0f}s")
            self.done()
        return self.stats


def _ts() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")


def _safe(s: str) -> str:
    return "".join(c if c.isalnum() or c in "-._" else "_" for c in str(s))


def load_sources() -> None:
    """Import every module in sources/ so decorators populate REGISTRY."""
    import importlib
    import pkgutil
    from . import sources as pkg
    for m in pkgutil.iter_modules(pkg.__path__):
        importlib.import_module(f"{pkg.__name__}.{m.name}")
