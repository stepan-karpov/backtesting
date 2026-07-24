// ─────────────────────────────────────────────────────────────────────────────
// bindings.cpp — THE ONLY FILE WITH PYTHON INTEROP
//
// Contains:
//   1. PyStrategy  — wraps a Python strategy object, calls on_lob / on_fill
//                    via pybind11. This is the single C++ ↔ Python seam.
//   2. run()       — takes file paths, creates readers, runs C++ Backtester,
//                    writes result CSVs to disk.
//   3. pybind11 module definition.
//
// All business logic lives in engine/*.hpp (pure C++, no Python headers).
// ─────────────────────────────────────────────────────────────────────────────

#include <pybind11/pybind11.h>
#include <pybind11/numpy.h>

#include "engine/backtester.hpp"
#include "engine/execution.hpp"
#include "engine/orderbook.hpp"
#include "engine/reader.hpp"
#include "engine/result.hpp"
#include "engine/strategy.hpp"

#include <cstdint>
#include <string>

namespace py = pybind11;
using namespace pybind11::literals;

// ─── PyStrategy: the C++ ↔ Python seam ───────────────────────────────────────
//
// on_lob: strategy returns list[(side_str, price, size)]; parsed to vector<Order>.
// on_fill: called with primitive args (t_us, side_str, price, size).

class PyStrategy : public StrategyBase {
    py::object _on_lob;
    py::object _on_fill;

public:
    explicit PyStrategy(py::object strategy)
        : _on_lob (strategy.attr("on_lob"))
        , _on_fill(strategy.attr("on_fill"))
    {}

    std::vector<Order> on_lob(const OrderBook& ob, double inventory) override {
        py::object ret = _on_lob(
            py::cast(&ob, py::return_value_policy::reference),
            inventory
        );
        std::vector<Order> orders;
        for (auto item : ret) {
            auto tup = item.cast<py::tuple>();
            const char s = tup[0].cast<std::string>()[0];  // 'b' or 'a'
            orders.push_back({
                s == 'b',
                tup[1].cast<double>(),
                tup[2].cast<double>()
            });
        }
        return orders;
    }

    void on_fill(int64_t t_us, const Fill& f) override {
        static const char* SIDES[] = {"bid", "ask", "markout"};
        _on_fill(t_us, SIDES[f.side], f.price, f.size);
    }
};

// ─── run_arrays(): in-memory numpy arrays → C++ Backtester → CSV files ────────
//
// Market data arrives as pre-parsed numpy arrays (see feed.py). The venue-specific
// parsing lives in Python; the engine only sees normalised columns.
//
//   lob_*   : row-major [n_lob, depth], one snapshot per row (depth = book depth
//             the feed loaded, inferred from the array width, 1..MAX_LOB_LEVELS)
//   trade_* : flat [n_trade], one trade per row
//
// c_style|forcecast guarantees contiguous, correctly-typed buffers (a copy is
// made only if the caller passed a non-contiguous or wrong-dtype array).

using F64Array = py::array_t<double,  py::array::c_style | py::array::forcecast>;
using I64Array = py::array_t<int64_t, py::array::c_style | py::array::forcecast>;
using U8Array  = py::array_t<uint8_t, py::array::c_style | py::array::forcecast>;

static void run_arrays(
    py::object strategy,
    I64Array   lob_ts,
    F64Array   bid_px, F64Array bid_sz,
    F64Array   ask_px, F64Array ask_sz,
    I64Array   trade_ts,
    U8Array    trade_is_sell,
    F64Array   trade_price,
    F64Array   trade_size,
    int64_t    latency_us,
    int64_t    log_interval_us,
    int64_t    quote_log_stride,
    const std::string& output_path
) {
    const int64_t n_lob   = lob_ts.shape(0);
    const int64_t n_trade = trade_ts.shape(0);

    // ── book depth is whatever the feed loaded (array width) ──────────────────
    if (bid_px.ndim() != 2 || bid_px.shape(0) != n_lob)
        throw std::runtime_error("run_arrays: bid_px must have shape [n_lob, depth]");
    const int64_t depth = bid_px.shape(1);
    if (depth < 1 || depth > MAX_LOB_LEVELS)
        throw std::runtime_error(
            "run_arrays: depth must be in [1, " + std::to_string(MAX_LOB_LEVELS) + "]");

    // ── shape checks: fail loudly rather than read out of bounds ──────────────
    auto require_lob_grid = [&](const F64Array& a, const char* name) {
        if (a.ndim() != 2 || a.shape(0) != n_lob || a.shape(1) != depth)
            throw std::runtime_error(
                std::string("run_arrays: ") + name + " must match bid_px shape [n_lob, depth]");
    };
    require_lob_grid(bid_sz, "bid_sz");
    require_lob_grid(ask_px, "ask_px"); require_lob_grid(ask_sz, "ask_sz");

    auto require_trade_col = [&](const auto& a, const char* name) {
        if (a.ndim() != 1 || a.shape(0) != n_trade)
            throw std::runtime_error(
                std::string("run_arrays: ") + name + " must have shape [n_trade]");
    };
    require_trade_col(trade_is_sell, "trade_is_sell");
    require_trade_col(trade_price,   "trade_price");
    require_trade_col(trade_size,    "trade_size");

    PyStrategy           py_strat(std::move(strategy));
    PessimisticExecution exec;
    Backtester           bt(latency_us, log_interval_us, quote_log_stride);

    ArrayLobReader lob(
        lob_ts.data(),
        bid_px.data(), bid_sz.data(), ask_px.data(), ask_sz.data(),
        n_lob, static_cast<int>(depth));
    ArrayTradeReader trades(
        trade_ts.data(), trade_is_sell.data(),
        trade_price.data(), trade_size.data(),
        n_trade);

    RunData data = bt.run(py_strat, exec, lob, trades);
    data.save_csv(output_path);
}

// ─── pybind11 module ──────────────────────────────────────────────────────────

PYBIND11_MODULE(_engine, m) {
    m.doc() = "C++ backtester engine";

    m.attr("MAX_LOB_LEVELS") = MAX_LOB_LEVELS;   // compile-time cap on book depth

    py::class_<OrderBook>(m, "OrderBook")
        .def_property_readonly("best_bid",    &OrderBook::best_bid)
        .def_property_readonly("best_ask",    &OrderBook::best_ask)
        .def_property_readonly("mid",         &OrderBook::mid)
        .def_property_readonly("spread",      &OrderBook::spread)
        .def_property_readonly("timestamp_us",
            [](const OrderBook& ob) { return ob.timestamp_us; })
        .def_property_readonly("bids", [](const OrderBook& ob) {
            py::list r;
            for (int k = 0; k < ob.depth; ++k) {
                const auto& l = ob.bids[k];
                py::list row; row.append(l.price); row.append(l.amount);
                r.append(row);
            }
            return r;
        })
        .def_property_readonly("asks", [](const OrderBook& ob) {
            py::list r;
            for (int k = 0; k < ob.depth; ++k) {
                const auto& l = ob.asks[k];
                py::list row; row.append(l.price); row.append(l.amount);
                r.append(row);
            }
            return r;
        });

    m.def("run_arrays", &run_arrays,
        "strategy"_a,
        "lob_ts"_a,
        "bid_px"_a, "bid_sz"_a, "ask_px"_a, "ask_sz"_a,
        "trade_ts"_a, "trade_is_sell"_a, "trade_price"_a, "trade_size"_a,
        "latency_us"_a, "log_interval_us"_a, "quote_log_stride"_a,
        "output_path"_a
    );
}
