#pragma once
#include "orderbook.hpp"
#include <algorithm>
#include <vector>

// ─── Order / Fill ─────────────────────────────────────────────────────────────

struct Order {
    bool   is_bid;
    double price;
    double size;
};

struct Fill {
    // 0 = bid, 1 = ask, 2 = markout
    int    side;
    double price;
    double size;
};

// ─── ExecutionModel (abstract) ────────────────────────────────────────────────

class ExecutionModel {
public:
    virtual ~ExecutionModel() = default;

    // Match the live resting orders against one incoming trade.
    //   live       — resting orders; filled orders are shrunk / removed in-place
    //   ob         — apply_trade called in-place
    //   fills_out  — filled events appended here
    virtual void match(
        std::vector<Order>& live,
        OrderBook& ob,
        bool is_sell, double trade_price, double trade_amount,
        std::vector<Fill>& fills_out
    ) = 0;
};

// ─── PessimisticExecution ─────────────────────────────────────────────────────
// We are last in queue at our price level: an order fills only if the trade
// volume exceeds the LOB volume displayed at that price.
//
// Each resting order is tested independently against the full trade volume.
// overfill caveat: a single large trade can therefore fill several of our levels
// beyond its own size. Acceptable for now (see design decision); switch to a
// shared volume budget if fills look implausibly high.

class PessimisticExecution : public ExecutionModel {
public:
    void match(
        std::vector<Order>& live,
        OrderBook& ob,
        bool is_sell, double trade_price, double trade_amount,
        std::vector<Fill>& fills_out
    ) override {
        for (auto& o : live) {
            if (o.size <= 0.0) continue;

            if (is_sell && o.is_bid && trade_price <= o.price) {
                double leftover = trade_amount - ob.queue_at(true, o.price);
                if (leftover > 0.0) {
                    double fill = o.size < leftover ? o.size : leftover;
                    fills_out.push_back({0, o.price, fill});
                    o.size -= fill;
                }
            } else if (!is_sell && !o.is_bid && trade_price >= o.price) {
                double leftover = trade_amount - ob.queue_at(false, o.price);
                if (leftover > 0.0) {
                    double fill = o.size < leftover ? o.size : leftover;
                    fills_out.push_back({1, o.price, fill});
                    o.size -= fill;
                }
            }
        }

        // Drop fully-filled orders; partial fills keep their remainder resting.
        live.erase(
            std::remove_if(live.begin(), live.end(),
                           [](const Order& o) { return o.size <= 0.0; }),
            live.end());

        ob.apply_trade(is_sell, trade_price, trade_amount);
    }
};
