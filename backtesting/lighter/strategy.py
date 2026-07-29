from __future__ import annotations


class OrderGateway:
    """Exchange-operation vocabulary + the buffer the engine drains.

    The *verbs* (create_order, later cancel_order / modify_order) are the stable
    contract. The *policy* — when and how much to quote, order tracking,
    throttling — belongs in the strategy notebook: subclass this and build on top
    of the verbs. This base only records each verb as a compact tuple and holds it
    until the engine collects (drains) it after on_lob.
    """

    def __init__(self):
        self._pending: list[tuple] = []

    def create_order(self, size, price, ttl_s=0.0, reduce_only=False) -> None:
        """Post one order. Buffered as a bare tuple (no per-order object) that the
        engine reads by index on the same tick:

            (size, price, ttl_s, reduce_only)

        `size` is signed — its sign is the side (> 0 bid / buy, < 0 ask / sell) and
        its magnitude the quantity; a zero size is a no-op. `ttl_s` is the GTT
        lifetime in seconds and must be a number: <= 0 means GTC (rest until filled).
        The abs / side / seconds→µs coercions happen C++-side (see bindings.cpp).
        """
        if size:
            self._pending.append((size, price, ttl_s, reduce_only))

    # cancel_order(order_id) / modify_order(order_id, ...) — next step. They need
    # order ids (and thus create_order returning one), so they wait until there is
    # something to reference. Not part of the create-only MVP.

    def _drain(self) -> list[tuple]:
        """Hand the buffered order tuples to the engine and clear the buffer."""
        out, self._pending = self._pending, []
        return out


class Strategy:
    """Base strategy. Holds an OrderGateway; on_lob issues orders through it.

    The engine calls on_lob (imperative — it returns nothing), then _collect() to
    pick up whatever orders were issued during that call. Subclasses that want a
    richer order manager reassign self.gateway to their own OrderGateway subclass.
    """

    def __init__(self):
        self.gateway = OrderGateway()

    def on_lob(self, order_book, inventory: float) -> None:
        """Called on every LOB snapshot. Issue orders via self.gateway, e.g.
        `self.gateway.create_order(size, price, ttl_s=...)`. No return value."""
        raise NotImplementedError

    def on_fill(self, t_us: int, side: str, price: float, size: float) -> None:
        """Called after each fill. side is 'bid', 'ask', or 'markout'."""

    def _collect(self) -> list[tuple]:
        """Engine seam: drain the orders issued during the last on_lob."""
        return self.gateway._drain()
