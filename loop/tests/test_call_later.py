from loop.loop import EventLoop


def test_later_than_soon(event_loop: EventLoop):
    result = []
    event_loop.call_soon(lambda x: result.append(x), 0)
    event_loop.call_later(0.1, lambda x: result.append(x), 1)
    event_loop.call_later(0.3, lambda x: result.append(x), 3)
    event_loop.call_later(0.2, lambda x: result.append(x), 2)

    event_loop.run_forever()
    assert result == [0, 1, 2, 3]
