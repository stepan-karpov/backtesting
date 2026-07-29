from __future__ import annotations

from .gateway import OrderGateway


class Strategy:
    def __init__(self):
        self.gateway = OrderGateway()

    def on_lob(self, order_book, inventory: float) -> None:
        """Called on every LOB snapshot. Issue orders via self.gateway, e.g.
        `self.gateway.create_order(size, price, ttl_s=...)`. No return value."""
        raise NotImplementedError

    def on_fill(self, t_us: int, side: str, price: float, size: float) -> None:
        """Called after each fill. side is 'bid', 'ask', or 'markout'."""
        # raise NotImplementedError

    def _lob_step(self, order_book, inventory: float) -> list[tuple]:
        """Engine seam — one call per LOB tick (see PyStrategy in bindings.cpp):
        run the user's imperative on_lob, then drain the gateway's queued orders.
        Keeps on_lob return-free while the hot path pays a single C++↔Python hop."""
        self.on_lob(order_book, inventory)
        return self.gateway._drain()
