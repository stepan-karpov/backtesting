// Unit tests for NonDestructingRingBuffer — the in-flight queue behind the latency
// model. Covers the FIFO contract, the two throw paths (overflow, non-power-of-two
// capacity), index wraparound, and the "non-destructing" reuse the engine relies on
// (a popped slot keeps its state so the next push reuses its buffer, no realloc).

#include "../../engine/ring_buffer.hpp"
#include <gtest/gtest.h>
#include <stdexcept>
#include <vector>

TEST(RingBuffer, EmptyOnConstruction) {
    NonDestructingRingBuffer<int> b(4);
    EXPECT_TRUE(b.empty());
}

TEST(RingBuffer, FifoOrder) {
    NonDestructingRingBuffer<int> b(4);
    b.push_back() = 10;
    b.push_back() = 20;
    b.push_back() = 30;
    EXPECT_FALSE(b.empty());
    EXPECT_EQ(b.front(), 10); b.pop_front();
    EXPECT_EQ(b.front(), 20); b.pop_front();
    EXPECT_EQ(b.front(), 30); b.pop_front();
    EXPECT_TRUE(b.empty());
}

// ── overflow: a push into a full ring throws rather than clobbering ──
TEST(RingBuffer, OverflowThrowsWhenFull) {
    NonDestructingRingBuffer<int> b(2);
    b.push_back() = 1;
    b.push_back() = 2;                                   // head_ - tail_ == capacity_
    EXPECT_THROW(b.push_back(), std::runtime_error);
    b.pop_front();                                       // frees one slot
    EXPECT_NO_THROW(b.push_back() = 3);
}

// ── capacity must be a power of two (the index mask assumes it) ──
TEST(RingBuffer, NonPowerOfTwoCapacityThrows) {
    EXPECT_THROW(NonDestructingRingBuffer<int>(3), std::runtime_error);
    EXPECT_THROW(NonDestructingRingBuffer<int>(6), std::runtime_error);
    EXPECT_NO_THROW(NonDestructingRingBuffer<int>(1));   // 1 is a power of two
    EXPECT_NO_THROW(NonDestructingRingBuffer<int>(8));
}

// ── head_/tail_ grow past capacity; the & (capacity-1) mask must keep FIFO correct ──
TEST(RingBuffer, WraparoundKeepsFifoWithFullRing) {
    NonDestructingRingBuffer<int> b(2);
    b.push_back() = 0;
    b.push_back() = 1;
    for (int i = 2; i < 200; ++i) {          // slide a full 2-element ring forward 198×
        EXPECT_EQ(b.front(), i - 2);
        b.pop_front();
        b.push_back() = i;
    }
    EXPECT_EQ(b.front(), 198); b.pop_front();
    EXPECT_EQ(b.front(), 199); b.pop_front();
    EXPECT_TRUE(b.empty());
}

// ── the "non-destructing" promise: pop_front does not destruct, so a wrapped push
//    returns the SAME slot with its state intact (the engine reuses the quotes buffer). ──
TEST(RingBuffer, NonDestructingReuseKeepsSlotState) {
    NonDestructingRingBuffer<std::vector<int>> b(1);     // cap 1 → always the same slot
    std::vector<int>& s1 = b.push_back();
    s1 = {1, 2, 3, 4, 5};
    b.pop_front();                                       // NOT destructed
    std::vector<int>& s2 = b.push_back();                // wraps back to slot 0
    EXPECT_EQ(&s1, &s2);                                 // same physical storage
    EXPECT_EQ(s2, (std::vector<int>{1, 2, 3, 4, 5}));    // state survived the pop
}

// ── pop_back undoes the last push (rewinds head_) ──
TEST(RingBuffer, PopBackUndoesLastPush) {
    NonDestructingRingBuffer<int> b(4);
    b.push_back() = 10;
    b.push_back() = 20;
    b.pop_back();                            // drop the 20
    EXPECT_FALSE(b.empty());
    EXPECT_EQ(b.front(), 10);
    b.pop_back();                            // drop the 10
    EXPECT_TRUE(b.empty());
}
