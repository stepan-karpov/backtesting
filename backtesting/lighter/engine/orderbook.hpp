#pragma once
#include <array>
#include <cstdint>
#include <stdexcept>
#include <string>

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
    // Prices/sizes arrive as float32 (the feed stores them so to halve RAM) and are
    // widened to double here — the book and all downstream math stay double.
    void refresh(const float* bp, const float* ba,
                 const float* ap, const float* aa, int64_t ts) noexcept {
        for (int k = 0; k < depth; ++k) {
            bids[k] = {bp[k], ba[k]};
            asks[k] = {ap[k], aa[k]};
        }
        timestamp_us = ts;
    }

    // Consume trade volume in-place across the active levels.
    // Loud escalation: throws if the trade exhausts the entire loaded book — it ran
    // through all `depth` levels (not stopped by remaining volume nor by the trade
    // price) with volume still left. That means the feed depth is too shallow to
    // represent this trade; better to fail than to silently drop the excess.
    void apply_trade(bool is_sell, double price, double amount) {
        auto& lvls = is_sell ? bids : asks;
        double rem = amount;
        int k = 0;
        for (; k < depth; ++k) {
            auto& l = lvls[k];
            if (rem <= 0.0) break;
            if ( is_sell && l.price < price) break;
            if (!is_sell && l.price > price) break;
            double c = l.amount < rem ? l.amount : rem;
            l.amount -= c;
            rem      -= c;
        }
        if (k == depth && rem > 0.0)
            throw std::runtime_error(
                "apply_trade: trade (price=" + std::to_string(price) +
                ", amount=" + std::to_string(amount) + ") punched through all " +
                std::to_string(depth) + " loaded book levels — increase LighterFeed(depth=...)");
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
