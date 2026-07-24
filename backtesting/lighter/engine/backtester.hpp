#pragma once
#include "execution.hpp"
#include "orderbook.hpp"
#include "reader.hpp"
#include "result.hpp"
#include "strategy.hpp"
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
// exchange instantly: its full desired quote set is put "in flight" and becomes
// live (replace-all) only at T + latency_us — one round-trip, as a real order
// packet would. Multiple sets can be in flight at once (a FIFO queue); the live
// set keeps resting and matching in the meantime.

// One in-flight order message: the strategy's desired quotes and when they land.
struct InFlight {
    int64_t            active_at;   // exchange time the message reaches the book
    std::vector<Order> quotes;      // full replace-all set (empty = cancel all)
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

            // Land every message that has arrived by now (latest one wins).
            while (!in_flight.empty() && in_flight.front().active_at <= t_us) {
                live = std::move(in_flight.front().quotes);
                in_flight.pop_front();
            }

            if (take_lob) {
                // ── LOB event: strategy re-quotes; the new set goes in flight ──
                OrderBook& ob = lob.orderbook();
                in_flight.push_back({t_us + latency_us_, strategy.on_lob(ob, inventory)});

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
                exec.match(live, ob, ev.is_sell, ev.price, ev.amount, trade_fills);

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
