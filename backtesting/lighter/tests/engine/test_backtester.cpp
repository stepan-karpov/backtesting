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
