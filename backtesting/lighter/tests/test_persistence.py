import numpy as np
import pandas as pd
import pytest

from backtesting.lighter.persistence import save_run, load_run


def _arrays() -> dict:
    return {
        "pnl_t": np.array([0, 1_000_000], np.int64),
        "pnl_v": np.array([0.0, 1.5]),
        "inv_v": np.array([0.0, 2.0]),
        "qt_t": np.array([0, 500_000, 1_000_000], np.int64),
        "qt_bid": np.array([100.0, np.nan, 100.5]),        # NaN must survive the round-trip
        "qt_ask": np.array([101.0, 101.0, np.nan]),
        "qt_mid": np.array([100.5, 100.7, 100.5]),
        "fill_t": np.array([500_000, 1_000_000], np.int64),
        "fill_side": np.array([0, 2], np.int32),            # bid, markout
        "fill_price": np.array([100.0, 100.5]),
        "fill_size": np.array([2.0, -2.0]),
        "fill_inv": np.array([2.0, 0.0]),
        "fill_mid": np.array([100.5, 100.5]),
        "fill_fee": np.array([0.05, 0.0]),
    }


def test_save_load_roundtrip_is_bit_identical(tmp_path):
    arrays = _arrays()
    save_run(arrays, str(tmp_path / "run"))
    back = load_run(str(tmp_path / "run"))
    assert set(back) == set(arrays)
    for k in arrays:
        np.testing.assert_array_equal(back[k], arrays[k], err_msg=k)   # NaN-aware


def test_save_run_writes_three_parquets_and_returns_prefix(tmp_path):
    prefix = save_run(_arrays(), str(tmp_path / "run"))
    assert prefix == str(tmp_path / "run")
    for name in ("pnl", "quotes", "fills"):
        assert (tmp_path / f"run_{name}.parquet").exists()


def test_csv_fallback_maps_string_side_to_code(tmp_path):
    prefix = str(tmp_path / "legacy")                       # write CSVs, no parquet
    pd.DataFrame({"t_us": [0], "pnl": [1.0], "inventory": [0.0]}).to_csv(f"{prefix}_pnl.csv", index=False)
    pd.DataFrame({"t_us": [0], "bid": [100.0], "ask": [101.0], "mid": [100.5]}).to_csv(f"{prefix}_quotes.csv", index=False)
    pd.DataFrame({"t_us": [0], "side": ["ask"], "price": [101.0], "size": [-1.0],
                  "inventory": [-1.0], "mid_at_fill": [100.5], "fee": [0.01]}).to_csv(f"{prefix}_fills.csv", index=False)
    back = load_run(prefix)                                 # parquet absent → CSV fallback
    assert back["fill_side"].tolist() == [1]                # "ask" string → code 1
    assert back["pnl_v"].tolist() == [1.0]


def test_missing_run_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_run(str(tmp_path / "does_not_exist"))
