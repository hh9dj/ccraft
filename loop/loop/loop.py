import collections
import heapq
import time
import traceback
from selectors import EVENT_READ, EVENT_WRITE, DefaultSelector, SelectorKey
from typing import Any

MAX_NTODO_PER_ITER = 8


class EventLoop:
    def __init__(self, n: int = MAX_NTODO_PER_ITER) -> None:
        self._ready_cb = collections.deque()
        self._selector = DefaultSelector()
        self._scheduled_cb = []
        self._running = False
        self._sequence_order = 0
        self.max_ntodo_per_iter = n

    def call_soon(self, cb, *args):
        self._ready_cb.append((cb, args))

    def call_later(self, delay: float, cb, *args):
        heapq.heappush(
            self._scheduled_cb,
            (delay + time.monotonic(), self._sequence_order, cb, args),
        )
        self._sequence_order += 1

    def _compute_timeout(self) -> float | None:
        if self._ready_cb:
            return 0
        if self._scheduled_cb:
            next_scheduled_at = self._scheduled_cb[0][0]
            return max(next_scheduled_at - time.monotonic(), 0)
        if self._selector.get_map():
            return None
        return 0

    def add_reader(self, file_descriptor: int, cb, *args):
        self._add_event(file_descriptor, EVENT_READ, cb, args)

    def add_writer(self, file_descriptor: int, cb, *args):
        self._add_event(file_descriptor, EVENT_WRITE, cb, args)

    def _add_event(self, file_descriptor: int, event, cb, args):
        try:
            key = self._selector.get_key(fileobj=file_descriptor)
        except KeyError:
            data: dict[int, Any] = {EVENT_READ: None, EVENT_WRITE: None}
            data[event] = (cb, args)
            self._selector.register(fileobj=file_descriptor, events=event, data=data)
        else:
            data = key.data
            if data[event] is not None:
                raise KeyError(f"fd {file_descriptor} already registered for {event}")
            data[event] = (cb, args)
            self._selector.modify(
                fileobj=file_descriptor, events=key.events | event, data=data
            )

    def remove_reader(self, file_descriptor: int):
        self._remove_event(file_descriptor, EVENT_READ)

    def remove_writer(self, file_descriptor: int):
        self._remove_event(file_descriptor, EVENT_WRITE)

    def _remove_event(self, file_descriptor: int, event):
        key = self._selector.get_key(fileobj=file_descriptor)
        data = key.data
        if data[event] is None:
            raise KeyError(f"fd {file_descriptor} not registered for {event}")
        data[event] = None
        remaining = key.events & ~event
        if remaining:
            self._selector.modify(fileobj=file_descriptor, events=remaining, data=data)
        else:
            self._selector.unregister(fileobj=file_descriptor)

    def _run_once(self):
        # 1. exit guard: nothing to loop for
        if not (self._ready_cb or self._scheduled_cb or self._selector.get_map()):
            self._running = False
            return

        # 2. compute the block timeout:
        timeout = self._compute_timeout()

        # 3. wait for I/O readiness; a signal aborts the tick, the next one recomputes
        try:
            io_event_list = self._selector.select(timeout=timeout)
        except InterruptedError:
            # when the process is waken up by a signal we end the tick
            return

        # 4. promote ready fds into the ready queue
        for e in io_event_list:
            self._handle_event(e)

        # 5. promote timers that expired, now recomputed after the wait
        now = time.monotonic()
        while self._scheduled_cb:
            next_scheduled_at = self._scheduled_cb[0][0]
            if next_scheduled_at <= now:
                _, _, cb, args = heapq.heappop(self._scheduled_cb)
                self.call_soon(cb, *args)
            else:
                break

        # 6. run ready callbacks up to a per-tick limit
        ntodo = min(len(self._ready_cb), self.max_ntodo_per_iter)
        for _ in range(ntodo):
            if not self._running:
                return
            cb, args = self._ready_cb.popleft()
            try:
                cb(*args)
            except Exception as e:
                traceback.print_exception(e)

    def _handle_event(self, event: tuple[SelectorKey, int]):
        key, ready_event = event
        if ready_event & EVENT_READ and key.data[EVENT_READ]:
            cb, args = key.data[EVENT_READ]
            self.call_soon(cb, *args)
        if ready_event & EVENT_WRITE and key.data[EVENT_WRITE]:
            cb, args = key.data[EVENT_WRITE]
            self.call_soon(cb, *args)

    def run_forever(self):
        if self._running:
            raise RuntimeError("Loop already running")
        self._running = True

        try:
            while True:
                self._run_once()
                if not self._running:
                    break
        finally:
            self._running = False

    def stop(self):
        self._running = False
