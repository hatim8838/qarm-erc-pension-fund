"""Precompute what never changes, so the app only runs the level-2 ERC across <= 6 sleeves for any choice.

    OMP_NUM_THREADS=1 python webapp_v2/scripts/precompute.py

Writes webapp_v2/precomputed/ (parquet): the level-1 ERC of every sleeve at every ESG level with all sectors
(sleeve returns, weights, risk contributions, turnover, windows and screen at every rebalancing), the last
estimation window of every sleeve, the "Our strategy" lab, and meta.json (parameters, code and data
fingerprints). Re-run it whenever the data, the parameters or the method change: until then the app
ignores the files and computes everything live. Every stored table is read back and compared exactly
with the live result before meta.json is written.
"""

import os

for _var in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS"):
    os.environ.setdefault(_var, "1")  # single-threaded, deterministic arithmetic, as on the online server

import shutil  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402
from pathlib import Path  # noqa: E402

import pandas as pd  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config as cfg  # noqa: E402
from logic import composition, construction, data, portfolio, report, store  # noqa: E402


def _same(stored, live) -> None:
    """Exact equality of a stored table with the live one (values, index, columns, dtypes, names)."""
    check = pd.testing.assert_frame_equal if isinstance(live, pd.DataFrame) else pd.testing.assert_series_equal
    check(stored, live, check_exact=True, check_freq=False)


def _check_level1(stored: dict, live: dict) -> None:
    for key in ("returns", "weights", "turnover", "rc"):
        _same(stored[key], live[key])
    assert stored["windows"].keys() == live["windows"].keys() and stored["screen"].keys() == live["screen"].keys()
    for t, w in live["windows"].items():
        _same(stored["windows"][t], w)
    for t, (candidates, excluded) in live["screen"].items():
        pd.testing.assert_index_equal(stored["screen"][t][0], candidates, exact=True)
        pd.testing.assert_index_equal(stored["screen"][t][1], excluded, exact=True)


def level1_all() -> list:
    """Level 1 of every sleeve: each ESG level for the regions (all sectors), unfiltered bonds and commodities."""
    done = []
    for sleeve in data.sleeves():
        regional = sleeve in data.regions()
        sectors = tuple(data.sectors()) if regional else ()
        for esg in cfg.ESG_LEVELS if regional else (portfolio.NO_SCREEN,):
            start = time.perf_counter()
            live = construction.level1(sleeve, sectors, esg)
            live = {**live, "rc": composition.rc_frame(sleeve, live["weights"])}
            store.save_level1(sleeve, esg, live, construction.sleeve_returns(sleeve, sectors).columns)
            done.append((sleeve, esg, live))
            print(f"level 1  {sleeve:12} {esg:7} {time.perf_counter() - start:6.1f} s", flush=True)
    return done


def main() -> None:
    store.STATE["enabled"] = False  # recompute everything live, even if older files are valid
    shutil.rmtree(store.DIR, ignore_errors=True)
    done = level1_all()
    for sleeve in data.sleeves():
        store.save_tail(sleeve, data.sleeve_tail(sleeve))
    lab = report.strategy_lab(portfolio.build(portfolio.baseline()))
    store.save_strategy(*lab)
    store.write_meta()
    store.STATE["enabled"] = True
    for sleeve, esg, live in done:  # read every file back: it must equal the live result exactly
        _check_level1(store.load_level1(sleeve, esg), live)
    for sleeve in data.sleeves():
        store.STATE["enabled"] = False
        live = data.sleeve_tail.__wrapped__(sleeve)
        store.STATE["enabled"] = True
        _same(store.load_tail(sleeve), live)
    for stored, live in zip(store.load_strategy(), lab):
        _same(stored, live)
    assert store.available(), "meta.json does not match the current fingerprint"
    size = sum(p.stat().st_size for p in store.DIR.rglob("*") if p.is_file())
    print(f"written {store.DIR} ({size / 2**20:.1f} MB), every table read back identical", flush=True)


if __name__ == "__main__":
    main()
