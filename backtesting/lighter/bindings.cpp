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

class PyStrategy : public StrategyBase {
    py::object _lob_step;
    py::object _on_fill;

public:
    explicit PyStrategy(py::object strategy)
        : _lob_step(strategy.attr("_lob_step"))
        , _on_fill (strategy.attr("on_fill"))
    {}

    void on_lob(const OrderBook& ob, double inventory, std::vector<Order>& orders) override {
        py::object pending = _lob_step(
            py::cast(&ob, py::return_value_policy::reference), inventory);

        for (auto item : pending) {
            const py::tuple o = item.cast<py::tuple>();      // (size, price, ttl_s, reduce_only)
            const double  size = o[0].cast<double>();        // signed: sign = side
            const double  px   = o[1].cast<double>();
            const double  ttl  = o[2].cast<double>();        // seconds; <= 0 = GTC
            const bool    ro   = o[3].cast<bool>();
            const int64_t ttl_us = ttl > 0.0 ? static_cast<int64_t>(ttl * 1e6) : 0;
            orders.push_back({size > 0.0, px, size < 0.0 ? -size : size,
                              ttl_us, /*expire_at=*/0, ro});
        }
    }

    void on_fill(int64_t t_us, const Fill& f) override {
        static const char* SIDES[] = {"bid", "ask", "markout"};
        _on_fill(t_us, SIDES[f.side], f.price, f.size);
    }
};

// ─── run_arrays(): in-memory numpy arrays → C++ Backtester → numpy arrays ─────

using F64Array = py::array_t<double,  py::array::c_style | py::array::forcecast>;
using F32Array = py::array_t<float,   py::array::c_style | py::array::forcecast>;
using I64Array = py::array_t<int64_t, py::array::c_style | py::array::forcecast>;
using U8Array  = py::array_t<uint8_t, py::array::c_style | py::array::forcecast>;

template <class T>
static py::array_t<T> to_np(const std::vector<T>& v) {
    return py::array_t<T>(static_cast<py::ssize_t>(v.size()), v.data());
}

static int64_t require_valid_shapes(
    const I64Array& lob_ts,
    const F32Array& bid_px, const F32Array& bid_sz,
    const F32Array& ask_px, const F32Array& ask_sz,
    const I64Array& trade_ts,
    const U8Array&  trade_is_sell,
    const F64Array& trade_price, const F64Array& trade_size)
{
    const int64_t n_lob   = lob_ts.shape(0);
    const int64_t n_trade = trade_ts.shape(0);

    if (bid_px.ndim() != 2 || bid_px.shape(0) != n_lob)
        throw std::runtime_error("run_arrays: bid_px must have shape [n_lob, depth]");
    const int64_t depth = bid_px.shape(1);
    if (depth < 1 || depth > MAX_LOB_LEVELS)
        throw std::runtime_error(
            "run_arrays: depth must be in [1, " + std::to_string(MAX_LOB_LEVELS) + "]");

    auto require_lob_grid = [&](const F32Array& a, const char* name) {
        if (a.ndim() != 2 || a.shape(0) != n_lob || a.shape(1) != depth)
            throw std::runtime_error(
                std::string("run_arrays: ") + name + " must match bid_px shape [n_lob, depth]");
    };
    require_lob_grid(bid_sz, "bid_sz");
    require_lob_grid(ask_px, "ask_px");
    require_lob_grid(ask_sz, "ask_sz");

    auto require_trade_col = [&](const auto& a, const char* name) {
        if (a.ndim() != 1 || a.shape(0) != n_trade)
            throw std::runtime_error(
                std::string("run_arrays: ") + name + " must have shape [n_trade]");
    };
    require_trade_col(trade_is_sell, "trade_is_sell");
    require_trade_col(trade_price,   "trade_price");
    require_trade_col(trade_size,    "trade_size");

    return depth;
}

static py::dict run_arrays(
    py::object strategy,
    I64Array   lob_ts,
    F32Array   bid_px, F32Array bid_sz,
    F32Array   ask_px, F32Array ask_sz,
    I64Array   trade_ts,
    U8Array    trade_is_sell,
    F64Array   trade_price,
    F64Array   trade_size,
    int64_t    latency_us,
    int64_t    log_interval_us,
    int64_t    quote_log_stride
) {
    const int64_t depth   = require_valid_shapes(lob_ts, bid_px, bid_sz, ask_px, ask_sz,
                                                 trade_ts, trade_is_sell, trade_price, trade_size);
    const int64_t n_lob   = lob_ts.shape(0);
    const int64_t n_trade = trade_ts.shape(0);

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

    // Hand the RunData columns back as numpy arrays (see to_np). No file I/O here —
    // the caller (Backtester.run) decides whether to persist and in what format.
    py::dict out;
    out["pnl_t"]      = to_np(data.pnl_t);
    out["pnl_v"]      = to_np(data.pnl_v);
    out["inv_v"]      = to_np(data.inv_v);
    out["qt_t"]       = to_np(data.qt_t);
    out["qt_bid"]     = to_np(data.qt_bid);
    out["qt_ask"]     = to_np(data.qt_ask);
    out["qt_mid"]     = to_np(data.qt_mid);
    out["fill_t"]     = to_np(data.fill_t);
    out["fill_side"]  = to_np(data.fill_side);
    out["fill_price"] = to_np(data.fill_price);
    out["fill_size"]  = to_np(data.fill_size);
    out["fill_inv"]   = to_np(data.fill_inv);
    out["fill_mid"]   = to_np(data.fill_mid);
    return out;
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
        "latency_us"_a, "log_interval_us"_a, "quote_log_stride"_a
    );
}
