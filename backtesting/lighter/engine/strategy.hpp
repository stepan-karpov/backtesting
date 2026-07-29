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

    // Called on every LOB snapshot. Returns the orders to CREATE on this event
    // (appended to the live set — additive, not replace-all). Return an empty
    // vector to create nothing.
    virtual void on_lob(const OrderBook& ob, double inventory, std::vector<Order>& orders) = 0;

    // Called after each fill. Default is no-op (most strategies ignore fills).
    virtual void on_fill(int64_t t_us, const Fill& fill) {}
};
