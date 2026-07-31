// Unit tests for Backtester::run — the replay loop: latency in-flight, additive
// live set, GTT reap, PnL/inventory accounting, determinism. Asserts on in-memory
// RunData (fills/pnl vectors); the final markout fill is side 2.

#include "helpers.hpp"
#include <gtest/gtest.h>
#include <cmath>
#include <stdexcept>

using namespace t;

// ── latency gating: an order becomes matchable only at T + latency_us ──
TEST(Backtester, LatencyGating) {
    Feed f;
    f.lob(0, 100.0, 10.0, 101.0, 10.0).trade(100, /*sell=*/true, 100.0, 100.0);

    {   OnceStrategy s({bid(100.0, 5.0)});
        RunData d = f.run(s, /*latency_us=*/0);
        EXPECT_EQ(n_side(d, 0), 1);                // lands at t=0 ≤ trade → fills
    }
    {   OnceStrategy s({bid(100.0, 5.0)});
        RunData d = f.run(s, /*latency_us=*/200);
        EXPECT_EQ(n_side(d, 0), 0);                // lands at t=200 > trade → no fill
    }
}

// ── latency is monotone: each +1000 µs blanks exactly one more of four trades.
//    One resting bid (queue 0 → fills any sell), quoted every tick; four sells at
//    500/1500/2500/3500 µs. Stronger than the binary LatencyGating case above:
//    fills fall 4→3→2→1 as the lead-in window [0, latency) swallows one more sell. ──
TEST(Backtester, LatencyMonotonicallyBlanksTrades) {
    Feed f;
    for (int64_t t = 0; t < 5000; t += 1000)
        f.lob(t, 100.0, 0.0, 101.0, 1.0);              // bid@100 queue 0
    for (int64_t t : {500, 1500, 2500, 3500})
        f.trade(t, /*sell=*/true, 100.0, 1.0);

    const int expected[] = {4, 3, 2, 1};
    int64_t latency = 0;
    for (int e : expected) {
        EveryTick s({bid(100.0, 1.0)});                // GTC bid, re-quoted every tick
        RunData d = f.run(s, latency);
        EXPECT_EQ(n_side(d, 0), e) << "latency_us=" << latency;
        latency += 1000;
    }
}

// ── GTT expiry: an order is reaped at expire_at (landing + ttl) ──
TEST(Backtester, GttExpiry) {
    // ttl 1000 µs, latency 0 → lands at t=0, expires at t=1000
    {   Feed f;
        f.lob(0, 100.0, 0.0, 101.0, 0.0).trade(500, true, 100.0, 100.0);
        OnceStrategy s({bid(100.0, 5.0, /*ttl_us=*/1000)});
        RunData d = f.run(s, 0);
        EXPECT_EQ(n_side(d, 0), 1);                // trade before expiry → fills
    }
    {   Feed f;
        f.lob(0, 100.0, 0.0, 101.0, 0.0).trade(2000, true, 100.0, 100.0);
        OnceStrategy s({bid(100.0, 5.0, /*ttl_us=*/1000)});
        RunData d = f.run(s, 0);
        EXPECT_EQ(n_side(d, 0), 0);                // trade after expiry → reaped, no fill
    }
}

// ── additive model: landed orders are appended, not replaced. Two ticks each
//    create a resting bid; a later sell fills BOTH (replace-all would fill one). ──
TEST(Backtester, AdditiveAppend) {
    Feed f;
    f.lob(0, 100.0, 0.0, 101.0, 0.0)
     .lob(1, 100.0, 0.0, 101.0, 0.0)
     .trade(2, true, 100.0, 100.0);
    EveryTick s({bid(100.0, 5.0)});                // GTC, quoted every tick
    RunData d = f.run(s, 0);
    EXPECT_EQ(n_side(d, 0), 2);
}

// ── latency beyond the data span: nothing ever lands → zero fills ──
TEST(Backtester, LatencyBeyondSpanStarves) {
    Feed f;
    f.lob(0, 100.0, 10.0, 101.0, 10.0).trade(100, true, 100.0, 100.0);
    OnceStrategy s({bid(100.0, 5.0)});
    RunData d = f.run(s, /*latency_us=*/1'000'000);   // ≫ span
    EXPECT_EQ(n_side(d, 0), 0);
}

