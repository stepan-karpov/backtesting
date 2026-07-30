// Unit tests for OrderBook — the book state the engine matches against. Covers refresh
// (float32 → double), the properties, apply_trade (partial / across levels / stop-on-price
// / zero-amount / punch-through throw, both sides), and queue_at (hit / price-break / scan).

#include "../../engine/orderbook.hpp"
#include <gtest/gtest.h>
#include <initializer_list>
#include <stdexcept>

// bids descending, asks ascending; both lists must hold `depth` levels.
static OrderBook make_book(int depth,
                           std::initializer_list<Level> bids,
                           std::initializer_list<Level> asks) {
    OrderBook ob;
    ob.depth = depth;
    int k = 0; for (const auto& l : bids) ob.bids[k++] = l;
    k = 0;     for (const auto& l : asks) ob.asks[k++] = l;
    return ob;
}

TEST(OrderBook, RefreshWidensFloat32AndProperties) {
    float bp[3] = {100.25f, 99.0f, 98.0f}, ba[3] = {5.0f, 10.0f, 20.0f};
    float ap[3] = {101.75f, 102.0f, 103.0f}, aa[3] = {5.0f, 10.0f, 20.0f};
    OrderBook ob; ob.depth = 3;
    ob.refresh(bp, ba, ap, aa, /*ts=*/1234);
    EXPECT_DOUBLE_EQ(ob.best_bid(), 100.25);          // exact float32 → double
    EXPECT_DOUBLE_EQ(ob.best_ask(), 101.75);
    EXPECT_DOUBLE_EQ(ob.mid(), 0.5 * (100.25 + 101.75));
    EXPECT_DOUBLE_EQ(ob.spread(), 101.75 - 100.25);
    EXPECT_EQ(ob.timestamp_us, 1234);
    EXPECT_DOUBLE_EQ(ob.bids[2].amount, 20.0);        // deeper level widened too
}

// ── apply_trade: aggressive SELL consumes bids from the top ──
TEST(OrderBook, ApplyTradeSellPartialTopLevel) {
    OrderBook ob = make_book(2, {{100, 5}, {99, 10}}, {{101, 5}, {102, 10}});
    ob.apply_trade(/*is_sell=*/true, /*price=*/100, /*amount=*/3);
    EXPECT_DOUBLE_EQ(ob.bids[0].amount, 2.0);         // 5 − 3
    EXPECT_DOUBLE_EQ(ob.bids[1].amount, 10.0);        // untouched
}

TEST(OrderBook, ApplyTradeSellAcrossLevelsStopsOnVolume) {
    OrderBook ob = make_book(3, {{100, 5}, {99, 10}, {98, 20}}, {{101, 5}, {102, 10}, {103, 20}});
    ob.apply_trade(true, /*price=*/98, /*amount=*/12);   // fills @100 fully, part of @99
    EXPECT_DOUBLE_EQ(ob.bids[0].amount, 0.0);         // 5 consumed  (c = l.amount branch)
    EXPECT_DOUBLE_EQ(ob.bids[1].amount, 3.0);         // 10 − 7      (c = rem branch)
    EXPECT_DOUBLE_EQ(ob.bids[2].amount, 20.0);        // rem hit 0 before here
}

TEST(OrderBook, ApplyTradeSellStopsAtPrice) {
    OrderBook ob = make_book(2, {{100, 5}, {99, 10}}, {{101, 5}, {102, 10}});
    ob.apply_trade(true, /*price=*/100, /*amount=*/8);   // only bids ≥ 100 → just @100
    EXPECT_DOUBLE_EQ(ob.bids[0].amount, 0.0);
    EXPECT_DOUBLE_EQ(ob.bids[1].amount, 10.0);        // 99 < 100 → break, leftover not a punch-through
}

TEST(OrderBook, ApplyTradeSellPunchThroughThrows) {
    OrderBook ob = make_book(2, {{100, 5}, {99, 10}}, {{101, 5}, {102, 10}});
    // sell @99 fills both bids (15 total); 100 remains and price never stops → escalate
    EXPECT_THROW(ob.apply_trade(true, /*price=*/99, /*amount=*/100), std::runtime_error);
}

// ── apply_trade: aggressive BUY consumes asks (mirror) ──
TEST(OrderBook, ApplyTradeBuyConsumesAsksStopsAtPrice) {
    OrderBook ob = make_book(2, {{100, 5}, {99, 10}}, {{101, 5}, {102, 10}});
    ob.apply_trade(/*is_sell=*/false, /*price=*/101, /*amount=*/8);   // asks ≤ 101 → just @101
    EXPECT_DOUBLE_EQ(ob.asks[0].amount, 0.0);
    EXPECT_DOUBLE_EQ(ob.asks[1].amount, 10.0);        // 102 > 101 → break
}

TEST(OrderBook, ApplyTradeBuyPunchThroughThrows) {
    OrderBook ob = make_book(2, {{100, 5}, {99, 10}}, {{101, 5}, {102, 10}});
    EXPECT_THROW(ob.apply_trade(false, /*price=*/102, /*amount=*/100), std::runtime_error);
}

TEST(OrderBook, ApplyTradeZeroAmountIsNoOp) {
    OrderBook ob = make_book(2, {{100, 5}, {99, 10}}, {{101, 5}, {102, 10}});
    EXPECT_NO_THROW(ob.apply_trade(true, 100, 0.0));  // rem ≤ 0 → break at k=0, k != depth → no throw
    EXPECT_DOUBLE_EQ(ob.bids[0].amount, 5.0);         // unchanged
}

// ── queue_at ──
TEST(OrderBook, QueueAtFoundAtLevels) {
    OrderBook ob = make_book(3, {{100, 5}, {99, 10}, {98, 20}}, {{101, 5}, {102, 10}, {103, 20}});
    EXPECT_DOUBLE_EQ(ob.queue_at(/*is_bid=*/true, 100), 5.0);   // level 0
    EXPECT_DOUBLE_EQ(ob.queue_at(true, 98), 20.0);              // deeper level
    EXPECT_DOUBLE_EQ(ob.queue_at(/*is_bid=*/false, 102), 10.0); // ask side
}

TEST(OrderBook, QueueAtMissBreaksByPrice) {
    OrderBook ob = make_book(2, {{100, 5}, {99, 10}}, {{101, 5}, {102, 10}});
    EXPECT_DOUBLE_EQ(ob.queue_at(true, 99.5), 0.0);   // between bids → bid price < 99.5 breaks
    EXPECT_DOUBLE_EQ(ob.queue_at(true, 101), 0.0);    // above best bid → breaks at level 0
    EXPECT_DOUBLE_EQ(ob.queue_at(false, 101.5), 0.0); // between asks → ask price > 101.5 breaks
}

TEST(OrderBook, QueueAtMissScansToEnd) {
    OrderBook ob = make_book(2, {{100, 5}, {99, 10}}, {{101, 5}, {102, 10}});
    EXPECT_DOUBLE_EQ(ob.queue_at(true, 50), 0.0);     // below all bids → no price break, loop ends
    EXPECT_DOUBLE_EQ(ob.queue_at(false, 200), 0.0);   // above all asks → loop ends
}
