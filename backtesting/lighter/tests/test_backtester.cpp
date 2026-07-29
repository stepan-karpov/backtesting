// Unit tests for Backtester::run — the replay loop: latency in-flight, additive
// live set, GTT reap, PnL/inventory accounting, determinism. Asserts on in-memory
// RunData (fills/pnl vectors); the final markout fill is side 2.

#include "helpers.hpp"
#include <gtest/gtest.h>

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
