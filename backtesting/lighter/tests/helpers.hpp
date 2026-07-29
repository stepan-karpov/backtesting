#pragma once
// Shared fixtures for the engine unit tests. Pure C++: the engine headers are
// Python-free, so tests #include them directly and assert on in-memory RunData —
// no pybind, no CSV, no filesystem.

#include "../engine/backtester.hpp"
#include "../engine/execution.hpp"
#include "../engine/orderbook.hpp"
#include "../engine/reader.hpp"
#include "../engine/result.hpp"
#include "../engine/strategy.hpp"

#include <cstdint>
#include <utility>
#include <vector>

namespace t {

// ── Order builders (Order = {is_bid, price, size, ttl_us, expire_at, reduce_only}) ──
inline Order bid(double price, double size, int64_t ttl_us = 0, bool ro = false) {
    return Order{true, price, size, ttl_us, 0, ro};
}
inline Order ask(double price, double size, int64_t ttl_us = 0, bool ro = false) {
    return Order{false, price, size, ttl_us, 0, ro};
}

// ── Book builder. Given levels, then one out-of-reach sentinel per side (deeper
// bids at price 0, deeper asks at a huge price) so apply_trade stops by price
// rather than exhausting the loaded book — a synthetic trade bigger than the top
// level then does not trip the punch-through escalation. ──
inline OrderBook make_book(std::vector<Level> bids, std::vector<Level> asks,
                           int64_t ts = 0) {
    OrderBook ob;
    const int nb = static_cast<int>(bids.size());
    const int na = static_cast<int>(asks.size());
    ob.depth = (nb > na ? nb : na) + 1;                 // +1 sentinel floor/ceiling
    for (int k = 0; k < ob.depth; ++k) {
        ob.bids[k] = k < nb ? bids[k] : Level{0.0,  0.0};
        ob.asks[k] = k < na ? asks[k] : Level{1e18, 0.0};
    }
    ob.timestamp_us = ts;
    return ob;
}

// ── Test strategies (implement the C++ StrategyBase directly) ──
struct OnceStrategy : StrategyBase {         // emit `batch` on the first event only
    std::vector<Order> batch;
    bool fired = false;
    explicit OnceStrategy(std::vector<Order> b) : batch(std::move(b)) {}
    void on_lob(const OrderBook&, double, std::vector<Order>& orders) override {
        if (fired) return;
        fired = true;
        orders.insert(orders.end(), batch.begin(), batch.end());
    }
};

struct EveryTick : StrategyBase {            // emit `batch` on every LOB event
    std::vector<Order> batch;
    explicit EveryTick(std::vector<Order> b) : batch(std::move(b)) {}
    void on_lob(const OrderBook&, double, std::vector<Order>& orders) override {
        orders.insert(orders.end(), batch.begin(), batch.end());
    }
};

// ── Tiny feed builder → contiguous arrays → Backtester → RunData.
// Top-of-book only; deeper levels padded out of reach (see make_book rationale). ──
struct Feed {
    struct Snap { int64_t ts; double bp, bs, ap, as; };
    struct Trd  { int64_t ts; bool is_sell; double price, size; };
    std::vector<Snap> snaps;
    std::vector<Trd>  trades;
    int depth = 2;

    Feed& lob(int64_t ts, double bp, double bs, double ap, double as) {
        snaps.push_back({ts, bp, bs, ap, as});
        return *this;
    }
    Feed& trade(int64_t ts, bool is_sell, double price, double size) {
        trades.push_back({ts, is_sell, price, size});
        return *this;
    }

    RunData run(StrategyBase& strat, int64_t latency_us,
                int64_t log_interval_us = 10'000'000, int64_t quote_stride = 1,
                double fee_bps = 0.0) const {
        const int n = static_cast<int>(snaps.size());
        std::vector<int64_t> lts(n);
        std::vector<float>   bp(n * depth, 0.0f),  bs(n * depth, 0.0f);   // float32 grids
        std::vector<float>   ap(n * depth, 1e18f), as(n * depth, 0.0f);
        for (int i = 0; i < n; ++i) {
            lts[i] = snaps[i].ts;
            bp[i * depth] = snaps[i].bp;  bs[i * depth] = snaps[i].bs;   // level 0
            ap[i * depth] = snaps[i].ap;  as[i * depth] = snaps[i].as;
            // deeper bids stay 0 (below any trade); deeper asks stay 1e18 (above any)
        }
        const int m = static_cast<int>(trades.size());
        std::vector<int64_t> tts(m);
        std::vector<uint8_t> tsell(m);
        std::vector<double>  tpx(m), tsz(m);
        for (int j = 0; j < m; ++j) {
            tts[j]   = trades[j].ts;
            tsell[j] = trades[j].is_sell ? 1 : 0;
            tpx[j]   = trades[j].price;
            tsz[j]   = trades[j].size;
        }
        ArrayLobReader   lob(lts.data(), bp.data(), bs.data(), ap.data(), as.data(), n, depth);
        ArrayTradeReader tr(tts.data(), tsell.data(), tpx.data(), tsz.data(), m);
        PessimisticExecution exec;
        Backtester bt(latency_us, log_interval_us, quote_stride, fee_bps);
        return bt.run(strat, exec, lob, tr);
    }
};

// ── RunData queries. Fill side: 0 = bid, 1 = ask, 2 = markout (final close). ──
inline int n_fills(const RunData& d) {              // real fills, excluding markout
    int c = 0;
    for (auto s : d.fill_side) if (s != 2) ++c;
    return c;
}
inline int n_side(const RunData& d, int side) {
    int c = 0;
    for (auto s : d.fill_side) if (s == side) ++c;
    return c;
}

}  // namespace t
