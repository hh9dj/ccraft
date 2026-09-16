import collections
import traceback


class EventLoop:
    def __init__(self) -> None:
        self._ready_queue = collections.deque()
        self._running = False

    def call_soon(self, cb, *args):
        self._ready_queue.append((cb, args))

    def run_forever(self):
        if self._running:
            raise RuntimeError("Loop already running")

        self._running = True

        try:
            while len(self._ready_queue) and self._running:
                cb, args = self._ready_queue.popleft()
                try:
                    cb(*args)
                except Exception as e:
                    traceback.print_exception(e)

        finally:
            self._running = False

    def stop(self):
        if self._running:
            # NOTE: stop drops work from the queue (if running)
            # maybe drain later to keep parity with
            # reference implementation of asyncio loop
            self._ready_queue.clear()
        self._running = False