// ── PnL/inventory accounting: reconstruct final PnL from fills; the final
//    markout closes inventory and the reported PnL equals cash after markout. ──
TEST(Backtester, PnlAccountingAndMarkout) {
    Feed f;
    f.lob(0, 100.0, 0.0, 101.0, 0.0)
     .trade(100, true, 100.0, 100.0)               // our bid@100 fills 5 → inv +5, cash −500
     .lob(200, 110.0, 0.0, 111.0, 0.0);            // mid moves to 110.5
    OnceStrategy s({bid(100.0, 5.0)});
    RunData d = f.run(s, 0);

    double cash = 0.0, inv = 0.0, mk_price = 0.0, mk_size = 0.0;
    for (std::size_t i = 0; i < d.fill_side.size(); ++i) {
        const int    side = d.fill_side[i];
        const double p = d.fill_price[i], sz = d.fill_size[i];
        if      (side == 0) { cash -= p * sz; inv += sz; }   // bid
        else if (side == 1) { cash += p * sz; inv -= sz; }   // ask
        else                { mk_price = p;   mk_size = sz; } // markout
    }
    EXPECT_NEAR(mk_size + inv, 0.0, 1e-9);         // markout closes net inventory
    const double recon = cash + inv * mk_price;    // = −500 + 5·110.5 = 52.5
    ASSERT_FALSE(d.pnl_v.empty());
    EXPECT_NEAR(recon, d.pnl_v.back(), 1e-9);
    EXPECT_DOUBLE_EQ(d.inv_v.back(), 0.0);
}

// ── fees: each real fill pays fee_bps of notional (markout is fee-free), and the
//    reported PnL drops by exactly the total fee versus a zero-fee run. ──
TEST(Backtester, FeeChargedPerFillReducesPnl) {
    Feed f;
    f.lob(0, 100.0, 0.0, 101.0, 0.0)
     .trade(100, true, 100.0, 100.0)               // bid@100 fills 5 → notional 500
     .lob(200, 110.0, 0.0, 111.0, 0.0);

    OnceStrategy s0({bid(100.0, 5.0)});
    RunData d0 = f.run(s0, 0, 10'000'000, 1, /*fee_bps=*/0.0);
    OnceStrategy s1({bid(100.0, 5.0)});
    RunData d1 = f.run(s1, 0, 10'000'000, 1, /*fee_bps=*/10.0);

    // fee on the real fill = 10 bps · 100 · 5 = 0.5 ; markout (side 2) pays nothing
    double fee_sum = 0.0, markout_fee = -1.0;
    for (std::size_t i = 0; i < d1.fill_side.size(); ++i) {
        if (d1.fill_side[i] == 2) markout_fee = d1.fill_fee[i];
        else                      fee_sum += d1.fill_fee[i];
    }
    EXPECT_NEAR(fee_sum, 0.5, 1e-9);
    EXPECT_DOUBLE_EQ(markout_fee, 0.0);

    for (double fee : d0.fill_fee) EXPECT_DOUBLE_EQ(fee, 0.0);   // zero-fee run → all zeros

    ASSERT_FALSE(d0.pnl_v.empty());
    ASSERT_FALSE(d1.pnl_v.empty());
    EXPECT_NEAR(d1.pnl_v.back(), d0.pnl_v.back() - 0.5, 1e-9);   // PnL drops by exactly the fee
}

// ── determinism: identical inputs → identical output ──
TEST(Backtester, Deterministic) {
    Feed f;
    f.lob(0, 100.0, 10.0, 101.0, 10.0)
     .lob(1, 100.0, 10.0, 101.0, 10.0)
     .trade(2, true, 100.0, 50.0)
     .lob(3, 100.0, 10.0, 101.0, 10.0);
    auto once = [&] { OnceStrategy s({bid(100.0, 5.0)}); return f.run(s, 1000); };
    RunData a = once(), b = once();

    ASSERT_EQ(a.fill_side.size(), b.fill_side.size());
    for (std::size_t i = 0; i < a.fill_side.size(); ++i) {
        EXPECT_EQ(a.fill_side[i], b.fill_side[i]);
        EXPECT_DOUBLE_EQ(a.fill_price[i], b.fill_price[i]);
        EXPECT_DOUBLE_EQ(a.fill_size[i], b.fill_size[i]);
    }
    ASSERT_EQ(a.pnl_v.size(), b.pnl_v.size());
    for (std::size_t i = 0; i < a.pnl_v.size(); ++i)
        EXPECT_DOUBLE_EQ(a.pnl_v[i], b.pnl_v[i]);
}

