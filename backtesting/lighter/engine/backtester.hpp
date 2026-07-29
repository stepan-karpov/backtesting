#pragma once
#include "execution.hpp"
#include "orderbook.hpp"
#include "reader.hpp"
#include "result.hpp"
#include "strategy.hpp"
#include "ring_buffer.hpp"
#include <algorithm>
#include <cstdint>
#include <stdexcept>
#include <vector>

// Pure C++ replay engine. No Python types anywhere in this file.
//
// Two-pointer merge of a LOB source and a trade source. The sources are
// duck-typed (valid / timestamp / orderbook|event / advance), so the same loop
// drives the in-memory ArrayReaders — see reader.hpp.
// Trades-first tie-breaking: at equal timestamps, trades processed before LOB.
//
// Latency model. A strategy reacting to an event at time T does not affect the
// exchange instantly: the orders it creates are put "in flight" and land on the
// book only at T + latency_us — one round-trip, as a real order packet would.
// Multiple batches can be in flight at once (a FIFO queue); the live set keeps
// resting and matching in the meantime.
//
// Order lifecycle (MVP: create-only). Landed orders are APPENDED to the live set
// (additive — no replace-all). An order leaves the book only by being filled or
// by its GTT lifetime expiring (expire_at, resolved from ttl_us at landing time).

// One in-flight order message: the orders to create and when they land.
struct InFlight {
    int64_t            active_at;   // exchange time the batch reaches the book
    std::vector<Order> quotes;      // orders to append to the live set on arrival
};

class Backtester {
    // ── config (set once at construction, immutable) ──────────────────────────
    int64_t latency_us_;
    int64_t log_interval_us_;
    int64_t quote_log_stride_;

    // ── run state (per run) ───────────────────────────────────────────────────
    // Held in fields, NOT reset between run() calls. Construct a fresh Backtester
    // for each run — run_arrays already does. A second run() on the same instance
    // would carry over stale state.
    double               cash_        = 0.0;
    double               inventory_   = 0.0;
    int64_t              last_log_us_ = 0;
    int64_t              lob_counter_ = 0;
    NonDestructingRingBuffer<InFlight> in_flight_;       // messages travelling to the exchange
    std::vector<Order>   live_;                   // orders currently resting on the book

public:
    Backtester(int64_t latency_us, int64_t log_interval_us, int64_t quote_log_stride)
        : latency_us_(latency_us)
        , log_interval_us_(log_interval_us)
        , quote_log_stride_(quote_log_stride < 1 ? 1 : quote_log_stride)
    {}

    template <class LobSource, class TradeSource>
    RunData run(
        StrategyBase&   strategy,
        ExecutionModel& exec,
        LobSource&      lob_source,
        TradeSource&    trades_source
    ) {
        if (!lob_source.valid()) throw std::runtime_error("empty LOB data");

        RunData data;
        presize(data, lob_source.size(), lob_source.span_us(), trades_source.size());

        last_log_us_ = lob_source.timestamp();
        int64_t current_timestamp_us = lob_source.timestamp();
        
        std::vector<Fill> trade_fills;
        trade_fills.reserve(40);

        while (lob_source.valid() || trades_source.valid()) {
            // Trades first on equal timestamps (LOB reflects post-trade state)
            const bool take_lob =
                !trades_source.valid() ||
                (lob_source.valid() && lob_source.timestamp() < trades_source.timestamp());

            current_timestamp_us = take_lob ? lob_source.timestamp() : trades_source.timestamp();

            land_and_reap(current_timestamp_us);

            if (take_lob) [[ likely ]] {
                process_lob(strategy, lob_source.orderbook(), data, current_timestamp_us);
                lob_source.advance();
            } else {
                process_trade(strategy, exec, lob_source.orderbook(),
                              trades_source.event(), data, current_timestamp_us, trade_fills);
                trades_source.advance();
            }

            if (current_timestamp_us - last_log_us_ >= log_interval_us_) {
                data.add_pnl_snapshot(current_timestamp_us,
                    cash_ + inventory_ * lob_source.orderbook().mid(), inventory_);
                last_log_us_ = current_timestamp_us;
            }
        }

        // Final markout — lob_source.orderbook() retains last valid state
        const double fin_mid = lob_source.orderbook().mid();
        cash_ += inventory_ * fin_mid;
        data.add_fill(current_timestamp_us, Fill{2, fin_mid, -inventory_}, 0.0, fin_mid);
        data.add_pnl_snapshot(current_timestamp_us, cash_, 0.0);

        return data;
    }

private:
    // Land every in-flight batch that has arrived by current_timestamp_us (append to the
    // live set — additive model), then reap any resting order whose GTT lifetime elapsed.
    void land_and_reap(int64_t current_timestamp_us) {
        while (!in_flight_.empty() && in_flight_.front().active_at <= current_timestamp_us) {
            for (auto& order : in_flight_.front().quotes)
                live_.push_back(std::move(order));
            in_flight_.pop_front();
        }
        live_.erase(
            std::remove_if(live_.begin(), live_.end(),
                [current_timestamp_us](const Order& order) {
                    return order.expire_at != 0 && order.expire_at <= current_timestamp_us;
                }),
            live_.end());
    }

