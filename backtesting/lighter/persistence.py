from __future__ import annotations

import os

import numpy as np
import pandas as pd

# Persistence for a backtest run's column arrays (the dict returned by
# Backtester.run / _engine.run_arrays). Three tables — pnl, quotes, fills — stored as
# parquet: typed and binary, so read/write skip the text↔number conversion that made
# CSV the pipeline bottleneck (~17-58x faster to read, ~3.5x smaller on disk).
#
# The array contract carries `fill_side` as an int code (0=bid, 1=ask, 2=markout),
# exactly as the C++ engine emits it. On load we normalise legacy CSVs (which stored
# the side as a string) back to that code so callers see one schema.

_SIDE_CODE = {"bid": 0, "ask": 1, "markout": 2}

_PNL_COLS   = {"t_us": "pnl_t", "pnl": "pnl_v", "inventory": "inv_v"}
_QUOTE_COLS = {"t_us": "qt_t", "bid": "qt_bid", "ask": "qt_ask", "mid": "qt_mid"}
_FILL_COLS  = {"t_us": "fill_t", "side": "fill_side", "price": "fill_price",
               "size": "fill_size", "inventory": "fill_inv", "mid_at_fill": "fill_mid",
               "fee": "fill_fee"}
_QUOTA_COLS = {"t_us": "quota_t", "quota": "quota_v", "kind": "quota_kind"}


def save_run(arrays: dict, prefix: str) -> str:
    """Persist a run's arrays as `{prefix}_{pnl,quotes,fills}.parquet`. Returns prefix."""
    def frame(cols):
        return pd.DataFrame({name: arrays[key] for name, key in cols.items()})
    frame(_PNL_COLS).to_parquet(f"{prefix}_pnl.parquet", index=False)
    frame(_QUOTE_COLS).to_parquet(f"{prefix}_quotes.parquet", index=False)
    frame(_FILL_COLS).to_parquet(f"{prefix}_fills.parquet", index=False)
    frame(_QUOTA_COLS).to_parquet(f"{prefix}_quota.parquet", index=False)
    return prefix


def load_run(prefix: str) -> dict:
    """Load a persisted run back into the array dict. Reads parquet; falls back to the
    legacy CSV layout (`{prefix}_*.csv`) when parquet is absent — a migration bridge for
    runs saved before the format switch."""
    def read(name):
        parquet, csv = f"{prefix}_{name}.parquet", f"{prefix}_{name}.csv"
        if os.path.exists(parquet):
            return pd.read_parquet(parquet)
        if os.path.exists(csv):
            return pd.read_csv(csv)
        raise FileNotFoundError(f"no {parquet} nor {csv}")

    pnl, quotes, fills, quota = read("pnl"), read("quotes"), read("fills"), read("quota")

    side = fills["side"].to_numpy()
    if side.dtype.kind in "OUS":                     # legacy CSV stored side as a string
        side = np.array([_SIDE_CODE[s] for s in side], dtype=np.int32)

    out = {key: pnl[name].to_numpy()    for name, key in _PNL_COLS.items()}
    out |= {key: quotes[name].to_numpy() for name, key in _QUOTE_COLS.items()}
    out |= {key: fills[name].to_numpy()  for name, key in _FILL_COLS.items() if name != "side"}
    out |= {key: quota[name].to_numpy()  for name, key in _QUOTA_COLS.items()}
    out["fill_side"] = side
    return out