// ── a feed with no LOB snapshots fails loudly rather than running on nothing ──
TEST(Backtester, EmptyLobThrows) {
    Feed f;                                    // no .lob() → 0 snapshots
    f.trade(0, true, 100.0, 1.0);              // trades but no book
    OnceStrategy s({});
    EXPECT_THROW(f.run(s, /*latency=*/0), std::runtime_error);
}

// ── trades-first tie-break: at equal timestamps the trade is processed BEFORE the LOB
//    snapshot's quote is logged, so a fill that empties our resting bid shows up as
//    "no live bid" in that tick's quote (LOB-first would log bid=100 before the removal). ──
TEST(Backtester, TradesProcessedBeforeLobAtEqualTimestamp) {
    Feed f;
    f.lob(0, 100.0, 5.0, 101.0, 5.0)           // our bid@100 rests here
     .trade(10, /*sell=*/true, 100.0, 100.0)   // t=10: a big sell that clears the bid
     .lob(10, 100.0, 5.0, 101.0, 5.0);         // AND a LOB snapshot at the same t=10
    OnceStrategy s({bid(100.0, 5.0)});
    RunData d = f.run(s, /*latency=*/0);
    EXPECT_EQ(n_side(d, 0), 1);                 // the equal-ts trade filled the bid

    ASSERT_EQ(d.qt_t.size(), 2u);               // quotes logged at t=0 and t=10
    EXPECT_EQ(d.qt_t[1], 10);
    EXPECT_TRUE(std::isnan(d.qt_bid[1]));       // bid already removed by the trade → NaN
}

// ── quote_log_stride: only every Nth LOB snapshot is written to the quote log ──
TEST(Backtester, QuoteLogStrideSkipsSnapshots) {
    Feed f;
    for (int i = 0; i < 10; ++i) f.lob(i, 100.0, 5.0, 101.0, 5.0);
    OnceStrategy s({});                         // no orders; only the quote log matters here
    RunData d = f.run(s, /*latency=*/0, /*log_interval_us=*/10'000'000, /*quote_stride=*/3);
    EXPECT_EQ(d.qt_t.size(), 4u);               // logged at lob_counter 0,3,6,9 of 10
}

// ── pnl snapshots honor log_interval: a coarser interval writes fewer snapshots ──
TEST(Backtester, PnlSnapshotHonorsLogInterval) {
    Feed f;
    for (int i = 0; i <= 10; ++i) f.lob(i * 1'000'000, 100.0, 5.0, 101.0, 5.0);   // 0..10s, 1s apart
    OnceStrategy sf({});
    RunData fine   = f.run(sf, 0, /*log_interval_us=*/1'000'000, 1);   // snapshot ~every 1s
    OnceStrategy sc({});
    RunData coarse = f.run(sc, 0, /*log_interval_us=*/5'000'000, 1);   // snapshot ~every 5s
    EXPECT_GT(fine.pnl_t.size(), coarse.pnl_t.size());
    EXPECT_GE(fine.pnl_t.size(), 10u);
    EXPECT_LE(coarse.pnl_t.size(), 4u);
}

// ── the ASK/sell side end-to-end: an aggressive buy lifts our resting ask (side 1),
//    cash rises and inventory goes short (mirror of the bid-fill accounting). ──
TEST(Backtester, AskFillAccounting) {
    Feed f;
    f.lob(0, 100.0, 5.0, 101.0, 5.0)
     .trade(10, /*sell=*/false, 101.0, 100.0);   // aggressive BUY hits our ask@101
    OnceStrategy s({ask(101.0, 5.0)});
    RunData d = f.run(s, /*latency=*/0);
    EXPECT_EQ(n_side(d, 1), 1);                   // an ASK fill occurred (process_trade else-branch)
    ASSERT_FALSE(d.fill_inv.empty());
    EXPECT_LT(d.fill_inv[0], 0.0);               // inventory went short after selling
}

