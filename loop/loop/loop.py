import collections
import heapq
import time
import traceback


class EventLoop:
    # TODO: include a tie-breaker for same deadline tasks
    # to decide which take prio when two tasks are ready
    #
    #
    def __init__(self) -> None:
        self._ready_queue = collections.deque()
        self._ready_heap = []
        self._running = False

    def call_soon(self, cb, *args):
        self._ready_queue.append((cb, args))

    def call_later(self, delay: float, cb, *args):
        # add cb + delay into heap as tuple
        # each tick of run_forever should peak heap and check if its time to run the cb
        heapq.heappush(self._ready_heap, (delay + time.monotonic(), cb, args))

    def run_forever(self):
        if self._running:
            raise RuntimeError("Loop already running")

        self._running = True

        try:
            while (self._ready_queue or self._ready_heap) and self._running:
                if self._ready_queue:
                    cb, args = self._ready_queue.popleft()
                    try:
                        cb(*args)
                    except Exception as e:
                        traceback.print_exception(e)

                if self._ready_heap:
                    deadline, cb, args = self._ready_heap[0]
                    if time.monotonic() >= deadline:
                        heapq.heappop(self._ready_heap)
                        try:
                            cb(*args)
                        except Exception as e:
                            traceback.print_exception(e)

        finally:
            self._running = False

    def stop(self):
        self._running = False
