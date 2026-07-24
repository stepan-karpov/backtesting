#pragma once
#include <array>
#include <cstdint>

// Compile-time cap on book depth (Lighter data has at most 30 levels).
// The active number of levels is a runtime value (OrderBook::depth), set from
// the feed's array width — see reader.hpp / bindings.cpp.
static constexpr int MAX_LOB_LEVELS = 30;

struct Level { double price, amount; };

struct OrderBook {
    std::array<Level, MAX_LOB_LEVELS> bids;   // descending price
    std::array<Level, MAX_LOB_LEVELS> asks;   // ascending price
    int     depth        = MAX_LOB_LEVELS;    // active levels (1..MAX_LOB_LEVELS)
    int64_t timestamp_us = 0;

    // ── properties (level 0 always present: depth >= 1) ────────────────────────
    double best_bid() const noexcept { return bids[0].price; }
    double best_ask() const noexcept { return asks[0].price; }
    double mid()      const noexcept { return 0.5 * (bids[0].price + asks[0].price); }
    double spread()   const noexcept { return asks[0].price - bids[0].price; }

    // ── write API ────────────────────────────────────────────────────────────

    // Refresh from pre-extracted row slices (row-major arrays, stride = depth).
    void refresh(const double* bp, const double* ba,
                 const double* ap, const double* aa, int64_t ts) noexcept {
        for (int k = 0; k < depth; ++k) {
            bids[k] = {bp[k], ba[k]};
            asks[k] = {ap[k], aa[k]};
        }
        timestamp_us = ts;
    }

    // Consume trade volume in-place across the active levels.
    void apply_trade(bool is_sell, double price, double amount) noexcept {
        auto& lvls = is_sell ? bids : asks;
        double rem = amount;
        for (int k = 0; k < depth; ++k) {
            auto& l = lvls[k];
            if (rem <= 0.0) break;
            if ( is_sell && l.price < price) break;
            if (!is_sell && l.price > price) break;
            double c = l.amount < rem ? l.amount : rem;
            l.amount -= c;
            rem      -= c;
        }
    }

    // Volume queued at a specific price level (0 if not present within depth).
    double queue_at(bool is_bid, double price) const noexcept {
        const auto& lvls = is_bid ? bids : asks;
        for (int k = 0; k < depth; ++k) {
            const auto& l = lvls[k];
            if (l.price == price) return l.amount;
            if ( is_bid && l.price < price) break;
            if (!is_bid && l.price > price) break;
        }
        return 0.0;
    }
};