// ── quote log scans BOTH sides of the live set, with multiple orders per side ──
TEST(Backtester, QuoteLogScansBothSides) {
    Feed f;
    for (int i = 0; i < 4; ++i) f.lob(i, 100.0, 5.0, 101.0, 5.0);
    EveryTick s({bid(100.0, 5.0, /*ttl=*/0), ask(101.0, 5.0, 0)});   // GTC bid + ask every tick
    RunData d = f.run(s, /*latency=*/0);
    ASSERT_FALSE(d.qt_t.empty());
    const std::size_t last = d.qt_t.size() - 1;   // by the last tick both sides have rested
    EXPECT_DOUBLE_EQ(d.qt_bid[last], 100.0);      // best of the live bids (scan hits line 157)
    EXPECT_DOUBLE_EQ(d.qt_ask[last], 101.0);      // best of the live asks (scan hits line 158)
}

// ── defensive: quote_log_stride < 1 is clamped to 1 (logs every snapshot) ──
TEST(Backtester, StrideBelowOneClampsToOne) {
    Feed f;
    for (int i = 0; i < 5; ++i) f.lob(i, 100.0, 5.0, 101.0, 5.0);
    OnceStrategy s({});
    RunData d = f.run(s, /*latency=*/0, /*log_interval_us=*/10'000'000, /*quote_stride=*/0);
    EXPECT_EQ(d.qt_t.size(), 5u);                 // stride 0 → 1 → every snapshot logged
}

// ── defensive: log_interval <= 0 uses the fallback presize and snapshots every event ──
TEST(Backtester, ZeroLogIntervalSnapshotsEveryEvent) {
    Feed f;
    for (int i = 0; i < 5; ++i) f.lob(i, 100.0, 5.0, 101.0, 5.0);
    OnceStrategy s({});
    RunData d = f.run(s, /*latency=*/0, /*log_interval_us=*/0, /*quote_stride=*/1);
    EXPECT_GE(d.pnl_t.size(), 5u);                // ts − last_log ≥ 0 always → snapshot per event
}

// ── cancel_order: latency-delayed removal by id ──────────────────────────────
// Scripted strategy: emit `batch` on tick 0, emit `to_cancel` on tick `cancel_on`
// (0 = same tick as the create). Ticks count LOB events only.
struct CreateThenCancel : StrategyBase {
    std::vector<Order>    batch;
    std::vector<uint64_t> to_cancel;
    int cancel_on;
    int k = 0;
    CreateThenCancel(std::vector<Order> b, std::vector<uint64_t> c, int cancel_on_)
        : batch(std::move(b)), to_cancel(std::move(c)), cancel_on(cancel_on_) {}
    void on_lob(const OrderBook&, double, std::vector<Order>& orders,
                std::vector<uint64_t>& cancels) override {
        if (k == 0)         orders.insert(orders.end(), batch.begin(), batch.end());
        if (k == cancel_on) cancels.insert(cancels.end(), to_cancel.begin(), to_cancel.end());
        ++k;
    }
};

// A book with queue 0 at the touch (any sell fills a resting bid), snapshots every 500 µs.
static Feed cancel_feed() {
    Feed f;
    for (int64_t t = 0; t <= 3000; t += 500) f.lob(t, 100.0, 0.0, 101.0, 0.0);
    return f;
}

// In flight, trade inside the window: order lands at T_create+lat, cancel only at
// T_cancel+lat > that, so a trade in between still fills — you cannot cancel faster
// than the round trip.
TEST(Backtester, CancelInFlightStillFillsInsideTheWindow) {
    Feed f = cancel_feed();
    f.trade(1200, /*sell=*/true, 100.0, 100.0);        // between land(1000) and cancel-land(1500)
    CreateThenCancel s({bid(100.0, 5.0, 0, false, /*id=*/1)}, {1}, /*cancel_on=*/1);
    RunData d = f.run(s, /*latency=*/1000);
    EXPECT_EQ(n_side(d, 0), 1);
}

// Same setup, trade after the cancel has landed → the order is gone.
TEST(Backtester, CancelInFlightRemovesOnceItLands) {
    Feed f = cancel_feed();
    f.trade(2000, true, 100.0, 100.0);                 // after cancel-land(1500)
    CreateThenCancel s({bid(100.0, 5.0, 0, false, 1)}, {1}, 1);
    RunData d = f.run(s, 1000);
    EXPECT_EQ(n_side(d, 0), 0);
}

