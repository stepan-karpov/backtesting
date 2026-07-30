from backtesting.lighter.gateway import OrderGateway


def test_create_order_buffers_signed_tuple():
    g = OrderGateway()
    g.create_order(+1.5, 100.0, ttl_s=0.3, reduce_only=True)
    g.create_order(-2.0, 101.0)                       # defaults: ttl_s=0.0, reduce_only=False
    assert g._pending == [(1.5, 100.0, 0.3, True), (-2.0, 101.0, 0.0, False)]


def test_zero_size_is_a_noop():
    g = OrderGateway()
    g.create_order(0.0, 100.0)
    g.create_order(0, 100.0)
    assert g._pending == []                           # the `if size:` guard drops both


def test_drain_returns_and_clears():
    g = OrderGateway()
    g.create_order(1.0, 100.0)
    assert g._drain() == [(1.0, 100.0, 0.0, False)]
    assert g._pending == []                           # buffer cleared on drain
    assert g._drain() == []                           # a second drain is empty
