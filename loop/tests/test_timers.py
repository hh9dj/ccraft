import time

from loop.loop import EventLoop


def test_absorb_exceptions(event_loop: EventLoop):
    """A timer callback that raises does not stop the loop; later timers still fire."""
    result = []

    def should_not_stop_loop():
        e = Exception("test")
        raise e

    event_loop.call_later(0.1, should_not_stop_loop)
    event_loop.call_later(0.1, lambda x: result.append(x), 1)
    event_loop.call_later(0.1, should_not_stop_loop)
    event_loop.run_forever()

    assert result == [1]


def test_no_hot_spin(event_loop: EventLoop):
    """Waiting for a timer blocks (low CPU) instead of hot-spinning."""
    result = []
    start = time.monotonic()
    start_cpu = time.process_time()
    event_loop.call_later(0.1, lambda x: result.append(x), 1)
    event_loop.call_later(0.2, lambda x: result.append(x), 2)
    event_loop.call_later(0.3, lambda x: result.append(x), 3)
    event_loop.run_forever()

    elapsed = time.monotonic() - start
    elapsed_cpu = time.process_time() - start_cpu
    assert elapsed_cpu <= elapsed / 2

    assert result == [1, 2, 3]


def test_max_delay(event_loop: EventLoop):
    """Timers at 0.1/0.2/0.3 s finish in about the max delay, not the sum."""
    result = []
    start = time.monotonic()
    event_loop.call_later(0.1, lambda x: result.append(x), 1)
    event_loop.call_later(0.2, lambda x: result.append(x), 2)
    event_loop.call_later(0.3, lambda x: result.append(x), 3)
    event_loop.run_forever()

    elapsed = time.monotonic() - start
    assert elapsed <= 0.5
    assert elapsed >= 0.3

    assert result == [1, 2, 3]


def test_negative_delay(event_loop: EventLoop):
    """Negative delays are clamped and fire immediately, in scheduling order."""
    result = []
    start = time.monotonic()

    event_loop.call_later(-2, lambda x: result.append(x), 1)
    event_loop.call_later(-2, lambda x: result.append(x), 2)
    event_loop.call_later(-2, lambda x: result.append(x), 3)
    event_loop.run_forever()

    elapsed = time.monotonic() - start
    assert elapsed <= 0.2

    assert result == [1, 2, 3]


def test_tied_delays(event_loop: EventLoop):
    """Timers with equal deadlines fire in scheduling order via the sequence tiebreaker."""
    result = []
    event_loop.call_later(0.1, lambda x: result.append(x), 1)
    event_loop.call_later(0.1, lambda x: result.append(x), 2)
    event_loop.call_later(0.1, lambda x: result.append(x), 3)

    event_loop.run_forever()

    assert result == [1, 2, 3]


def test_ready_work_not_delayed(event_loop: EventLoop):
    """Ready callbacks run immediately and are not delayed behind a far timer."""
    executed_soon = []
    executed_later = []
    event_loop.call_later(0.2, lambda _: executed_later.append(time.monotonic()), None)
    event_loop.call_soon(lambda _: executed_soon.append(time.monotonic()), None)
    event_loop.call_later(0.3, lambda _: executed_later.append(time.monotonic()), None)
    event_loop.call_soon(lambda _: executed_soon.append(time.monotonic()), None)

    start = time.monotonic()
    event_loop.run_forever()

    for t in executed_soon:
        assert t <= start + 0.05

    assert len(executed_soon) == 2
    assert len(executed_later) == 2


def test_execution_order(event_loop: EventLoop):
    """Mixed call_soon and call_later callbacks run in deadline order."""
    result = []
    event_loop.call_soon(lambda x: result.append(x), 0)
    event_loop.call_later(0.1, lambda x: result.append(x), 2)
    event_loop.call_later(0.3, lambda x: result.append(x), 4)
    event_loop.call_later(0.2, lambda x: result.append(x), 3)
    event_loop.call_soon(lambda x: result.append(x), 1)

    event_loop.run_forever()
    assert result == [0, 1, 2, 3, 4]