// Create and cancel on the same tick ride one message: landed, then removed → nothing rests.
TEST(Backtester, CreateAndCancelSameTickRestsNothing) {
    Feed f = cancel_feed();
    f.trade(2000, true, 100.0, 100.0);
    CreateThenCancel s({bid(100.0, 5.0, 0, false, 1)}, {1}, /*cancel_on=*/0);
    RunData d = f.run(s, 0);
    EXPECT_EQ(n_side(d, 0), 0);
}

// Cancelling an id that was never live matches nothing → the real order still rests.
TEST(Backtester, CancelUnknownIdIsNoOp) {
    Feed f = cancel_feed();
    f.trade(2000, true, 100.0, 100.0);
    CreateThenCancel s({bid(100.0, 5.0, 0, false, 1)}, {999}, 1);
    RunData d = f.run(s, 0);
    EXPECT_EQ(n_side(d, 0), 1);
}

// Two resting bids at the same price (ids 1, 2); a sell of 5 fills each independently.
// Cancelling id 1 removes exactly that order → only id 2 survives to fill.
TEST(Backtester, CancelRemovesOnlyTheMatchingId) {
    Feed f = cancel_feed();
    f.trade(2000, true, 100.0, 5.0);
    std::vector<Order> two = {bid(100.0, 5.0, 0, false, 1), bid(100.0, 5.0, 0, false, 2)};
    CreateThenCancel ctrl(two, {}, 1);
    EXPECT_EQ(n_side(f.run(ctrl, 0), 0), 2);           // baseline: both fill (independent matching)
    CreateThenCancel s(two, {1}, 1);
    EXPECT_EQ(n_side(f.run(s, 0), 0), 1);              // id 1 cancelled → only id 2 fills
}

// The same id in the cancel list twice: removed once, the second is a no-op, no crash.
TEST(Backtester, DoubleCancelSameIdIsHarmless) {
    Feed f = cancel_feed();
    f.trade(2000, true, 100.0, 5.0);
    CreateThenCancel s({bid(100.0, 5.0, 0, false, 1), bid(100.0, 5.0, 0, false, 2)}, {1, 1}, 1);
    RunData d = f.run(s, 0);
    EXPECT_EQ(n_side(d, 0), 1);                        // only id 2 remains
}

// Cancelling an order that already expired (GTT reaped) matches nothing — no-op, no crash.
TEST(Backtester, CancelExpiredOrderIsNoOp) {
    Feed f = cancel_feed();
    f.trade(3000, true, 100.0, 100.0);
    // ttl 500 µs, latency 0 → order expires ~500; cancel emitted much later (tick 4, t=2000)
    CreateThenCancel s({bid(100.0, 5.0, /*ttl_us=*/500, false, 1)}, {1}, /*cancel_on=*/4);
    RunData d = f.run(s, 0);
    EXPECT_EQ(n_side(d, 0), 0);                        // expired before the trade; cancel is inert
}

// Cancelling an order that already filled fully (a size-0 husk still in live_) removes
// the husk harmlessly — the fill already happened, so nothing changes.
TEST(Backtester, CancelAlreadyFilledOrderIsNoOp) {
    Feed f = cancel_feed();
    f.trade(1200, true, 100.0, 100.0);                 // fills the bid fully at 1200
    CreateThenCancel s({bid(100.0, 5.0, 0, false, 1)}, {1}, /*cancel_on=*/4);  // cancel long after
    RunData d = f.run(s, 1000);
    EXPECT_EQ(n_side(d, 0), 1);                         // the fill stands; the late cancel is inert
}

// A partially filled order keeps its remainder resting under the same id; cancelling it
// removes the remainder, so a later sell that would have taken it finds nothing.
TEST(Backtester, CancelRemovesThePartiallyFilledRemainder) {
    Feed f;
    for (int64_t t = 0; t <= 3000; t += 500) f.lob(t, 100.0, 0.0, 101.0, 0.0);
    f.trade(700,  true, 100.0, 4.0);                   // partial: fills 4 of the size-10 bid
    f.trade(2500, true, 100.0, 100.0);                 // would take the remaining 6 — if still there
    CreateThenCancel s({bid(100.0, 10.0, 0, false, 1)}, {1}, /*cancel_on=*/3);  // cancel at t=1500
    RunData d = f.run(s, 0);
    EXPECT_EQ(n_side(d, 0), 1);                         // only the partial fill; remainder cancelled
    CreateThenCancel ctrl({bid(100.0, 10.0, 0, false, 1)}, {}, 3);
    EXPECT_EQ(n_side(f.run(ctrl, 0), 0), 2);            // control: remainder fills the second sell
}

