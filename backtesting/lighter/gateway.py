from __future__ import annotations


class OrderGateway:
    """Exchange-operation vocabulary + the buffer the engine drains.

    The *verbs* (create_order, cancel_order; modify_order later) are the stable
    contract. The *policy* — when and how much to quote, order tracking,
    throttling — belongs in the strategy notebook: subclass this and build on top
    of the verbs. This base only records each verb (orders as compact tuples, cancels
    as ids) and holds them until the engine collects (drains) them after on_lob.
    """

    def __init__(self):
        self._pending: list[tuple] = []
        self._cancels: list[int] = []
        self._next_oid = 1              # 0 is reserved for "no order" (zero-size no-op)

    def create_order(self, size, price, ttl_s=0.0, reduce_only=False) -> int:
        """Post one order; return its id (a positive int) for later cancel_order.

        Buffered as a bare tuple (no per-order object) that the engine reads by index
        on the same tick:

            (oid, size, price, ttl_s, reduce_only)

        `size` is signed — its sign is the side (> 0 bid / buy, < 0 ask / sell) and
        its magnitude the quantity; a zero size is a no-op and returns 0. `ttl_s` is
        the GTT lifetime in seconds and must be a number: <= 0 means GTC (rest until
        filled). The abs / side / seconds→µs coercions happen C++-side (see bindings.cpp).
        """
        if not size:
            return 0
        oid = self._next_oid
        self._next_oid += 1
        self._pending.append((oid, size, price, ttl_s, reduce_only))
        return oid

    def cancel_order(self, oid) -> None:
        """Cancel a resting order by the id create_order returned. Latency-delayed like
        any message: it removes the order when it lands, and is a harmless no-op if the
        order has already filled or expired (or the id was never live). Cancelling 0 —
        the id of a zero-size no-op — does nothing."""
        if oid:
            self._cancels.append(oid)

    def _drain(self) -> tuple[list[tuple], list[int]]:
        """Hand the buffered (orders, cancels) to the engine and clear both buffers."""
        orders, cancels = self._pending, self._cancels
        self._pending, self._cancels = [], []
        return orders, cancels
