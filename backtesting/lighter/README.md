# backtesting (Lighter)

C++ market-making backtester exposed to Python via pybind11.

The hot loop (order matching, PnL accounting) runs entirely in C++. Python defines
the strategy, loads the market data, and reads results. Lighter's on-disk format
(parquet LOB + zst trades) is parsed Python-side by `LighterFeed`; the engine only
ever sees normalised in-memory arrays.

---

## Build

```bash
cd backtesting/lighter
make          # produces _engine.<suffix>.so
make clean    # remove the .so
```

Requires: `clang++` with C++17, `pybind11`, `numpy`, Python headers. Make sure
`pybind11`/`numpy` are installed in the *same* interpreter `make` uses (`python3`).

---

## Usage

```python
from backtesting.lighter import Strategy, Backtester, LighterFeed, OrderBook
from backtesting.lighter.instruments.visualize import BacktestResult

class MyStrategy(Strategy):
    def on_lob(self, ob: OrderBook, inventory: float) -> None:
        # imperative: issue orders through the gateway; nothing is returned
        self.gateway.create_order(+size, ob.mid - d, ttl_s=2.0)
        self.gateway.create_order(-size, ob.mid + d, ttl_s=2.0)

    def on_fill(self, t_us: int, side: str, price: float, size: float) -> None:
        pass  # optional

feed = LighterFeed(lob_paths, trades_paths)   # parquet + zst → normalised arrays
bt   = Backtester(log_interval_sec=10.0)
prefix = bt.run(MyStrategy(), feed, output_path="results/my_run")

r = BacktestResult(prefix)
display(r.summary_df())
r.plot().show()
```

`lob_paths` / `trades_paths` are lists of Lighter files, e.g.
`data/lighter/DOGE/lob/<YYYYMMDD>/<HH>.parquet` and
`.../trades/<YYYYMMDD>/<HH>.jsonl.zst`.

---

## Strategy API

### `on_lob(ob, inventory) → None`

Called on every LOB snapshot. Issue orders **imperatively** through `self.gateway`;
`on_lob` returns nothing. Orders are **additive** — each `create_order` appends a new
order to the book. An order leaves the book only when it is filled or when its GTT
lifetime (`ttl_s`) elapses. There is no replace-all, so a strategy that quotes must
throttle itself (quote on a schedule, not every tick) or its orders accumulate.

```python
# a 3-level ladder, each order living 2 s
def on_lob(self, ob, inventory):
    for i in range(1, 4):
        self.gateway.create_order(+q, ob.mid - i*d, ttl_s=2.0)
        self.gateway.create_order(-q, ob.mid + i*d, ttl_s=2.0)
```

### `gateway.create_order(size, price, ttl_s=0.0, reduce_only=False)`

The only order verb in the MVP (`cancel_order` / `modify_order` come later).

| Arg | Meaning |
|---|---|
| `size` | signed: `> 0` → bid (buy), `< 0` → ask (sell); a zero size is a no-op |
| `price` | limit price |
| `ttl_s` | GTT lifetime in seconds (a number, default `0.0`); `<= 0` rests until filled (GTC) |
| `reduce_only` | order fills only when it shrinks `|inventory|` |

`self.gateway` is an `OrderGateway`. Subclass it in your notebook to add order-management
policy (tracking, throttling, ladders) on top of the verbs, then assign it in the
strategy's `__init__`.

`OrderBook` fields available from Python:

| Field | Type | Description |
|---|---|---|
| `ob.mid` | float | `(best_bid + best_ask) / 2` |
| `ob.best_bid` | float | top bid price |
| `ob.best_ask` | float | top ask price |
| `ob.spread` | float | `best_ask − best_bid` |
| `ob.timestamp_us` | int | event timestamp in microseconds |
| `ob.bids` | list[list] | `depth` levels `[price, amount]`, descending |
| `ob.asks` | list[list] | `depth` levels `[price, amount]`, ascending |

`depth` is set by the feed (`LighterFeed(..., depth=3)`); indexing `ob.bids`/`ob.asks`
beyond it raises `IndexError`.

### `on_fill(t_us, side, price, size)`

Called after each fill. `side` is `"bid"`, `"ask"`, or `"markout"` (final position close).

---

## LighterFeed API

```python
feed = LighterFeed(lob_paths, trades_paths, depth=3)   # load 3 book levels
feed                # repr: depth, snapshot/trade counts and time spans
feed.arrays()       # dict of normalised numpy arrays passed to the engine
```

Loads and normalises Lighter data on construction:

- ordered by **exchange time** (LOB `sent_ts`, trades `timestamp`), µs;
- `is_maker_ask` → `is_sell` (aggressor side);
- `depth` book levels into `[n, depth]` price/size grids (parquet column projection —
  only the loaded levels are read, keeping long horizons in RAM). The engine reads the
  active depth from the array width; `depth ≤ MAX_LOB_LEVELS` (30).

This is the only venue-aware component: a feed for another venue with the same
`.arrays()` output drops in without engine changes.

---

## Backtester API

```python
Backtester(
    latency_us: int = 0,          # round-trip order latency (µs)
    log_interval_sec: float = 10.0,
    quote_log_stride: int = 50,    # log quotes every N LOB events
    fee_bps: float = 0.0,          # per-fill taker/maker fee, bps of notional
)
prefix = bt.run(strategy, feed, output_path="results/my_run")
```

`fee_bps` charges `fee_bps·1e-4·price·size` from cash on **every real fill**, online in
the engine, so the persisted PnL is **net of fees** (the final markout close is a
valuation mark and pays none). The fee is baked into the run — a different tier is a
different run. `fee_bps = 0` reproduces the gross, fee-free result.

