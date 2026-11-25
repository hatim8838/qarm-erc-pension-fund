"""Precomputed results in webapp_v2/precomputed/, written once by scripts/precompute.py (parquet files).

They are used only when meta.json matches the current parameters, code and data (sizes and SHA-256
hashes); otherwise every loader here returns None and the app computes live, exactly as before.
Modification dates are recorded in meta.json but not compared: git does not keep them, so they always
differ on a fresh checkout (Streamlit Cloud).
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

import config as cfg

DIR = cfg.PRECOMPUTED_DIR
META = DIR / "meta.json"
FORMAT = 1  # bump when the layout of the stored files changes
STATE = {"enabled": True}  # scripts/precompute.py switches the stored results off while it recomputes them
# Modules whose code shapes the stored numbers: a change in any of them invalidates the files
MODULES = ("logic.composition", "logic.construction", "logic.covariance", "logic.data", "logic.portfolio",
           "logic.report", "logic.risk", "logic.store", "logic.universe", "core.config", "core.importation_data",
           "core.utilities")
SCREEN_OUT, SCREEN_KEPT = -1, 0  # screen frame: not a candidate, kept; k >= 1 = k-th excluded (worst first)
PARQUET = {"compression": "zstd"}


# --------------------------------------------------------------------------- #
# Fingerprint and validity
# --------------------------------------------------------------------------- #
def parameters() -> dict:
    """Settings that shape the stored results."""
    return {"format": FORMAT, "estimation_window": cfg.ESTIMATION_WINDOW, "rebalancing": cfg.REBALANCING_FREQ,
            "start": cfg.PORTFOLIO_START, "trading_days": cfg.TRADING_DAYS, "esg_levels": cfg.ESG_LEVELS}


def _sha256(path: Path) -> str:
    """SHA-256 of a file's content."""
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _code_files() -> list[Path]:
    """Source files of MODULES (located without importing them)."""
    return [Path(importlib.util.find_spec(m).origin) for m in MODULES]


def fingerprint() -> dict:
    """Parameters, code hashes and data files (size, modification date, SHA-256)."""
    data = {}
    for path in cfg.PRECOMPUTE_INPUTS:
        stat = path.stat()
        data[path.name] = {"size": stat.st_size, "sha256": _sha256(path),
                           "modified": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(timespec="seconds")}
    code = {str(p.relative_to(cfg.ROOT)): _sha256(p) for p in _code_files()}
    return {"parameters": parameters(), "code": code, "data": data}


def _comparable(meta: dict) -> dict:
    """What must match: everything but the modification dates and the list of written files."""
    data = {name: {k: v for k, v in d.items() if k != "modified"} for name, d in meta.get("data", {}).items()}
    return {"parameters": meta.get("parameters"), "code": meta.get("code"), "data": data}


@lru_cache(maxsize=1)
def _valid() -> bool:
    """meta.json matches the current fingerprint and every listed file is there, with its size."""
    if not META.exists():
        return False
    meta = json.loads(META.read_text())
    files = meta.get("files", {})
    complete = bool(files) and all((DIR / f).is_file() and (DIR / f).stat().st_size == n for f, n in files.items())
    return complete and _comparable(meta) == _comparable(json.loads(json.dumps(fingerprint())))


def available() -> bool:
    """True when the stored results can be used."""
    return STATE["enabled"] and _valid()


def write_meta() -> None:
    """Write meta.json: the fingerprint and the size of every file written."""
    files = {str(p.relative_to(DIR)): p.stat().st_size for p in sorted(DIR.rglob("*.parquet"))}
    META.write_text(json.dumps({**fingerprint(), "files": files}, indent=2, sort_keys=True) + "\n")
    _valid.cache_clear()


def _read(path: Path) -> pd.DataFrame | None:
    """A stored table, or None when the files are not usable (the caller then computes live)."""
    if not available():
        return None
    try:
        return pd.read_parquet(path)
    except (OSError, ValueError):  # missing or unreadable file (pyarrow's errors are ValueErrors)
        return None