// A cancel for an id that does not exist yet lands before that id is ever created, matches
// nothing, and is inert — cancels only touch what is resting when they land.
TEST(Backtester, PrematureCancelBeforeCreateIsInert) {
    Feed f = cancel_feed();
    f.trade(2000, true, 100.0, 100.0);
    struct PreCancel : StrategyBase {                  // tick 0: cancel id 1; tick 1: create id 1
        int k = 0;
        void on_lob(const OrderBook&, double, std::vector<Order>& orders,
                    std::vector<uint64_t>& cancels) override {
            if (k == 0) cancels.push_back(1);
            if (k == 1) orders.push_back(bid(100.0, 5.0, 0, false, 1));
            ++k;
        }
    } s;
    RunData d = f.run(s, 0);
    EXPECT_EQ(n_side(d, 0), 1);                         // premature cancel missed; order 1 rests & fills
}

// ── volume quota: placements spend it (one free per 15 s), maker fills earn floor($/2) ──
struct CreateEachTick : StrategyBase {      // create one bid on the first `until` LOB events
    int k = 0, until;
    explicit CreateEachTick(int until_) : until(until_) {}
    void on_lob(const OrderBook&, double, std::vector<Order>& orders,
                std::vector<uint64_t>&) override {
        if (k < until) orders.push_back(bid(100.0, 5.0, 0, false, static_cast<uint64_t>(k + 1)));
        ++k;
    }
};

// Four placements at 0 / 5 / 10 / 16 s: the free slot (rolling ≥15 s) covers the 0 s and
// 16 s ones, so only the 5 s and 10 s placements each cost 1 → 1000 → 998.
TEST(Backtester, QuotaCreatesSpendOneWithAFreeSlotEvery15s) {
    Feed f;
    for (int64_t t : {int64_t{0}, int64_t{5'000'000}, int64_t{10'000'000}, int64_t{16'000'000}})
        f.lob(t, 100.0, 0.0, 101.0, 0.0);
    CreateEachTick s(4);
    RunData d = f.run(s, 0);
    ASSERT_FALSE(d.quota_v.empty());
    EXPECT_EQ(d.quota_v.front(), 1000);   // seed at the run start
    EXPECT_EQ(d.quota_v.back(), 998);     // two paid placements, two free
}

// A maker fill of notional $300 earns floor(300 / 2) = 150; the sole placement is free.
TEST(Backtester, QuotaFillEarnsFloorOfNotionalOverTwoDollars) {
    Feed f;
    f.lob(0, 100.0, 0.0, 101.0, 0.0)
     .trade(100, /*sell=*/true, 100.0, 3.0);          // fills our bid@100 for 3 → notional 300
    OnceStrategy s({bid(100.0, 5.0, 0, false, 1)});
    RunData d = f.run(s, 0);
    EXPECT_EQ(d.quota_v.back(), 1150);                // 1000 (free placement) + 150 (fill)
}

// on_fill reports the id of the resting order that filled (the id create_order returned).
struct FillIdRecorder : StrategyBase {
    uint64_t place_id;
    bool fired = false;
    std::vector<uint64_t> filled_ids;
    explicit FillIdRecorder(uint64_t id) : place_id(id) {}
    void on_lob(const OrderBook&, double, std::vector<Order>& orders,
                std::vector<uint64_t>&) override {
        if (!fired) { fired = true; orders.push_back(bid(100.0, 5.0, 0, false, place_id)); }
    }
    void on_fill(int64_t, const Fill& f) override { filled_ids.push_back(f.id); }
};

TEST(Backtester, OnFillCarriesTheFilledOrdersId) {
    Feed f;
    f.lob(0, 100.0, 0.0, 101.0, 0.0).trade(100, /*sell=*/true, 100.0, 100.0);
    FillIdRecorder s(/*id=*/42);
    f.run(s, 0);
    ASSERT_EQ(s.filled_ids.size(), 1u);      // only our real fill; the markout is not routed here
    EXPECT_EQ(s.filled_ids[0], 42u);
}
