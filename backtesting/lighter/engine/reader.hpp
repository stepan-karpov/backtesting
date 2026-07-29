#pragma once
#include "orderbook.hpp"
#include <cstdint>

// ─────────────────────────────────────────────────────────────────────────────
// Readers stream market data into the engine one event at a time. The data is
// parsed venue-side in Python (see feed.py) and handed over as normalised arrays,
// so these readers only walk buffers — no file or format handling here.
//
// Both expose the same small interface the Backtester duck-types against:
//   valid() · timestamp() · advance()  (+ orderbook() / event())
// ─────────────────────────────────────────────────────────────────────────────

struct TradeEvent {
    int64_t t_us;
    bool    is_sell;
    double  price;
    double  amount;
};

// ─────────────────────────────────────────────────────────────────────────────
// ArrayLobReader — walks pre-parsed LOB snapshots. Prices/sizes are row-major
// with stride = depth (row i holds level 0..depth-1); one int64 timestamp per row.
// depth is the runtime book depth the feed loaded (1..MAX_LOB_LEVELS).
//
// Ownership: the arrays are owned by the caller (Python numpy buffers) and must
// outlive the reader. Nothing is copied except the current row into _ob.
// ─────────────────────────────────────────────────────────────────────────────

class ArrayLobReader {
    const int64_t* ts_;
    const float*   bid_p_;   // float32 grids (widened to double in OrderBook::refresh)
    const float*   bid_a_;
    const float*   ask_p_;
    const float*   ask_a_;
    int64_t        n_;
    int            depth_;
    int64_t        i_ = 0;

    OrderBook ob_;
    bool      valid_ = false;

    void load(int64_t i) noexcept {
        const std::size_t off = static_cast<std::size_t>(i) * depth_;
        ob_.refresh(bid_p_ + off, bid_a_ + off,
                    ask_p_ + off, ask_a_ + off, ts_[i]);
    }

public:
    ArrayLobReader(const int64_t* ts,
                   const float* bid_p, const float* bid_a,
                   const float* ask_p, const float* ask_a,
                   int64_t n, int depth)
        : ts_(ts), bid_p_(bid_p), bid_a_(bid_a), ask_p_(ask_p), ask_a_(ask_a),
          n_(n), depth_(depth) {
        ob_.depth = depth;
        valid_ = n_ > 0;
        if (valid_) load(0);
    }

    bool             valid()     const noexcept { return valid_; }
    int64_t          timestamp() const noexcept { return ob_.timestamp_us; }
    OrderBook&       orderbook()       noexcept { return ob_; }
    const OrderBook& orderbook() const noexcept { return ob_; }
    int64_t          size()      const noexcept { return n_; }                      // total snapshots
    int64_t          span_us()   const noexcept { return n_ > 0 ? ts_[n_ - 1] - ts_[0] : 0; }

    void advance() {
        if (++i_ < n_) load(i_);
        else           valid_ = false;
    }
};

// ─────────────────────────────────────────────────────────────────────────────
// ArrayTradeReader — walks pre-parsed trades.
// is_sell marks the aggressor side (true = aggressive sell hitting bids).
// ─────────────────────────────────────────────────────────────────────────────

class ArrayTradeReader {
    const int64_t* ts_;
    const uint8_t* is_sell_;
    const double*  price_;
    const double*  size_;
    int64_t        n_;
    int64_t        i_ = 0;

    TradeEvent ev_{};
    bool       valid_ = false;

    void load(int64_t i) noexcept {
        ev_.t_us    = ts_[i];
        ev_.is_sell = is_sell_[i] != 0;
        ev_.price   = price_[i];
        ev_.amount  = size_[i];
    }

public:
    ArrayTradeReader(const int64_t* ts, const uint8_t* is_sell,
                     const double* price, const double* size, int64_t n)
        : ts_(ts), is_sell_(is_sell), price_(price), size_(size), n_(n) {
        valid_ = n_ > 0;
        if (valid_) load(0);
    }

    bool              valid()     const noexcept { return valid_; }
    int64_t           timestamp() const noexcept { return ev_.t_us; }
    const TradeEvent& event()     const noexcept { return ev_; }
    int64_t           size()      const noexcept { return n_; }                     // total trades

    void advance() {
        if (++i_ < n_) load(i_);
        else           valid_ = false;
    }
};
