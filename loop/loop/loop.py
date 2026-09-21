import collections
import heapq
import time
import traceback


class EventLoop:
    def __init__(self) -> None:
        self._ready_queue = collections.deque()
        self._delayed_cb_heap = []
        self._running = False
        self._sequence_order = 0

    def call_soon(self, cb, *args):
        self._ready_queue.append((cb, args))

    def call_later(self, delay: float, cb, *args):
        if delay <= 0:
            self.call_soon(cb, *args)
        else:
            heapq.heappush(
                self._delayed_cb_heap,
                (delay + time.monotonic(), self._sequence_order, cb, args),
            )
            self._sequence_order += 1

    @staticmethod
    def _compute_timeout(deadline: float):
        return deadline - time.monotonic()

    def run_forever(self):
        if self._running:
            raise RuntimeError("Loop already running")

        self._running = True

        try:
            while (self._ready_queue or self._delayed_cb_heap) and self._running:
                timeout = 0
                if self._delayed_cb_heap:
                    deadline, _, cb, args = self._delayed_cb_heap[0]
                    timeout = self._compute_timeout(deadline)
                    if timeout <= 0:
                        heapq.heappop(self._delayed_cb_heap)
                        self.call_soon(cb, *args)

                if self._ready_queue:
                    cb, args = self._ready_queue.popleft()
                    try:
                        cb(*args)
                    except Exception as e:
                        traceback.print_exception(e)
                else:
                    time.sleep(timeout)
        finally:
            self._running = False

    def stop(self):
        self._running = False
