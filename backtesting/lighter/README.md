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
    def on_lob(self, ob: OrderBook, inventory: float) -> list[tuple]:
        ...
        return [("bid", bid_price, size), ("ask", ask_price, size)]

    def on_fill(self, t_us: int, side: str, price: float, size: float) -> None:
        pass  # optional

feed = LighterFeed(lob_paths, trades_paths)   # parquet + zst → normalised arrays
bt   = Backtester(log_interval_sec=10.0)
prefix = bt.run(MyStrategy(), feed, output_path="results/my_run")

r = BacktestResult(prefix, capital=1000.0)
display(r.summary_df())
r.plot().show()
```

`lob_paths` / `trades_paths` are lists of Lighter files, e.g.
`data/lighter/DOGE/lob/<YYYYMMDD>/<HH>.parquet` and
`.../trades/<YYYYMMDD>/<HH>.jsonl.zst`.

---

## Strategy API

### `on_lob(ob, inventory) → list[tuple]`

Called on every LOB snapshot. Return the **full desired quote set** as a list of
`("bid"|"ask", price, size)` tuples — several levels per side are allowed (a ladder).
Each return replaces the previous set (replace-all); return `[]` to cancel all quotes.

```python
# a 3-level ladder
return [("bid", mid - 1*d, q), ("bid", mid - 2*d, q), ("bid", mid - 3*d, q),
        ("ask", mid + 1*d, q), ("ask", mid + 2*d, q), ("ask", mid + 3*d, q)]
```

`OrderBook` fields available from Python:

| Field | Type | Description |
|---|---|---|
| `ob.mid` | float | `(best_bid + best_ask) / 2` |
| `ob.best_bid` | float | top bid price |
| `ob.best_ask` | float | top ask price |
| `ob.spread` | float | `best_ask − best_bid` |
| `ob.timestamp_us` | int | event timestamp in microseconds |
| `ob.bids` | list[list] | 30 levels `[price, amount]`, descending |
| `ob.asks` | list[list] | 30 levels `[price, amount]`, ascending |

### `on_fill(t_us, side, price, size)`

Called after each fill. `side` is `"bid"`, `"ask"`, or `"markout"` (final position close).

---

## LighterFeed API

```python
feed = LighterFeed(lob_paths, trades_paths)
feed                # repr: snapshot/trade counts and time spans
feed.arrays()       # dict of normalised numpy arrays passed to the engine
```

Loads and normalises Lighter data on construction:

- ordered by **exchange time** (LOB `sent_ts`, trades `timestamp`), µs;
- `is_maker_ask` → `is_sell` (aggressor side);
- 30 book levels into `[n, 30]` price/size grids.

This is the only venue-aware component: a feed for another venue with the same
`.arrays()` output drops in without engine changes.

---

## Backtester API

```python
Backtester(
    latency_us: int = 0,          # round-trip order latency (µs)
    log_interval_sec: float = 10.0,
    quote_log_stride: int = 50,    # log quotes every N LOB events
)
prefix = bt.run(strategy, feed, output_path="results/my_run")
```

`latency_us` is the **round-trip** latency: a quote decided reacting to an event at
exchange time `T` becomes live on the book only at `T + latency_us`, as a real order
packet would. Until then the previous quotes keep resting and matching. See *Execution
& latency model* below.

`run()` writes three CSV files and returns the prefix:

| File | Columns | Logged when |
|---|---|---|
| `{prefix}_pnl.csv` | `t_us, pnl, inventory` | every `log_interval_sec` |
| `{prefix}_quotes.csv` | `t_us, bid, ask, mid` | every `quote_log_stride` LOB events |
| `{prefix}_fills.csv` | `t_us, side, price, size, inventory` | on each fill |

---

## BacktestResult API

```python
r = BacktestResult(prefix, capital=1000.0)
r.summary()      # dict: total_pnl, sharpe_annualized, max_drawdown, n_fills, ...
r.summary_df()   # MultiIndex DataFrame (PnL / Fills / Inventory)
r.plot(tick_size=None)  # 4-panel Plotly figure (tick_size scales quote offsets)
```

Plot panels: quote offsets from mid · PnL · inventory · cumulative fill imbalance.

---

## File Structure

```
backtesting/lighter/
  __init__.py        # exports: Strategy, Backtester, OrderBook, LighterFeed, LOB_LEVELS
  strategy.py        # Strategy base class (Python)
  feed.py            # LighterFeed: parquet/zst → normalised numpy arrays
  backtester.py      # Thin wrapper: calls _engine.run_arrays(), returns prefix
  bindings.cpp       # THE ONLY file with pybind11 — PyStrategy + run_arrays()
  Makefile           # clang++ -O3 -std=c++17 → _engine*.so
  engine/
    orderbook.hpp    # OrderBook: refresh(), apply_trade(), queue_at()
    execution.hpp    # Order, Fill, PessimisticExecution
    strategy.hpp     # StrategyBase abstract class (pure C++)
    reader.hpp       # ArrayLobReader, ArrayTradeReader — walk in-memory arrays
    backtester.hpp   # Two-pointer merge loop + latency in-flight queue
    result.hpp       # RunData accumulator + save_csv(prefix)
  instruments/
    visualize/       # BacktestResult: reads CSVs → summary_df() + plot()
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

**Execution & latency model** (`engine/backtester.hpp`). The strategy's returned quote
set is not applied instantly: it is pushed onto a FIFO of in-flight messages, each
tagged to land at `T + latency_us`. On every event the engine promotes all messages
that have arrived (replace-all — the latest wins) into the live resting set. Several
messages can be in flight at once; the live set keeps resting and matching in the
meantime. With `latency_us = 0` quotes are live from the next event onward.

**Matching** (`PessimisticExecution`): each live order is assumed last-in-queue at its
price level — a fill triggers only when the trade volume exceeds the LOB queue ahead of
the order (`trade_amount − queue_at(price)`). All resting levels are matched against the
trade independently; partial fills keep their remainder resting.

---

## Known limitations (no-fee model)

The simulation is fee-free and models fills correctly for passive quoting at/behind the
touch. Be aware of the current bounds:

- **Quotes inside the spread fill trivially.** `queue_at` returns 0 for a price not on a
  book level, so an order posted strictly inside the spread has zero queue ahead and
  fills on any through-trade. Fills for such quotes are optimistic.
- **Independent matching can overfill.** Each level is tested against the full trade
  volume, so one large trade may fill several of your levels beyond its own size.
- **Not modelled yet:** maker/taker fees, latency jitter, nonce-based queue position,
  tick-size rounding.

Engine behaviour is checked in `research/exchanges/lighter/BacktestingChecks.ipynb`.
