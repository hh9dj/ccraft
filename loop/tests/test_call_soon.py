# TODO: implement tests


from loop.loop import EventLoop


def test_absorb_exceptions(event_loop: EventLoop):

    result = []

    def should_not_stop_loop():
        e = Exception("test")
        raise e

    event_loop.call_soon(should_not_stop_loop)
    event_loop.call_soon(lambda x: result.append(x), 1)
    event_loop.call_soon(should_not_stop_loop)
    event_loop.run_forever()

    assert result == [1]


def test_duplicate_running(event_loop: EventLoop):

    result = []

    def should_not_run_fully():
        result.append(1)
        try:
            event_loop.run_forever()
        except RuntimeError:
            result.append(2)
            return

        result.append(3)

    event_loop.call_soon(should_not_run_fully)
    event_loop.run_forever()

    assert result == [1, 2]


def test_immediate_return(event_loop: EventLoop):
    event_loop.run_forever()
    assert True


def test_queue_order(event_loop: EventLoop):
    result = []

    event_loop.call_soon(lambda x: result.append(x), 1)
    event_loop.call_soon(lambda x: result.append(x), 2)
    event_loop.call_soon(lambda x: result.append(x), 3)
    event_loop.run_forever()
    assert result == [1, 2, 3]


def test_resume_after_stop(event_loop: EventLoop):
    result = []

    event_loop.call_soon(lambda x: result.append(x), 1)

    event_loop.call_soon(event_loop.stop)

    event_loop.call_soon(lambda x: result.append(x), 2)
    event_loop.call_soon(lambda x: result.append(x), 3)

    event_loop.run_forever()

    assert result == [1]

    event_loop.run_forever()

    assert result == [1, 2, 3]
