#pragma once
#include "execution.hpp"
#include "orderbook.hpp"
#include <cstdint>
#include <vector>

// Abstract C++ strategy interface.
// Python strategies (defined in notebooks) are wrapped by PyStrategy in bindings.cpp —
// that is the only place where C++ ↔ Python interop occurs.

class StrategyBase {
public:
    virtual ~StrategyBase() = default;

    // Called on every LOB snapshot. Outputs, for this event, the orders to CREATE
    // (appended to the live set — additive, not replace-all) and the ids to CANCEL
    // (resting orders removed by id when this message lands). Leave both empty to do
    // nothing. Cancels are latency-delayed like orders and are a no-op if the target
    // has already filled or expired.
    virtual void on_lob(const OrderBook& ob, double inventory,
                        std::vector<Order>& orders, std::vector<uint64_t>& cancels) = 0;

    // Called after each fill. Default is no-op (most strategies ignore fills).
    virtual void on_fill(int64_t t_us, const Fill& fill) {}
};
