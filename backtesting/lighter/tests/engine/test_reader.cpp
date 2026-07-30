// Unit tests for the array readers — the in-memory feed the engine walks. Covers
// valid/advance to exhaustion, per-row load (LOB stride = depth, trade fields),
// size / span_us (including single-row and empty), and is_sell mapping.

#include "../../engine/reader.hpp"
#include <gtest/gtest.h>
#include <cstdint>
#include <vector>

// ── ArrayLobReader ──
TEST(ArrayLobReader, WalksRowsAndExhausts) {
    std::vector<int64_t> ts = {10, 20, 30};
    // depth 2, row-major [n, depth]; level-1 is a sentinel we don't read here
    std::vector<float> bp = {100, 0,  101, 0,  102, 0};
    std::vector<float> ba = {5,   0,  6,   0,  7,   0};
    std::vector<float> ap = {200, 0,  201, 0,  202, 0};
    std::vector<float> aa = {5,   0,  6,   0,  7,   0};
    ArrayLobReader r(ts.data(), bp.data(), ba.data(), ap.data(), aa.data(), 3, /*depth=*/2);

    EXPECT_TRUE(r.valid());
    EXPECT_EQ(r.timestamp(), 10);
    EXPECT_DOUBLE_EQ(r.orderbook().best_bid(), 100.0);      // row 0
    EXPECT_DOUBLE_EQ(r.orderbook().best_ask(), 200.0);

    r.advance();                                            // row 1 at offset 1*depth = 2
    EXPECT_TRUE(r.valid());
    EXPECT_EQ(r.timestamp(), 20);
    EXPECT_DOUBLE_EQ(r.orderbook().best_bid(), 101.0);      // stride is correct

    r.advance();                                            // row 2
    EXPECT_EQ(r.timestamp(), 30);
    EXPECT_DOUBLE_EQ(r.orderbook().best_bid(), 102.0);

    r.advance();                                            // past the end
    EXPECT_FALSE(r.valid());

    EXPECT_EQ(r.size(), 3);
    EXPECT_EQ(r.span_us(), 20);                             // 30 − 10
}

TEST(ArrayLobReader, SingleRowSpanIsZero) {
    std::vector<int64_t> ts = {42};
    std::vector<float> bp = {100, 0}, ba = {5, 0}, ap = {200, 0}, aa = {5, 0};
    ArrayLobReader r(ts.data(), bp.data(), ba.data(), ap.data(), aa.data(), 1, 2);
    EXPECT_TRUE(r.valid());
    EXPECT_EQ(r.size(), 1);
    EXPECT_EQ(r.span_us(), 0);                              // ts[last] − ts[0] = 0
    r.advance();
    EXPECT_FALSE(r.valid());
}

TEST(ArrayLobReader, EmptyIsInvalid) {
    std::vector<int64_t> ts = {10};                         // arrays exist but n = 0
    std::vector<float> bp = {100, 0}, ba = {5, 0}, ap = {200, 0}, aa = {5, 0};
    ArrayLobReader r(ts.data(), bp.data(), ba.data(), ap.data(), aa.data(), /*n=*/0, 2);
    EXPECT_FALSE(r.valid());                                // never loaded
    EXPECT_EQ(r.size(), 0);
    EXPECT_EQ(r.span_us(), 0);                              // n_ > 0 ? ... : 0  → the 0 branch
}

// ── ArrayTradeReader ──
TEST(ArrayTradeReader, WalksTradesAndMapsFields) {
    std::vector<int64_t> ts    = {100, 200};
    std::vector<uint8_t> sell  = {1, 0};                    // is_sell mapping: !=0
    std::vector<double>  price = {50.5, 51.0};
    std::vector<double>  size  = {3.0, 4.0};
    ArrayTradeReader r(ts.data(), sell.data(), price.data(), size.data(), 2);

    EXPECT_TRUE(r.valid());
    EXPECT_EQ(r.timestamp(), 100);
    EXPECT_TRUE(r.event().is_sell);
    EXPECT_DOUBLE_EQ(r.event().price, 50.5);
    EXPECT_DOUBLE_EQ(r.event().amount, 3.0);

    r.advance();
    EXPECT_TRUE(r.valid());
    EXPECT_EQ(r.timestamp(), 200);
    EXPECT_FALSE(r.event().is_sell);                        // 0 → false
    EXPECT_DOUBLE_EQ(r.event().price, 51.0);
    EXPECT_DOUBLE_EQ(r.event().amount, 4.0);

    r.advance();
    EXPECT_FALSE(r.valid());
    EXPECT_EQ(r.size(), 2);
}

TEST(ArrayTradeReader, EmptyIsInvalid) {
    std::vector<int64_t> ts = {100};
    std::vector<uint8_t> sell = {1};
    std::vector<double> price = {50.0}, size = {1.0};
    ArrayTradeReader r(ts.data(), sell.data(), price.data(), size.data(), /*n=*/0);
    EXPECT_FALSE(r.valid());
    EXPECT_EQ(r.size(), 0);
}
