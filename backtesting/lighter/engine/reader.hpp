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
    const int64_t* _ts;
    const float*   _bid_p;   // float32 grids (widened to double in OrderBook::refresh)
    const float*   _bid_a;
    const float*   _ask_p;
    const float*   _ask_a;
    int64_t        _n;
    int            _depth;
    int64_t        _i = 0;

    OrderBook _ob;
    bool      _valid = false;

    void _load(int64_t i) noexcept {
        const std::size_t off = static_cast<std::size_t>(i) * _depth;
        _ob.refresh(_bid_p + off, _bid_a + off,
                    _ask_p + off, _ask_a + off, _ts[i]);
    }

public:
    ArrayLobReader(const int64_t* ts,
                   const float* bid_p, const float* bid_a,
                   const float* ask_p, const float* ask_a,
                   int64_t n, int depth)
        : _ts(ts), _bid_p(bid_p), _bid_a(bid_a), _ask_p(ask_p), _ask_a(ask_a),
          _n(n), _depth(depth) {
        _ob.depth = depth;
        _valid = _n > 0;
        if (_valid) _load(0);
    }

    bool             valid()     const noexcept { return _valid; }
    int64_t          timestamp() const noexcept { return _ob.timestamp_us; }
    OrderBook&       orderbook()       noexcept { return _ob; }
    const OrderBook& orderbook() const noexcept { return _ob; }
    int64_t          size()      const noexcept { return _n; }                      // total snapshots
    int64_t          span_us()   const noexcept { return _n > 0 ? _ts[_n - 1] - _ts[0] : 0; }

    void advance() {
        if (++_i < _n) _load(_i);
        else           _valid = false;
    }
};

// ─────────────────────────────────────────────────────────────────────────────
// ArrayTradeReader — walks pre-parsed trades.
// is_sell marks the aggressor side (true = aggressive sell hitting bids).
// ─────────────────────────────────────────────────────────────────────────────

class ArrayTradeReader {
    const int64_t* _ts;
    const uint8_t* _is_sell;
    const double*  _price;
    const double*  _size;
    int64_t        _n;
    int64_t        _i = 0;

    TradeEvent _ev{};
    bool       _valid = false;

    void _load(int64_t i) noexcept {
        _ev.t_us    = _ts[i];
        _ev.is_sell = _is_sell[i] != 0;
        _ev.price   = _price[i];
        _ev.amount  = _size[i];
    }

public:
    ArrayTradeReader(const int64_t* ts, const uint8_t* is_sell,
                     const double* price, const double* size, int64_t n)
        : _ts(ts), _is_sell(is_sell), _price(price), _size(size), _n(n) {
        _valid = _n > 0;
        if (_valid) _load(0);
    }

    bool              valid()     const noexcept { return _valid; }
    int64_t           timestamp() const noexcept { return _ev.t_us; }
    const TradeEvent& event()     const noexcept { return _ev; }
    int64_t           size()      const noexcept { return _n; }                     // total trades

    void advance() {
        if (++_i < _n) _load(_i);
        else           _valid = false;
    }
};
