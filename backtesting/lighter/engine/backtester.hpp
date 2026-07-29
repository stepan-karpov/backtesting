#pragma once
#include "execution.hpp"
#include "orderbook.hpp"
#include "reader.hpp"
#include "result.hpp"
#include "strategy.hpp"
#include <algorithm>
#include <cstdint>
#include <deque>
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
    int64_t latency_us_;
    int64_t log_interval_us_;
    int64_t quote_log_stride_;

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
        LobSource&      lob,
        TradeSource&    trades
    ) const {
        if (!lob.valid()) throw std::runtime_error("empty LOB data");

        RunData data;
        // Pre-size outputs: quotes ≈ one per stride events; pnl ≈ span / log_interval;
        // fills ≈ one per trade (a loose hint — multi-level fills may exceed it).
        {
            const int64_t n_lob  = lob.size();
            const int64_t n_quot = n_lob / quote_log_stride_ + 1;
            const int64_t n_pnl  = log_interval_us_ > 0
                                 ? lob.span_us() / log_interval_us_ + 2
                                 : n_lob / 10 + 1;
            data.reserve(static_cast<std::size_t>(n_quot),
                         static_cast<std::size_t>(n_pnl),
                         static_cast<std::size_t>(trades.size()));
        }

        double cash = 0.0, inventory = 0.0;

        std::deque<InFlight> in_flight;   // messages travelling to the exchange
        std::vector<Order>   live;        // orders currently resting on the book

        int64_t last_log_us = lob.timestamp();
        int64_t lob_counter = 0;
        int64_t t_us        = lob.timestamp();

        std::vector<Fill> trade_fills;
        trade_fills.reserve(4);

        while (lob.valid() || trades.valid()) {
            // Trades first on equal timestamps (LOB reflects post-trade state)
            const bool take_lob =
                !trades.valid() ||
                (lob.valid() && lob.timestamp() < trades.timestamp());

            t_us = take_lob ? lob.timestamp() : trades.timestamp();

            // Land every batch that has arrived by now — orders are appended
            // (additive model), then reap any whose GTT lifetime has elapsed.
            while (!in_flight.empty() && in_flight.front().active_at <= t_us) {
                for (auto& o : in_flight.front().quotes)
                    live.push_back(std::move(o));
                in_flight.pop_front();
            }
            live.erase(
                std::remove_if(live.begin(), live.end(),
                    [t_us](const Order& o) {
                        return o.expire_at != 0 && o.expire_at <= t_us;
                    }),
                live.end());

            if (take_lob) {
                // ── LOB event: strategy issues new orders; the batch goes in flight ──
                OrderBook& ob = lob.orderbook();
                std::vector<Order> batch = strategy.on_lob(ob, inventory);
                const int64_t active_at = t_us + latency_us_;
                for (auto& o : batch)   // resolve GTT lifetime relative to landing
                    o.expire_at = (o.ttl_us > 0) ? active_at + o.ttl_us : 0;
                in_flight.push_back({active_at, std::move(batch)});

                if (lob_counter % quote_log_stride_ == 0) {
                    bool   hb = false, ha = false;   // best bid / ask of the live set
                    double bp = 0.0,   ap = 0.0;
                    for (const auto& o : live) {
                        if (o.is_bid) { if (!hb || o.price > bp) { bp = o.price; hb = true; } }
                        else          { if (!ha || o.price < ap) { ap = o.price; ha = true; } }
                    }
                    data.add_quote(t_us, hb, bp, ha, ap, ob.mid());
                }
                ++lob_counter;
                lob.advance();

            } else {
                // ── Trade event: match against the live resting orders ────────
                OrderBook&        ob = lob.orderbook();
                const TradeEvent& ev = trades.event();

                trade_fills.clear();
                exec.match(live, ob, ev.is_sell, ev.price, ev.amount, inventory, trade_fills);

                for (const auto& f : trade_fills) {
                    if (f.side == 0) { cash -= f.price * f.size; inventory += f.size; }
                    else             { cash += f.price * f.size; inventory -= f.size; }
                    data.add_fill(t_us, f, inventory, ob.mid());
                    strategy.on_fill(t_us, f);
                }
                trades.advance();
            }

            if (t_us - last_log_us >= log_interval_us_) {
                data.add_pnl_snapshot(t_us,
                    cash + inventory * lob.orderbook().mid(), inventory);
                last_log_us = t_us;
            }
        }

        // Final markout — lob.orderbook() retains last valid state
        const double fin_mid = lob.orderbook().mid();
        cash += inventory * fin_mid;
        data.add_fill(t_us, Fill{2, fin_mid, -inventory}, 0.0, fin_mid);
        data.add_pnl_snapshot(t_us, cash, 0.0);

        return data;
    }
};
