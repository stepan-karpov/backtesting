#include <stdexcept>

template <typename T>
class NonDestructingRingBuffer {
 private:
  T* buffer_ = nullptr;
  const size_t capacity_;
  size_t tail_ = 0;
  size_t head_ = 0;
 public:
  NonDestructingRingBuffer(const size_t capacity = 32)
   : buffer_(::new T[capacity])
     , capacity_(capacity)
  {
    if (!((capacity & (capacity - 1)) == 0)) {
      ::delete[](buffer_);
      throw std::runtime_error("capacity should be power of two");
    }
  }

  NonDestructingRingBuffer(const NonDestructingRingBuffer&) = delete;
  NonDestructingRingBuffer& operator=(const NonDestructingRingBuffer&) = delete;
  NonDestructingRingBuffer(NonDestructingRingBuffer&&) = delete;
  NonDestructingRingBuffer& operator=(NonDestructingRingBuffer&&) = delete;

  T& push_back() {
    if (head_ - tail_ == capacity_) { throw std::runtime_error("increase ring buffer capacity"); }
    return buffer_[head_++ & (capacity_ - 1)];
  }
  void pop_back() { --head_; }
  T& front() { return buffer_[tail_ & (capacity_ - 1)]; }
  void pop_front() { tail_++; }

  bool empty() const { return head_ == tail_; }

  ~NonDestructingRingBuffer() {
    if (!buffer_) { return; }

    ::delete[](buffer_);
    buffer_ = nullptr;
  }
};
 