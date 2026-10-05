import collections
import errno
import heapq
import os
import time
import traceback
from selectors import EVENT_READ, EVENT_WRITE, DefaultSelector
from typing import Any


class EventLoop:
    def __init__(self) -> None:
        self._ready_queue = collections.deque()
        self._selector = DefaultSelector()
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
        return max(deadline - time.monotonic(), 0)

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

    def run_forever(self):
        if self._running:
            raise RuntimeError("Loop already running")
        self._running = True

        try:
            while (
                self._selector.get_map() or self._ready_queue or self._delayed_cb_heap
            ) and self._running:
                timeout = 0
                if self._delayed_cb_heap:
                    deadline, _, cb, args = self._delayed_cb_heap[0]
                    timeout = self._compute_timeout(deadline)
                    if timeout <= 0:
                        heapq.heappop(self._delayed_cb_heap)
                        self.call_soon(cb, *args)

                while self._ready_queue and self._running:
                    cb, args = self._ready_queue.popleft()
                    try:
                        cb(*args)
                    except Exception as e:
                        traceback.print_exception(e)

                if timeout == 0 and self._selector.get_map():
                    timeout = None

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