`latency_us` is the **round-trip** latency: a quote decided reacting to an event at
exchange time `T` becomes live on the book only at `T + latency_us`, as a real order
packet would. Until then the previous quotes keep resting and matching. See *Execution
& latency model* below.

`run()` writes three parquet files (typed/binary — see `persistence.py`) and returns the
prefix; load them back with `BacktestResult(prefix)`:

| File | Columns | Logged when |
|---|---|---|
| `{prefix}_pnl.parquet` | `t_us, pnl, inventory` | every `log_interval_sec` |
| `{prefix}_quotes.parquet` | `t_us, bid, ask, mid` | every `quote_log_stride` LOB events |
| `{prefix}_fills.parquet` | `t_us, side, price, size, inventory, mid_at_fill, fee` | on each fill |

---

## BacktestResult API

```python
r = BacktestResult(prefix)
r.summary()      # dict: total_pnl, sharpe_annualized, max_drawdown, n_fills, ...
r.summary_df()   # MultiIndex DataFrame (PnL / Fills / Inventory)
r.plot(tick_size=None)  # 4-panel Plotly figure (tick_size scales quote offsets)
```

Plot panels: quote offsets from mid · PnL · inventory · cumulative fill imbalance.

---

## File Structure

```
backtesting/lighter/
  __init__.py        # exports: Strategy, OrderGateway, Backtester, ...
  strategy.py        # Strategy base + OrderGateway (create_order)
  feed.py            # LighterFeed: parquet/zst → normalised numpy arrays
  backtester.py      # Thin wrapper: calls _engine.run_arrays(), persists, returns prefix
  persistence.py     # save_run / load_run: run arrays ↔ {prefix}_*.parquet
  bindings.cpp       # THE ONLY file with pybind11 — PyStrategy + run_arrays()
  Makefile           # clang++ -O3 -std=c++17 → _engine*.so; make test-all runs the suite
  engine/
    orderbook.hpp    # OrderBook: refresh(), apply_trade(), queue_at()
    execution.hpp    # Order, Fill, PessimisticExecution
    strategy.hpp     # StrategyBase abstract class (pure C++)
    reader.hpp       # ArrayLobReader, ArrayTradeReader — walk in-memory arrays
    backtester.hpp   # Two-pointer merge loop + latency in-flight queue
    result.hpp       # RunData accumulator (returns column arrays to Python)
  instruments/
    visualize/       # BacktestResult: reads parquet → summary_df() + plot()
  tests/             # engine/*.cpp (GoogleTest) + *.py (pytest) — mirror the package
```

---

## Architecture

**Single seam.** `bindings.cpp` is the only file that includes pybind11.
`PyStrategy` wraps the Python strategy object and calls `on_lob` / `on_fill` across
the boundary. All other C++ files (`engine/`) are Python-free.

**Data ingestion.** `LighterFeed` parses Lighter's parquet/zst into normalised numpy
arrays; `run_arrays` hands the raw buffers to the engine, which walks them with
`ArrayLobReader` / `ArrayTradeReader` (no copies beyond the current row). Nothing
in the engine knows about file formats.

**Simulation loop** (`engine/backtester.hpp`): two-pointer merge of the LOB and trade
sources by exchange timestamp. At each step the earlier event is consumed; ties go to
trades first (the LOB snapshot already reflects a post-trade state).

**Execution & latency model** (`engine/backtester.hpp`). The orders a strategy creates
are not applied instantly: each batch is pushed onto a FIFO of in-flight messages,
tagged to land at `T + latency_us`. On every event the engine lands all batches that
have arrived, **appending** their orders to the live resting set (additive — no
replace-all), then reaps any order whose GTT lifetime has elapsed. A GTT order's
`expire_at` is measured from when it lands on the book (`T + latency_us + ttl`).
Several batches can be in flight at once; the live set keeps resting and matching in
the meantime. With `latency_us = 0` orders are live from the next event onward.

**Matching** (`PessimisticExecution`): a trade at the order's **own price** already
counts — a bid matches a sell with `trade_price ≤ bid`, an ask a buy with
`trade_price ≥ ask`; **no strict pierce below/above the quote is required**. Given a
qualifying trade, each live order is assumed last-in-queue at its price level, so a fill
triggers only when the trade volume exceeds the LOB queue ahead of the order
(`trade_amount − queue_at(price)`). All resting levels are matched against the trade
independently; partial fills keep their remainder resting.

---

## Known limitations

Fills are modelled correctly for passive quoting at/behind the touch, and trading fees
are charged online (`Backtester(fee_bps=…)`; net PnL). Be aware of the current bounds:

- **Quotes inside the spread fill trivially.** `queue_at` returns 0 for a price not on a
  book level, so an order posted strictly inside the spread has zero queue ahead and
  fills on any through-trade. Fills for such quotes are optimistic.
- **Independent matching can overfill.** Each level is tested against the full trade
  volume, so one large trade may fill several of your levels beyond its own size.
- **reduce-only uses start-of-trade inventory.** A reduce-only order is capped against
  `inventory` as it stood when the trade arrived, so several reduce-only fills within
  one trade can jointly over-reduce (flip the sign). A corollary of the overfill caveat.
- **Not modelled yet:** latency jitter, nonce-based queue position, tick-size rounding,
  cancel/modify (create-only MVP). Fees are a flat per-fill `fee_bps`, not a tiered or
  maker/taker-split schedule.

Engine behaviour is checked by the test suite under `tests/` — C++ GoogleTest
(`tests/engine/*.cpp`) plus pytest (`tests/*.py`, `tests/instruments/visualize/`); run
both with `make test-all PYTHON=~/venv/bin/python`.
