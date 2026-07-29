// Unit tests for PessimisticExecution::match — the fill model.
// We are last in queue at our price: an order fills only when the trade volume
// exceeds the book volume displayed at that price (fill = min(order, trade − queue)).

#include "helpers.hpp"
#include <gtest/gtest.h>

using namespace t;

static std::vector<Fill> match_once(std::vector<Order>& live, OrderBook& ob,
                                    bool is_sell, double px, double amt, double inv) {
    PessimisticExecution exec;
    std::vector<Fill> fills;
    exec.match(live, ob, is_sell, px, amt, inv, fills);
    return fills;
}

// ── basic fill: trade beyond the queue fills, min(order, trade − queue) ──
TEST(Execution, BidFillsOnSell) {
    OrderBook ob = make_book({{100.0, 10.0}}, {{101.0, 10.0}});
    std::vector<Order> live{bid(100.0, 5.0)};
    auto f = match_once(live, ob, /*sell=*/true, 100.0, 100.0, 0.0);
    ASSERT_EQ(f.size(), 1u);
    EXPECT_EQ(f[0].side, 0);                       // bid
    EXPECT_DOUBLE_EQ(f[0].price, 100.0);
    EXPECT_DOUBLE_EQ(f[0].size, 5.0);              // min(5, 100 − queue 10)
    EXPECT_TRUE(live.empty());                     // fully filled → removed
}

// ── no fill while the trade is inside the queue ahead ──
TEST(Execution, NoFillWhenTradeBelowQueue) {
    OrderBook ob = make_book({{100.0, 10.0}}, {{101.0, 10.0}});
    std::vector<Order> live{bid(100.0, 5.0)};
    auto f = match_once(live, ob, true, 100.0, 8.0, 0.0);   // 8 ≤ queue 10
    EXPECT_TRUE(f.empty());
    ASSERT_EQ(live.size(), 1u);
    EXPECT_DOUBLE_EQ(live[0].size, 5.0);           // untouched
}

// ── partial fill: only (trade − queue) fills, the remainder keeps resting ──
TEST(Execution, PartialFillLeavesRemainder) {
    OrderBook ob = make_book({{100.0, 5.0}}, {{101.0, 5.0}});
    std::vector<Order> live{bid(100.0, 10.0)};
    auto f = match_once(live, ob, true, 100.0, 7.0, 0.0);   // leftover 7 − 5 = 2
    ASSERT_EQ(f.size(), 1u);
    EXPECT_DOUBLE_EQ(f[0].size, 2.0);
    ASSERT_EQ(live.size(), 1u);
    EXPECT_DOUBLE_EQ(live[0].size, 8.0);           // 10 − 2 rests
}

// ── price gating: a sell above our bid price does not reach it ──
TEST(Execution, PriceGatingSellAboveOrder) {
    OrderBook ob = make_book({{100.0, 0.0}}, {{101.0, 0.0}});
    std::vector<Order> live{bid(100.0, 5.0)};
    auto f = match_once(live, ob, true, 101.0, 100.0, 0.0);  // sell @101 > order @100
    EXPECT_TRUE(f.empty());
}

// ── mirror side: an ask fills against a buy ──
TEST(Execution, AskFillsOnBuy) {
    OrderBook ob = make_book({{99.0, 10.0}}, {{100.0, 10.0}});
    std::vector<Order> live{ask(100.0, 5.0)};
    auto f = match_once(live, ob, /*sell=*/false, 100.0, 100.0, 0.0);
    ASSERT_EQ(f.size(), 1u);
    EXPECT_EQ(f[0].side, 1);                        // ask
    EXPECT_DOUBLE_EQ(f[0].size, 5.0);
}

// ── independent matching can overfill: each level is tested against the FULL
//    trade, so a small trade can fill several levels beyond its own size ──
TEST(Execution, IndependentMultiLevelCanOverfill) {
    OrderBook ob = make_book({{100.0, 0.0}, {99.0, 0.0}}, {{101.0, 0.0}});
    std::vector<Order> live{bid(100.0, 5.0), bid(99.0, 5.0)};
    auto f = match_once(live, ob, true, 99.0, 6.0, 0.0);   // trade 6, queue 0 at both
    ASSERT_EQ(f.size(), 2u);                                // 5 + 5 = 10 filled > trade 6
    EXPECT_DOUBLE_EQ(f[0].size, 5.0);
    EXPECT_DOUBLE_EQ(f[1].size, 5.0);
    EXPECT_TRUE(live.empty());
}

// ── reduce-only bid does not fill when flat or long (nothing to reduce) ──
TEST(Execution, ReduceOnlyBidSkippedWhenNotShort) {
    OrderBook ob = make_book({{100.0, 0.0}}, {{101.0, 0.0}});
    std::vector<Order> flat{bid(100.0, 5.0, 0, /*ro=*/true)};
    EXPECT_TRUE(match_once(flat, ob, true, 100.0, 100.0, /*inv=*/0.0).empty());

    OrderBook ob2 = make_book({{100.0, 0.0}}, {{101.0, 0.0}});
    std::vector<Order> lng{bid(100.0, 5.0, 0, true)};
    EXPECT_TRUE(match_once(lng, ob2, true, 100.0, 100.0, /*inv=*/+3.0).empty());
}

// ── reduce-only bid fills only up to the short it can cover (cap = −inventory) ──
TEST(Execution, ReduceOnlyBidFillsCappedWhenShort) {
    OrderBook ob = make_book({{100.0, 0.0}}, {{101.0, 0.0}});
    std::vector<Order> live{bid(100.0, 5.0, 0, true)};
    auto f = match_once(live, ob, true, 100.0, 100.0, /*inv=*/-2.0);   // cap = 2
    ASSERT_EQ(f.size(), 1u);
    EXPECT_DOUBLE_EQ(f[0].size, 2.0);              // min(5, 100) then capped to 2
    ASSERT_EQ(live.size(), 1u);
    EXPECT_DOUBLE_EQ(live[0].size, 3.0);           // 5 − 2 rests
}

// ── reduce-only ask mirror: caps at the long it can cover (cap = inventory) ──
TEST(Execution, ReduceOnlyAskFillsCappedWhenLong) {
    OrderBook ob = make_book({{99.0, 0.0}}, {{100.0, 0.0}});
    std::vector<Order> live{ask(100.0, 5.0, 0, true)};
    auto f = match_once(live, ob, false, 100.0, 100.0, /*inv=*/+2.0);  // cap = 2
    ASSERT_EQ(f.size(), 1u);
    EXPECT_EQ(f[0].side, 1);
    EXPECT_DOUBLE_EQ(f[0].size, 2.0);
}
