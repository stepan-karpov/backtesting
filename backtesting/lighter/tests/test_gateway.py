from backtesting.lighter.gateway import OrderGateway


def test_create_order_buffers_signed_tuple_and_returns_id():
    g = OrderGateway()
    oid1 = g.create_order(+1.5, 100.0, ttl_s=0.3, reduce_only=True)
    oid2 = g.create_order(-2.0, 101.0)                # defaults: ttl_s=0.0, reduce_only=False
    assert (oid1, oid2) == (1, 2)                     # positive, monotonically increasing
    assert g._pending == [(1, 1.5, 100.0, 0.3, True), (2, -2.0, 101.0, 0.0, False)]


def test_zero_size_is_a_noop_and_returns_zero():
    g = OrderGateway()
    assert g.create_order(0.0, 100.0) == 0            # no id burned
    assert g.create_order(0, 100.0) == 0
    assert g._pending == []                           # the guard drops both
    assert g.create_order(1.0, 100.0) == 1            # next real order still gets id 1


def test_cancel_buffers_id_and_ignores_zero():
    g = OrderGateway()
    g.cancel_order(7)
    g.cancel_order(0)                                 # 0 = no-op id → not buffered
    g.cancel_order(3)
    assert g._cancels == [7, 3]


def test_drain_returns_orders_and_cancels_then_clears():
    g = OrderGateway()
    oid = g.create_order(1.0, 100.0)
    g.cancel_order(oid)
    assert g._drain() == ([(1, 1.0, 100.0, 0.0, False)], [1])
    assert (g._pending, g._cancels) == ([], [])       # both buffers cleared on drain
    assert g._drain() == ([], [])                     # a second drain is empty
