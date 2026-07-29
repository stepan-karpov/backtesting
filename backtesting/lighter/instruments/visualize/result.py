from __future__ import annotations

from ...persistence import load_run

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

DARK = "plotly_dark"


class BacktestResult:
    """Loads a persisted backtest run (3 parquet tables) and reports a strategy summary.

    Public interface is unchanged: ``BacktestResult(prefix, capital).summary_df()``.
    Extra knobs are optional keyword-only params with defaults, so the old call
    still works. All the new work is private computation on the loaded tables.

    Two computation regimes, on purpose:

    * **Exact fill-level decomposition** (spread_capture / inventory_mtm / identity):
      inventory is constant between fills, so ``inv·Δmid`` over fill-to-fill legs is
      exact given ``mid_at_fill`` at the nodes — no grid, and the identity closes to
      machine zero *by construction*. Note: exact means exact **in the engine's
      mark-to-market model** (MtM at the mid seen at each fill), not absolute truth —
      the identity checks bookkeeping consistency, not model realism.

    * **1-second grid** for every temporal / distributional statistic. The event log
      is irregular: on thin markets gaps reach tens of minutes, so per-row stats would
      drown active minutes under idle ones. A uniform grid with as-of fill (values are
      piecewise-constant between events, so ffill is exact) fixes the weighting.
      Grid metrics inherit the *logging resolution* of the run: with
      ``quote_log_stride > 1`` or a coarse ``log_interval_sec``, jumps / uptime /
      markout are undersampled — ``summary_df()`` warns when it detects a coarse log.
    """

    def __init__(self, prefix: str, capital: float = 1000.0, *,
                 jump_bps: float = 20.0, jump_window_s: int = 60,
                 markout_s: int = 30, deadband: float | None = None):
        self.capital = capital
        self.jump_bps = jump_bps
        self.jump_window_s = jump_window_s
        self.markout_s = markout_s
        self.deadband = deadband
        self._grid_cache = None
        self._ff_cache = None
        self._mtm_cache = None
        self._build(load_run(prefix))

    def _build(self, a: dict) -> None:
        def to_dt(col):
            return pd.to_datetime(np.asarray(col, np.int64), unit="us")

        self.pnl = pd.Series(
            np.asarray(a["pnl_v"], float), index=to_dt(a["pnl_t"]), name="pnl")
        self.inventory = pd.Series(
            np.asarray(a["inv_v"], float), index=to_dt(a["pnl_t"]), name="inventory")

        self.quotes = pd.DataFrame(
            {"mid": np.asarray(a["qt_mid"], float),
             "bid": np.asarray(a["qt_bid"], float),
             "ask": np.asarray(a["qt_ask"], float)},
            index=to_dt(a["qt_t"]))

        self._has_mid = True   # the engine always emits mid_at_fill
        side = np.array(["bid", "ask", "markout"])[np.asarray(a["fill_side"], np.int64)]
        self.fills = pd.DataFrame(
            {"side": side, "price": np.asarray(a["fill_price"], float),
             "size": np.asarray(a["fill_size"], float),
             "inv_after": np.asarray(a["fill_inv"], float),
             "mid_at_fill": np.asarray(a["fill_mid"], float)},
            index=to_dt(a["fill_t"]))

    # ── grid & fill frames ──────────────────────────────────────────────────────

    @staticmethod
    def _asof(series: pd.Series, idx: pd.DatetimeIndex) -> pd.Series:
        """As-of (backward) sample of `series` onto `idx`; values are piecewise-const."""
        s = series[~series.index.duplicated(keep="last")].sort_index()
        return s.reindex(idx, method="ffill")

    def _grid(self) -> pd.DataFrame:
        if self._grid_cache is not None:
            return self._grid_cache
        start = self.pnl.index[0].floor("1s")
        end = self.pnl.index[-1].ceil("1s")
        idx = pd.date_range(start, end, freq="1s")
        left = pd.DataFrame({"t": idx})

        # As-of (backward) sample each source onto the 1s grid via merge_asof — one sorted
        # linear merge, no index hashing. reindex(ffill) needs a unique index, but the 6.7M
        # quotes index has duplicate-µs rows, so it forced a dedup whose hashing dominated
        # summary. merge_asof handles duplicates natively (takes the last row at or before
        # each grid second = keep-last), and is ~12x faster here. Sources are already sorted
        # (engine emits monotonic timestamps); the stable-sort guard is a defensive fallback
        # that preserves last-per-timestamp semantics if that ever fails.
        def as_of(src):
            if not src["t"].is_monotonic_increasing:
                src = src.sort_values("t", kind="stable")
            return pd.merge_asof(left, src, on="t", direction="backward")

        pnl_g = as_of(pd.DataFrame({"t": self.pnl.index,
                                    "pnl": self.pnl.to_numpy(),
                                    "inventory": self.inventory.to_numpy()}))
        # has_bid/has_ask: presence is notna() on the RAW rows, before the as-of — ffilling
        # the price would carry the last quote through periods we stopped quoting that side.
        q_g = as_of(pd.DataFrame({"t": self.quotes.index,
                                  "mid": self.quotes["mid"].to_numpy(),
                                  "has_bid": self.quotes["bid"].notna().to_numpy().astype(float),
                                  "has_ask": self.quotes["ask"].notna().to_numpy().astype(float)}))

        g = pd.DataFrame(index=idx)
        g["pnl"] = pnl_g["pnl"].to_numpy()
        g["inventory"] = pnl_g["inventory"].to_numpy()
        g["mid"] = q_g["mid"].to_numpy()
        g["has_bid"] = q_g["has_bid"].fillna(0.0).to_numpy() > 0.5
        g["has_ask"] = q_g["has_ask"].fillna(0.0).to_numpy() > 0.5
        self._grid_cache = g
        return g

    def _grid_mtm(self) -> pd.Series:
        """Fill-aware inventory MtM per grid second (a Series on the 1s grid).

        The naive grid MtM ``inventory(t)·Δmid(t)`` charges a whole second's move to the
        boundary position; a mid-second fill changes the position mid-interval, so part of
        the move is attributed to the wrong position — error ~ size·|intra-second Δmid|,
        random signs, growing like √N_fills·size (~$23 at large Q over 11 days). Fix: in a
        second that has fills, split the interval at the fills' exact timestamps and
        ``mid_at_fill``, telescoping over sub-intervals; between fills the position is
        exactly constant, so the split is exact, not an approximation. A fill exactly on a
        boundary τ=t belongs to ``[t, t+1)`` (half-open). Summed over the run this equals
        the exact checkpoint decomposition to machine precision — the boundary grid-mids
        telescope away. Falls back to the naive grid MtM when ``mid_at_fill`` is absent.
        """
        if self._mtm_cache is not None:
            return self._mtm_cache
        g = self._grid()
        M = g["mid"]
        M_next = M.shift(-1)

        if not self._has_mid or not len(self.fills):
            self._mtm_cache = g["inventory"].shift(1) * M.diff()   # degrade to naive
            return self._mtm_cache

        idx = g.index
        f_sec = self.fills.index.floor("1s")
        m = self.fills["mid_at_fill"].to_numpy()
        inv = self.fills["inv_after"].to_numpy()
        inv_before = np.concatenate([[0.0], inv[:-1]])             # position entering each fill

        # inventory carried into each grid second (from fills, as-of ≤ boundary)
        carry = pd.Series(inv, index=self.fills.index)
        carry = carry[~carry.index.duplicated(keep="last")].sort_index()
        i_enter = carry.reindex(idx, method="ffill").fillna(0.0)

        d = i_enter * (M_next - M)                                 # fill-less seconds (baseline)

        fdf = pd.DataFrame({"sec": f_sec, "m": m, "inv": inv, "inv_before": inv_before,
                            "M_s": M.reindex(f_sec).to_numpy(),
                            "M_next": M_next.reindex(f_sec).to_numpy()})

        def _sec(grp):
            mm, ii, ib = grp["m"].to_numpy(), grp["inv"].to_numpy(), grp["inv_before"].to_numpy()
            Ms, Mn = grp["M_s"].iloc[0], grp["M_next"].iloc[0]
            term_start = ib[0] * (mm[0] - Ms)                      # start of second → first fill
            term_mid = (ii[:-1] * np.diff(mm)).sum() if len(mm) > 1 else 0.0   # between fills
            term_end = 0.0 if np.isnan(Mn) else ii[-1] * (Mn - mm[-1])         # last fill → end
            return term_start + term_mid + term_end

        per_sec = fdf.groupby("sec", sort=True)[["m", "inv", "inv_before", "M_s", "M_next"]].apply(_sec)
        d.loc[per_sec.index] = per_sec.values
        # d is indexed by each interval's LEFT boundary [s, s+1); shift to the RIGHT
        # boundary so it aligns with ΔPnL(t)=pnl(t)-pnl(t-1) and the naive diff convention.
        self._mtm_cache = d.shift(1)
        return self._mtm_cache

    def _fill_frame(self) -> pd.DataFrame:
        """Trade fills (side==markout excluded from every statistic) + per-fill edge."""
        if self._ff_cache is not None:
            return self._ff_cache
        f = self.fills[self.fills["side"] != "markout"].copy()
        f["side_sign"] = np.where(f["side"] == "bid", 1.0, -1.0)
        if self._has_mid and len(f):
            m = f["mid_at_fill"].to_numpy()
            sign = f["side_sign"].to_numpy()
            f["captured_bps"] = sign * (m - f["price"].to_numpy()) / m * 1e4
            grid = self._grid()
            key = (f.index + pd.Timedelta(seconds=self.markout_s)).floor("1s")
            mid_fwd = grid["mid"].reindex(key).to_numpy()   # NaN past grid end → too-late fills
            f["markout_bps"] = sign * (mid_fwd - m) / m * 1e4
            f["net_edge_bps"] = f["captured_bps"] + f["markout_bps"]
        else:
            f["captured_bps"] = np.nan
            f["markout_bps"] = np.nan
            f["net_edge_bps"] = np.nan
        self._ff_cache = f
        return f

    # ── exact decomposition (fill checkpoints) ──────────────────────────────────

    def _decomp(self) -> dict:
        total = float(self.pnl.iloc[-1]) if len(self.pnl) else np.nan
        # fill-aware grid inv_mtm: exact within-second attribution (see _grid_mtm).
        # Sums to the exact checkpoint decomposition, so inv_mtm_grid_error → ~0.
        inv_mtm_grid = float(self._grid_mtm().sum(skipna=True))
        out = {"total": total, "inv_mtm_grid": inv_mtm_grid}

        if self._has_mid and len(self.fills):
            ff = self.fills[self.fills["side"] != "markout"]
            sign = np.where(ff["side"] == "bid", 1.0, -1.0)
            m = ff["mid_at_fill"].to_numpy()
            out["spread_capture"] = float(
                (sign * (m - ff["price"].to_numpy()) * ff["size"].to_numpy()).sum())
            # inv held between consecutive fill-mid nodes; markout is the final mid node.
            mids = self.fills["mid_at_fill"].to_numpy()
            inv = self.fills["inv_after"].to_numpy()
            out["inv_mtm_exact"] = float((inv[:-1] * np.diff(mids)).sum()) if len(mids) >= 2 else 0.0
            out["identity_gap"] = total - out["spread_capture"] - out["inv_mtm_exact"]
            out["inv_mtm_grid_error"] = inv_mtm_grid - out["inv_mtm_exact"]
        else:
            out.update(spread_capture=np.nan, inv_mtm_exact=np.nan,
                       identity_gap=np.nan, inv_mtm_grid_error=np.nan)
        return out

    # ── block bootstrap (fixed seed per call → pure function of the CSVs) ────────

    @staticmethod
    def _block_bootstrap(values, block_key, n_boot: int = 500):
        v = np.asarray(values, dtype=float)
        k = np.asarray(block_key)
        mask = ~np.isnan(v)
        v, k = v[mask], k[mask]
        if v.size == 0:
            return (np.nan, np.nan)
        blocks = [v[k == b] for b in pd.unique(k)]
        nb = len(blocks)
        rng = np.random.default_rng(0)
        means = np.empty(n_boot)
        for i in range(n_boot):
            pick = rng.integers(0, nb, nb)
            means[i] = np.concatenate([blocks[j] for j in pick]).mean()
        lo, hi = np.percentile(means, [2.5, 97.5])
        return (float(lo), float(hi))

    def _worst_unrealized(self, g: pd.DataFrame) -> float:
        """min over the grid of inventory·(mid − avg_entry); avg_entry = VWAP of the
        open position (add → VWAP, reduce → keep, flip → reset to the flipping price)."""
        tf = self.fills[self.fills["side"].isin(["bid", "ask"])]
        if not len(tf):
            return np.nan
        sides, prices, sizes = tf["side"].to_numpy(), tf["price"].to_numpy(), tf["size"].to_numpy()
        p = e = 0.0
        entries = np.empty(len(tf))
        for i in range(len(tf)):
            q = (1.0 if sides[i] == "bid" else -1.0) * sizes[i]
            price = prices[i]
            if p == 0.0 or (p > 0) == (q > 0):                 # open / add same side
                e = (e * abs(p) + price * abs(q)) / (abs(p) + abs(q))
                p += q
            elif abs(q) < abs(p):                              # partial reduce, keep VWAP
                p += q
            elif abs(q) == abs(p):                             # flat
                p, e = 0.0, 0.0
            else:                                              # flip: reset to fill price
                p += q
                e = price
            entries[i] = e
        entry_g = self._asof(pd.Series(entries, index=tf.index), g.index)
        unreal = g["inventory"] * (g["mid"] - entry_g)
        return float(unreal.min(skipna=True)) if unreal.notna().any() else np.nan

    # ── metrics ─────────────────────────────────────────────────────────────────

    def _compute(self) -> tuple[dict, dict]:
        v: dict = {}
        notes: dict = {}
        g = self._grid()
        ff = self._fill_frame()
        n_days = max((g.index[-1] - g.index[0]).total_seconds() / 86400.0, 1e-9)
        tot = float(self.pnl.iloc[-1]) if len(self.pnl) else 0.0
        v["total_pnl"] = tot
        v["n_days"] = float(n_days)      # run span in days (used by downstream economic-scale gates)

        # ---- PnL, temporal (grid) ----
        pnl_g = g["pnl"].dropna()
        if len(pnl_g) >= 2:
            ret = pnl_g.diff().dropna().to_numpy()
            std = float(ret.std())
            obs_per_year = 365.25 * 86400.0            # 1-s grid → one obs per second
            v["sharpe_annualized"] = float(ret.mean() / std * np.sqrt(obs_per_year)) if std > 0 else 0.0
            v["max_drawdown"] = float((pnl_g - np.maximum.accumulate(pnl_g)).min())
        else:
            v["sharpe_annualized"] = 0.0
            v["max_drawdown"] = 0.0

        # ---- exact decomposition ----
        d = self._decomp()
        v["spread_capture_usd"] = d["spread_capture"]
        v["inv_mtm_usd"] = d["inv_mtm_exact"]
        v["identity_gap_usd"] = d["identity_gap"]
        v["inv_mtm_grid_error_usd"] = d["inv_mtm_grid_error"]
        denom = abs(tot) if abs(tot) > 1e-12 else np.nan
        v["spread_capture_pct"] = d["spread_capture"] / denom * 100 if self._has_mid else np.nan
        v["inv_mtm_pct"] = d["inv_mtm_exact"] / denom * 100 if self._has_mid else np.nan

        # ---- per-fill edge + CI ----
        ne = ff["net_edge_bps"].to_numpy() if len(ff) else np.array([])
        mo = ff["markout_bps"].to_numpy() if len(ff) else np.array([])
        v["net_edge_per_fill_bps"] = float(np.nanmean(ne)) if ne.size and not np.all(np.isnan(ne)) else np.nan
        v["markout_30s_bps"] = float(np.nanmean(mo)) if mo.size and not np.all(np.isnan(mo)) else np.nan
        if len(ff) and self._has_mid:
            v["net_edge_ci_lo"], v["net_edge_ci_hi"] = self._block_bootstrap(ne, ff.index.floor("1h").asi8)
        else:
            v["net_edge_ci_lo"] = v["net_edge_ci_hi"] = np.nan

        # ---- variance / correlation (grid) ----
        # d_mtm is the fill-aware inventory MtM per second (see _grid_mtm); the 1 − corr²
        # definition is unchanged, only the series it consumes is more accurate.
        pair = pd.concat([g["pnl"].diff().rename("dpnl"),
                          self._grid_mtm().rename("dmtm")], axis=1).dropna()
        if len(pair) >= 2 and pair["dpnl"].std() > 0 and pair["dmtm"].std() > 0:
            r = float(pair["dpnl"].corr(pair["dmtm"]))
            v["capture_share_of_variance"] = 1.0 - r * r
        else:
            v["capture_share_of_variance"] = np.nan
        hourly = g["pnl"].diff().resample("1h").sum()
        hret = g["mid"].resample("1h").last().pct_change()
        hh = pd.concat([hourly, hret], axis=1).dropna()
        if len(hh) >= 2 and hh.iloc[:, 0].std() > 0 and hh.iloc[:, 1].std() > 0:
            v["corr_hourly_pnl_return"] = float(hh.iloc[:, 0].corr(hh.iloc[:, 1]))
        else:
            v["corr_hourly_pnl_return"] = np.nan

        # ---- fills (counts, not temporal) ----
        tf = self.fills[self.fills["side"].isin(["bid", "ask"])]
        nb = int((tf["side"] == "bid").sum())
        na = int((tf["side"] == "ask").sum())
        v["n_fills"], v["n_bid_fills"], v["n_ask_fills"] = nb + na, nb, na
        v["fill_imbalance"] = (nb - na) / (nb + na) if (nb + na) > 0 else 0.0
        v["turnover"] = float(tf["size"].sum())
        v["turnover_usd"] = float((tf["price"] * tf["size"]).sum())
        # captured spread per unit notional traded (notional-weighted captured bps)
        v["capture_yield_bps"] = (
            d["spread_capture"] / v["turnover_usd"] * 1e4
            if self._has_mid and v["turnover_usd"] > 0 else np.nan)

        # ---- inventory (grid) ----
        inv = g["inventory"]
        v["avg_inventory"] = float(inv.mean())
        v["std_inventory"] = float(inv.std())
        v["max_abs_inventory"] = float(inv.abs().max()) if len(inv) else 0.0
        v["mean_abs_inventory"] = float(inv.abs().mean())
        v["p90_abs_inventory"] = float(inv.abs().quantile(0.9))
        mx = v["max_abs_inventory"]
        v["time_at_90pct_max_inv_pct"] = float((inv.abs() >= 0.9 * mx).mean() * 100) if mx > 0 else np.nan

        # deadband is a DOLLAR notional threshold (default $20): ignore position wiggles
        # worth less than this, so zero-crossings / excursions stay comparable across
        # assets of very different coin price. Compare |inv·mid| — the position's $ value.
        deadband_usd = self.deadband if self.deadband is not None else 20.0
        outside = (inv.abs() * g["mid"]) > deadband_usd
        grp = outside.groupby((outside != outside.shift()).cumsum())
        exc = grp.size()[grp.first()]                          # lengths (s) of |inv|>band runs
        v["median_excursion_min"] = float(exc.median() / 60.0) if len(exc) else np.nan
        sig = np.sign(inv[outside].to_numpy())
        sig = sig[sig != 0]
        crossings = int((np.diff(sig) != 0).sum()) if sig.size > 1 else 0
        v["zero_crossings_per_day"] = crossings / n_days
        v["worst_unrealized_usd"] = self._worst_unrealized(g)

        # ---- tails (grid) ----
        ret_bps = g["mid"].pct_change() * 1e4
        is_jump = ret_bps.abs() > self.jump_bps
        v["n_jumps"] = int(is_jump.sum())
        if v["n_jumps"] > 0:
            w = int(self.jump_window_s)
            in_win = is_jump.astype(float).rolling(2 * w + 1, center=True, min_periods=1).max() > 0.5
            pnl_in = float(g["pnl"].diff()[in_win].sum())
            v["pnl_in_jump_windows_usd"] = pnl_in
            v["pnl_in_jump_windows_pct"] = pnl_in / denom * 100 if not np.isnan(denom) else np.nan
        else:
            v["pnl_in_jump_windows_usd"] = 0.0
            v["pnl_in_jump_windows_pct"] = np.nan
            notes["pnl_in_jump_windows ($)"] = "no jumps"
        v["worst_hour_usd"] = float(hourly.min()) if len(hourly) else np.nan
        v["p5_hourly_usd"] = float(hourly.quantile(0.05)) if len(hourly) else np.nan

        # ---- ops (grid + quote log) ----
        v["two_sided_uptime_pct"] = float((g["has_bid"] & g["has_ask"]).mean() * 100)
        changed = ((self.quotes["bid"] != self.quotes["bid"].shift()) |
                   (self.quotes["ask"] != self.quotes["ask"].shift())).astype(float)
        # Quote changes per minute. groupby(floor) not resample("1min"): resample calls
        # inferred_freq on the 6.7M quotes index (~0.7s/run — half of summary), groupby bins
        # directly. Reindex to the full minute span so quiet minutes count as 0, matching
        # resample's zero-filled bins. Verified bit-identical (index, values, p50/p95).
        counts = changed.groupby(self.quotes.index.floor("1min")).sum()
        if len(counts):
            full = pd.date_range(counts.index.min(), counts.index.max(), freq="1min")
            per_min = counts.reindex(full, fill_value=0.0)
        else:
            per_min = counts
        v["quote_updates_min_p50"] = float(per_min.median()) if len(per_min) else np.nan
        v["quote_updates_min_p95"] = float(per_min.quantile(0.95)) if len(per_min) else np.nan

        # ---- notes ----
        notes["zero_crossings / day"] = f"deadband=${deadband_usd:.4g} notional"
        notes["median_excursion (min)"] = f"deadband=${deadband_usd:.4g} notional"
        notes["quote_updates/min p50"] = "proxy (quotes.csv stride-sampled)"
        notes["quote_updates/min p95"] = "proxy (quotes.csv stride-sampled)"
        notes.setdefault("two_sided_uptime (%)", "quotes as-of between log strides")

        # coarse-log heuristic: median quote-log interval ≫ 1-s grid → undersampled.
        # Exposed as columns too — the direct coarse-log gate for downstream screening
        # (inv_mtm_grid_error is now fill-aware ≈ 0 and no longer detects coarse logs).
        med_q_dt = float(np.median(np.diff(self.quotes.index.asi8)) / 1e9) if len(self.quotes) > 1 else np.nan
        med_p_dt = float(np.median(np.diff(self.pnl.index.asi8)) / 1e9) if len(self.pnl) > 1 else np.nan
        v["median_quote_interval_s"] = med_q_dt
        v["median_pnl_interval_s"] = med_p_dt
        if not np.isnan(med_q_dt) and med_q_dt > 1.5:
            cnote = f"coarse quote log (median {med_q_dt:.1f}s > 1s grid); undersampled"
            for k in ("n_jumps", "two_sided_uptime (%)", "markout_30s (bps)"):
                notes[k] = cnote
        if not np.isnan(med_p_dt) and med_p_dt > 1.5:
            notes["sharpe_annualized"] = f"grid from log_interval≈{med_p_dt:.1f}s (coarse)"

        # markout horizon is a market state — always as-of from the grid
        notes.setdefault("markout_30s (bps)", "horizon mid: grid as-of")

        if not self._has_mid:
            notes["capture_share_of_variance"] = "fill-aware unavailable (no mid_at_fill); naive grid d_mtm"
            mnote = "needs mid_at_fill (rebuild engine / rerun)"
            for k in ("spread_capture ($)", "spread_capture (% of total)", "capture_yield (bps)",
                      "inventory_mtm ($)", "inventory_mtm (% of total)", "identity_gap ($)",
                      "inv_mtm_grid_error ($)", "net_edge_per_fill (bps)",
                      "net_edge CI95 [lo, hi]", "markout_30s (bps)"):
                notes[k] = mnote
        return v, notes

    # ── read API ────────────────────────────────────────────────────────────────

    def summary(self) -> dict:
        """Raw numeric metrics (superset of the legacy keys)."""
        return self._compute()[0]

    def summary_df(self) -> pd.DataFrame:
        v, notes = self._compute()
        c = self.capital

        def num(x):
            return x is not None and not (isinstance(x, float) and np.isnan(x))

        def fmt(kind, key):
            x = v.get(key)
            if not num(x):
                return "NaN"
            return {
                "usd4":  lambda: f"{x:+,.4f}",
                "usd2":  lambda: f"{x:+,.2f}",
                "pct2":  lambda: f"{x:+.2f}%",
                "bps":   lambda: f"{x:+.2f}",
                "ratio": lambda: f"{x:+.2f}",
                "share": lambda: f"{x:+.4f}",
                "count": lambda: f"{int(x):,}",
                "s4":    lambda: f"{x:+.4f}",
                "a4":    lambda: f"{x:.4f}",
                "a2":    lambda: f"{x:.2f}",
            }[kind]()

        def pctof(key):
            x = v.get(key)
            return f"{x / c * 100:+.4f}%" if num(x) else "NaN"

        def ci():
            lo, hi = v.get("net_edge_ci_lo"), v.get("net_edge_ci_hi")
            return f"[{lo:+.2f}, {hi:+.2f}]" if num(lo) and num(hi) else "NaN"

        spec = [
            ("PnL", "total_pnl ($)",                  fmt("usd4", "total_pnl")),
            # ("PnL", "total_pnl (%)",                  pctof("total_pnl")),
            ("PnL", "sharpe_annualized",              fmt("ratio", "sharpe_annualized")),
            ("PnL", "max_drawdown ($)",               fmt("usd4", "max_drawdown")),
            # ("PnL", "max_drawdown (%)",               pctof("max_drawdown")),
            ("PnL", "spread_capture ($)",             fmt("usd4", "spread_capture_usd")),
            ("PnL", "spread_capture (% of total)",    fmt("pct2", "spread_capture_pct")),
            ("PnL", "capture_yield (bps)",            fmt("bps", "capture_yield_bps")),
            ("PnL", "inventory_mtm ($)",              fmt("usd4", "inv_mtm_usd")),
            ("PnL", "inventory_mtm (% of total)",     fmt("pct2", "inv_mtm_pct")),
            ("PnL", "identity_gap ($)",               fmt("usd4", "identity_gap_usd")),
            ("PnL", "inv_mtm_grid_error ($)",         fmt("usd4", "inv_mtm_grid_error_usd")),
            ("PnL", "net_edge_per_fill (bps)",        fmt("bps", "net_edge_per_fill_bps")),
            ("PnL", "net_edge CI95 [lo, hi]",         ci()),
            ("PnL", "markout_30s (bps)",              fmt("bps", "markout_30s_bps")),
            ("PnL", "capture_share_of_variance",      fmt("share", "capture_share_of_variance")),
            ("PnL", "corr(hourly_pnl, hourly_return)", fmt("share", "corr_hourly_pnl_return")),
            ("Fills", "n_fills",                      fmt("count", "n_fills")),
            ("Fills", "n_bid_fills",                  fmt("count", "n_bid_fills")),
            ("Fills", "n_ask_fills",                  fmt("count", "n_ask_fills")),
            ("Fills", "fill_imbalance",               fmt("s4", "fill_imbalance")),
            ("Inventory", "avg_inventory",            fmt("s4", "avg_inventory")),
            ("Inventory", "std_inventory",            fmt("a4", "std_inventory")),
            ("Inventory", "max_abs_inventory",        fmt("a4", "max_abs_inventory")),
            ("Inventory", "turnover ($)",             fmt("usd2", "turnover_usd")),
            ("Inventory", "mean |inv|",               fmt("a4", "mean_abs_inventory")),
            ("Inventory", "p90 |inv|",                fmt("a4", "p90_abs_inventory")),
            ("Inventory", "zero_crossings / day",     fmt("a4", "zero_crossings_per_day")),
            ("Inventory", "median_excursion (min)",   fmt("a4", "median_excursion_min")),
            ("Inventory", "worst_unrealized ($)",     fmt("usd4", "worst_unrealized_usd")),
            ("Inventory", "time at ≥90% max|inv| (%)", fmt("a2", "time_at_90pct_max_inv_pct")),
            ("Tails", "n_jumps",                      fmt("count", "n_jumps")),
            ("Tails", "pnl_in_jump_windows ($)",      fmt("usd4", "pnl_in_jump_windows_usd")),
            ("Tails", "pnl_in_jump_windows (% of |total|)", fmt("pct2", "pnl_in_jump_windows_pct")),
            ("Tails", "worst_hour ($)",               fmt("usd4", "worst_hour_usd")),
            ("Tails", "p5_hourly ($)",                fmt("usd4", "p5_hourly_usd")),
            ("Ops", "two_sided_uptime (%)",           fmt("a2", "two_sided_uptime_pct")),
            ("Ops", "quote_updates/min p50",          fmt("a2", "quote_updates_min_p50")),
            ("Ops", "quote_updates/min p95",          fmt("a2", "quote_updates_min_p95")),
        ]

        idx = pd.MultiIndex.from_tuples([(g_, m_) for g_, m_, _ in spec], names=["group", "metric"])
        return pd.DataFrame(
            {"value": [val for _, _, val in spec],
             "note":  [notes.get(m_, "") for _, m_, _ in spec]},
            index=idx)

    def plot(self, height: int = 1100, tick_size: float | None = None,
             resample: str = "1min"):
        trade_fills = self.fills[self.fills["side"].isin(["bid", "ask"])]

        # --- PnL decomposition: spread capture vs inventory drift ---
        spread_pnl = pd.Series(dtype=float)
        inv_drift  = pd.Series(dtype=float)
        if len(trade_fills) and len(self.quotes):
            fills_m = pd.merge_asof(
                trade_fills[["side", "price", "size"]].sort_index(),
                self.quotes[["mid"]].sort_index(),
                left_index=True, right_index=True,
                direction="backward",
            ).dropna(subset=["mid"])
            per_fill = np.where(
                fills_m["side"] == "bid",
                (fills_m["mid"] - fills_m["price"]) * fills_m["size"],
                (fills_m["price"] - fills_m["mid"]) * fills_m["size"],
            )
            cum_spread = pd.Series(per_fill.cumsum(), index=fills_m.index)
            cs_df  = pd.DataFrame({"val": cum_spread.values}, index=cum_spread.index)
            pnl_df = pd.DataFrame({"t": self.pnl.index}, index=self.pnl.index)
            merged = pd.merge_asof(
                pnl_df.sort_index(), cs_df.sort_index(),
                left_index=True, right_index=True,
                direction="backward",
            )
            spread_pnl = pd.Series(merged["val"].fillna(0.0).values, index=self.pnl.index)
            inv_drift  = self.pnl - spread_pnl

        # --- Downsample PnL / inventory to target resolution ---
        pnl_ds = self.pnl.resample(resample).last().dropna()
        inv_ds = self.inventory.resample(resample).last().dropna()
        if len(spread_pnl):
            spread_pnl = spread_pnl.resample(resample).last().dropna()
            inv_drift  = inv_drift.resample(resample).last().dropna()

        # --- Quote offsets from mid ---
        if len(self.quotes):
            divisor    = tick_size if tick_size else 1.0
            ylabel_off = "ticks" if tick_size else "price units"
            qt_ds   = self.quotes.resample(resample).last().dropna()
            bid_off = (qt_ds["bid"] - qt_ds["mid"]) / divisor
            ask_off = (qt_ds["ask"] - qt_ds["mid"]) / divisor
        else:
            ylabel_off = ""
            qt_ds = pd.DataFrame()

        # --- Cumulative signed fill imbalance (resampled to target resolution) ---
        cum_imbalance = pd.Series(dtype=float)
        if len(trade_fills) > 1:
            signed        = trade_fills["side"].map({"bid": 1.0, "ask": -1.0})
            cum_imbalance = signed.cumsum().resample(resample).last().dropna()

        fig = make_subplots(
            rows=4, cols=1, shared_xaxes=True,
            row_heights=[0.15, 0.30, 0.25, 0.30],
            vertical_spacing=0.06,
            subplot_titles=(
                f"Quote offset from mid ({ylabel_off})",
                "PnL",
                "Inventory",
                "Cumulative fill imbalance (bid fills − ask fills)",
            ),
        )

        if len(qt_ds):
            fig.add_trace(go.Scatter(
                x=qt_ds.index, y=ask_off,
                mode="lines", name="ask offset",
                line=dict(width=1, dash="dot", color="red")), row=1, col=1)
            fig.add_trace(go.Scatter(
                x=qt_ds.index, y=bid_off,
                mode="lines", name="bid offset",
                line=dict(width=1, dash="dot", color="lime")), row=1, col=1)
            fig.add_hline(y=0, line=dict(width=0.5, dash="dot", color="gray"), row=1, col=1)

        fig.add_trace(go.Scatter(
            x=pnl_ds.index, y=pnl_ds.values,
            mode="lines", name="total PnL",
            line=dict(color="cyan", width=2)), row=2, col=1)
        if len(spread_pnl):
            fig.add_trace(go.Scatter(
                x=spread_pnl.index, y=spread_pnl.values,
                mode="lines", name="spread capture",
                line=dict(color="lime", dash="dot")), row=2, col=1)
            fig.add_trace(go.Scatter(
                x=inv_drift.index, y=inv_drift.values,
                mode="lines", name="inventory drift",
                line=dict(color="orange", dash="dot")), row=2, col=1)
        fig.add_hline(y=0, line=dict(width=0.5, dash="dot", color="gray"), row=2, col=1)
        fig.update_yaxes(title_text="PnL ($)", row=2, col=1)

        fig.add_trace(go.Scatter(
            x=inv_ds.index, y=inv_ds.values,
            mode="lines", name="inventory",
            line=dict(color="orange")), row=3, col=1)
        fig.add_hline(y=0, line=dict(width=0.5, dash="dot", color="gray"), row=3, col=1)

        if len(cum_imbalance):
            fig.add_trace(go.Scatter(
                x=cum_imbalance.index, y=cum_imbalance.values,
                mode="lines", name="cum imbalance",
                line=dict(color="magenta")), row=4, col=1)
            fig.add_hline(y=0, line=dict(width=0.5, dash="dot", color="gray"), row=4, col=1)

        fig.update_layout(
            template=DARK, height=height, showlegend=True,
            legend=dict(orientation="v", x=1.02, y=1, xanchor="left", yanchor="top"),
            margin=dict(r=160),
        )
        return fig

    def plot_price(self, height: int = 500, resample: str = "1min",
                   show_quotes: bool = True, show_fills: bool = False):
        """Price chart: mid over time, with the strategy's bid/ask quote curves.

        Returns a Plotly figure — use like ``s.plot_price().show()``.
          resample    : line resolution (pass "1s"/"5min" for finer/coarser).
          show_quotes : draw the strategy's own bid/ask quote curves (sit near mid —
                        zoom in to see the offset).
          show_fills  : overlay fills as markers (buy = lime ▲, sell = red ▼); off by default.
        """
        fig = go.Figure()

        if len(self.quotes):
            mid = self.quotes["mid"].resample(resample).last().dropna()
            fig.add_trace(go.Scatter(
                x=mid.index, y=mid.values, mode="lines",
                name="mid", line=dict(color="cyan", width=1)))
            if show_quotes:
                qb = self.quotes["bid"].resample(resample).last()
                qa = self.quotes["ask"].resample(resample).last()
                fig.add_trace(go.Scatter(
                    x=qb.index, y=qb.values, mode="lines", name="bid quote",
                    line=dict(color="lime", width=1)))
                fig.add_trace(go.Scatter(
                    x=qa.index, y=qa.values, mode="lines", name="ask quote",
                    line=dict(color="red", width=1)))

        if show_fills and len(self.fills):
            tf = self.fills[self.fills["side"].isin(["bid", "ask"])]
            buys, sells = tf[tf["side"] == "bid"], tf[tf["side"] == "ask"]
            fig.add_trace(go.Scatter(
                x=buys.index, y=buys["price"], mode="markers", name="buy fill",
                marker=dict(color="lime", symbol="triangle-up", size=7,
                            line=dict(color="white", width=0.5))))
            fig.add_trace(go.Scatter(
                x=sells.index, y=sells["price"], mode="markers", name="sell fill",
                marker=dict(color="red", symbol="triangle-down", size=7,
                            line=dict(color="white", width=0.5))))

        fig.update_layout(
            template=DARK, height=height, showlegend=True, title="Price & fills",
            yaxis_title="price",
            legend=dict(orientation="v", x=1.02, y=1, xanchor="left", yanchor="top"),
            margin=dict(r=140),
        )
        return fig
