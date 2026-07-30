#pragma once
#include "execution.hpp"
#include <cstdint>
#include <limits>
#include <vector>

struct RunData {
    std::vector<int64_t> pnl_t;
    std::vector<double>  pnl_v, inv_v;

    std::vector<int64_t> qt_t;
    std::vector<double>  qt_bid, qt_ask, qt_mid;

    std::vector<int64_t> fill_t;
    std::vector<int32_t> fill_side;
    std::vector<double>  fill_price, fill_size, fill_inv, fill_mid, fill_fee;

    // Lighter volume-quota balance, sampled at every event that changes it (an order
    // placement spends it, a fill earns it — see Backtester). Integer counts. `quota_kind`
    // tags each sample so downstream can count placements / free placements / fills.
    std::vector<int64_t> quota_t, quota_v;
    std::vector<int8_t>  quota_kind;

    enum QuotaKind : int8_t {                // values stored in quota_kind
        QUOTA_SEED         = 0,              // run-boundary marker (start / final)
        QUOTA_CREATE_PAID  = 1,              // placement that spent 1
        QUOTA_CREATE_FREE  = 2,              // placement covered by the free slot (spent 0)
        QUOTA_FILL         = 3,              // maker fill that earned floor(notional/$2)
    };

    void reserve(std::size_t n_quotes, std::size_t n_pnl, std::size_t n_fills) {
        quota_t.reserve(n_fills + n_pnl);
        quota_v.reserve(n_fills + n_pnl);
        quota_kind.reserve(n_fills + n_pnl);
        qt_t.reserve(n_quotes);
        qt_bid.reserve(n_quotes);
        qt_ask.reserve(n_quotes);
        qt_mid.reserve(n_quotes);
        pnl_t.reserve(n_pnl);
        pnl_v.reserve(n_pnl);
        inv_v.reserve(n_pnl);
        fill_t.reserve(n_fills);
        fill_side.reserve(n_fills);
        fill_price.reserve(n_fills);
        fill_size.reserve(n_fills);
        fill_inv.reserve(n_fills);
        fill_mid.reserve(n_fills);
        fill_fee.reserve(n_fills);
    }

    void add_pnl_snapshot(int64_t t, double pnl, double inv) {
        pnl_t.push_back(t);
        pnl_v.push_back(pnl);
        inv_v.push_back(inv);
    }

    void add_quote(int64_t t,
                   bool has_bid, double bid_price,
                   bool has_ask, double ask_price,
                   double mid) {
        static const double kNaN = std::numeric_limits<double>::quiet_NaN();
        qt_t.push_back(t);
        qt_bid.push_back(has_bid ? bid_price : kNaN);
        qt_ask.push_back(has_ask ? ask_price : kNaN);
        qt_mid.push_back(mid);
    }

    void add_fill(int64_t t, const Fill& f, double inv_after, double mid_at_fill, double fee) {
        fill_t.push_back(t);
        fill_side.push_back(f.side);
        fill_price.push_back(f.price);
        fill_size.push_back(f.size);
        fill_inv.push_back(inv_after);
        fill_mid.push_back(mid_at_fill);
        fill_fee.push_back(fee);
    }

    void add_quota_sample(int64_t t, int64_t quota, int8_t kind) {
        quota_t.push_back(t);
        quota_v.push_back(quota);
        quota_kind.push_back(kind);
    }
};
