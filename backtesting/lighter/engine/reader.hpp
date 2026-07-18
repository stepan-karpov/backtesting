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
// with stride = LOB_LEVELS (row i holds level 0..LOB_LEVELS-1); one int64
// timestamp per row.
//
// Ownership: the arrays are owned by the caller (Python numpy buffers) and must
// outlive the reader. Nothing is copied except the current row into _ob.
// ─────────────────────────────────────────────────────────────────────────────

class ArrayLobReader {
    const int64_t* _ts;
    const double*  _bid_p;
    const double*  _bid_a;
    const double*  _ask_p;
    const double*  _ask_a;
    int64_t        _n;
    int64_t        _i = 0;

    OrderBook _ob;
    bool      _valid = false;

    void _load(int64_t i) noexcept {
        const std::size_t off = static_cast<std::size_t>(i) * LOB_LEVELS;
        _ob.refresh(_bid_p + off, _bid_a + off,
                    _ask_p + off, _ask_a + off, _ts[i]);
    }

public:
    ArrayLobReader(const int64_t* ts,
                   const double* bid_p, const double* bid_a,
                   const double* ask_p, const double* ask_a,
                   int64_t n)
        : _ts(ts), _bid_p(bid_p), _bid_a(bid_a), _ask_p(ask_p), _ask_a(ask_a), _n(n) {
        _valid = _n > 0;
        if (_valid) _load(0);
    }

    bool             valid()     const noexcept { return _valid; }
    int64_t          timestamp() const noexcept { return _ob.timestamp_us; }
    OrderBook&       orderbook()       noexcept { return _ob; }
    const OrderBook& orderbook() const noexcept { return _ob; }

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

    void advance() {
        if (++_i < _n) _load(_i);
        else           _valid = false;
    }
};