    // LOB event: the strategy issues new orders; the batch's GTT lifetimes are resolved
    // relative to when it lands (T + latency), it goes in flight, then the quote is logged.
    void process_lob(StrategyBase& strategy, const OrderBook& order_book,
                     RunData& data, int64_t current_timestamp_us) {
        const int64_t active_at = current_timestamp_us + latency_us_;
        
        InFlight& back = in_flight_.push_back();
        
        back.active_at = active_at;
        back.quotes.clear();
        back.quotes.reserve(5);

        strategy.on_lob(order_book, inventory_, back.quotes);

        
        for (auto& order : back.quotes) {
            order.expire_at = (order.ttl_us > 0) ? active_at + order.ttl_us : 0;
        }

        if (lob_counter_ % quote_log_stride_ == 0) {
            bool   hb = false, ha = false;   // best bid / ask of the live set
            double bp = 0.0,   ap = 0.0;
            for (const auto& order : live_) {
                if (order.is_bid) { if (!hb || order.price > bp) { bp = order.price; hb = true; } }
                else              { if (!ha || order.price < ap) { ap = order.price; ha = true; } }
            }
            data.add_quote(current_timestamp_us, hb, bp, ha, ap, order_book.mid());
        }
        ++lob_counter_;
    }

    // Trade event: match against the live resting orders and apply the fills to the book
    // (cash / inventory), the result log, and the strategy's on_fill callback.
    void process_trade(StrategyBase& strategy, ExecutionModel& exec, OrderBook& order_book,
                       const TradeEvent& event, RunData& data, int64_t current_timestamp_us,
                       std::vector<Fill>& trade_fills
                    ) {
        trade_fills.clear();
        exec.match(live_, order_book, event.is_sell, event.price, event.amount,
                   inventory_, trade_fills);

        for (const auto& f : trade_fills) {
            if (f.side == 0) { cash_ -= f.price * f.size; inventory_ += f.size; }
            else             { cash_ += f.price * f.size; inventory_ -= f.size; }
            data.add_fill(current_timestamp_us, f, inventory_, order_book.mid());
            strategy.on_fill(current_timestamp_us, f);
        }
    }

    void presize(RunData& data, int64_t n_lob, int64_t span_us, int64_t n_trade) const {
        const int64_t n_quot = n_lob / quote_log_stride_ + 1;
        const int64_t n_pnl  = log_interval_us_ > 0 ? span_us / log_interval_us_ + 2
                                                    : n_lob / 10 + 1;

        data.reserve(static_cast<std::size_t>(n_quot),
                     static_cast<std::size_t>(n_pnl),
                     static_cast<std::size_t>(n_trade));
    }
};