def _write(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(path, **PARQUET)


# --------------------------------------------------------------------------- #
# Level 1 of each sleeve and ESG level (all sectors)
# --------------------------------------------------------------------------- #
def _level1_dir(sleeve: str, esg: str) -> Path:
    return DIR / "level1" / f"{sleeve}__{esg}"


def _screen_frame(screen: dict, columns: pd.Index) -> pd.DataFrame:
    """The (candidates, excluded) pairs of every date as one integer frame (columns in the sleeve's order)."""
    rows = {}
    for t, (candidates, excluded) in screen.items():
        row = pd.Series(SCREEN_OUT, index=columns, dtype="int16")
        row[candidates] = SCREEN_KEPT
        if len(excluded):
            row[excluded] = np.arange(1, len(excluded) + 1, dtype="int16")
        rows[t] = row
    return pd.DataFrame(rows).T


def _screen(frame: pd.DataFrame) -> dict:
    """Back to {date: (candidates in the sleeve's order, excluded worst first)}."""
    out = {}
    for t, row in frame.iterrows():
        v = row.to_numpy()
        out_rank = v[v > SCREEN_KEPT]
        out[t] = (frame.columns[v >= SCREEN_KEPT], frame.columns[v > SCREEN_KEPT][np.argsort(out_rank, kind="stable")])
    return out


def save_level1(sleeve: str, esg: str, result: dict, columns: pd.Index) -> None:
    """Returns, weights, risk contributions, turnover, windows and screen of one level-1 backtest."""
    folder = _level1_dir(sleeve, esg)
    _write(result["returns"].to_frame(), folder / "returns.parquet")
    _write(result["turnover"].to_frame(), folder / "turnover.parquet")
    _write(result["weights"], folder / "weights.parquet")
    _write(result["rc"], folder / "rc.parquet")
    _write(pd.concat(result["windows"], names=["rebalance"]).to_frame("value"), folder / "windows.parquet")
    _write(_screen_frame(result["screen"], columns), folder / "screen.parquet")


def load_level1(sleeve: str, esg: str) -> dict | None:
    """The same dict as construction.level1 computes live (plus "rc"), or None."""
    folder = _level1_dir(sleeve, esg)
    tables = {name: _read(folder / f"{name}.parquet")
              for name in ("returns", "turnover", "weights", "rc", "windows", "screen")}
    if any(t is None for t in tables.values()):
        return None
    windows = tables["windows"]["value"]
    return {"returns": tables["returns"].iloc[:, 0], "weights": tables["weights"],
            "turnover": tables["turnover"].iloc[:, 0], "screen": _screen(tables["screen"]),
            "windows": {t: w.droplevel(0).rename(None) for t, w in windows.groupby(level=0, sort=False)},
            "rc": tables["rc"]}


def load_last_weights(sleeve: str, esg: str) -> tuple[pd.Timestamp, pd.Series] | None:
    """Date and weights of the last rebalancing, in the order the ERC returned them (kept candidates);
    reads only the weights and the screen."""
    folder = _level1_dir(sleeve, esg)
    weights, screen = _read(folder / "weights.parquet"), _read(folder / "screen.parquet")
    if weights is None or screen is None:
        return None
    t = weights.index[-1]
    kept = screen.columns[screen.loc[t].to_numpy() == SCREEN_KEPT]
    return t, weights.loc[t, kept].rename(None)


# --------------------------------------------------------------------------- #
# Last estimation window of each sleeve, and "Our strategy"
# --------------------------------------------------------------------------- #
def save_tail(sleeve: str, tail: pd.DataFrame) -> None:
    _write(tail, DIR / "last_window" / f"{sleeve}.parquet")


def load_tail(sleeve: str) -> pd.DataFrame | None:
    """Returns of every asset of the sleeve over the last estimation window, or None."""
    return _read(DIR / "last_window" / f"{sleeve}.parquet")


def save_strategy(table: pd.DataFrame, holds: pd.Series) -> None:
    _write(table, DIR / "strategy" / "lab.parquet")
    _write(holds.rename("holds").to_frame(), DIR / "strategy" / "theorem.parquet")


def load_strategy() -> tuple[pd.DataFrame, pd.Series] | None:
    """The EW / ERC / MV table of the last rebalancing and the theorem at every rebalancing, or None."""
    table, holds = _read(DIR / "strategy" / "lab.parquet"), _read(DIR / "strategy" / "theorem.parquet")
    return None if table is None or holds is None else (table, holds["holds"].rename(None))
