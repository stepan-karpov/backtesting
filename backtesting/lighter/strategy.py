from __future__ import annotations

from .gateway import OrderGateway


class Strategy:
    def __init__(self):
        self.gateway = OrderGateway()

    def on_lob(self, order_book, inventory: float) -> None:
        """Called on every LOB snapshot. Issue orders via self.gateway, e.g.
        `self.gateway.create_order(size, price, ttl_s=...)`. No return value."""
        raise NotImplementedError

    def on_fill(self, t_us: int, side: str, price: float, size: float, order_id: int) -> None:
        """Called after each of our resting orders fills. `side` is 'bid' or 'ask';
        `order_id` is the id create_order returned for that order (0 = untracked). The
        final markout close is not routed here."""
        # raise NotImplementedError

    def _lob_step(self, order_book, inventory: float) -> tuple[list[tuple], list[int]]:
        """Engine seam — one call per LOB tick (see PyStrategy in bindings.cpp): run the
        user's imperative on_lob, then drain the gateway into (orders, cancels) for the
        engine. Keeps on_lob return-free while the hot path pays a single C++↔Python hop."""
        self.on_lob(order_book, inventory)
        return self.gateway._drain()
