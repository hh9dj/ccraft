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

    def _compute_timeout(self, deadline: float) -> float | None:
        timeout = max(deadline - time.monotonic(), 0)
        if timeout == 0 and not self._ready_cb and self._selector.get_map():
            timeout = None
        return timeout

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
        # 1. call ready callbacks up to a limite
        ntodo = min(len(self._ready_cb), self.max_ntodo_per_iter)
        for _ in range(ntodo):
            cb, args = self._ready_cb.popleft()
            try:
                cb(*args)
            except Exception as e:
                traceback.print_exception(e)

        # 2. schedule call_later callbacks
        timeout = 0
        while self._scheduled_cb:
            deadline, _, cb, args = self._scheduled_cb[0]
            timeout = self._compute_timeout(deadline)
            # timeout > 0, break until next iteraction when a cb is ready
            if timeout:
                break
            else:
                heapq.heappop(self._scheduled_cb)
                self.call_soon(cb, *args)

        # 3. pool for IO using selectors
        io_event_list = self._selector.select(timeout=timeout)
        for e in io_event_list:
            self._handle_event(e)

        if not (self._ready_cb or self._scheduled_cb or self._selector.get_map()):
            self._running = False

    def _handle_event(self, event: tuple[SelectorKey, int]):
        key, ready_event = event
        if ready_event & EVENT_READ and key.data[EVENT_READ]:
            cb, args = key.data[EVENT_READ]
            self.call_soon(cb, *args)
        if ready_event & EVENT_WRITE and key.data[EVENT_WRITE]:
            cb, args = key.data[EVENT_WRITE]
            self.call_soon(cb, *args)

    def _run_forever(self):
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

    def run_forever(self):
        if self._running:
            raise RuntimeError("Loop already running")
        self._running = True

        try:
            while (
                self._selector.get_map() or self._ready_cb or self._scheduled_cb
            ) and self._running:
                timeout = 0
                if self._scheduled_cb:
                    deadline, _, cb, args = self._scheduled_cb[0]
                    timeout = self._compute_timeout(deadline)
                    if not timeout:
                        heapq.heappop(self._scheduled_cb)
                        self.call_soon(cb, *args)

                while self._ready_cb and self._running:
                    cb, args = self._ready_cb.popleft()
                    try:
                        cb(*args)
                    except Exception as e:
                        traceback.print_exception(e)

                # timeout=0 return immediatly when other queues are waiting and no fd are registered
                # timeout=None when the others queues are empty and fds are registered (blocks)
                # timeout>0 when the others queues are empty and fds are registered (blocks until timeout)
                for key, events in self._selector.select(timeout=timeout):
                    if events & EVENT_READ and key.data[EVENT_READ]:
                        cb, args = key.data[EVENT_READ]
                        self.call_soon(cb, *args)
                    if events & EVENT_WRITE and key.data[EVENT_WRITE]:
                        cb, args = key.data[EVENT_WRITE]
                        self.call_soon(cb, *args)
        finally:
            self._running = False

    def stop(self):
        self._running = False
