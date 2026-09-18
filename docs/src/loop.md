# Project: Event Loop / Async Runtime

Implement a single-threaded event loop, also called a reactor, that watches many I/O sources for readiness and dispatches callbacks or tasks when events occur. Optionally, build an executor on top of it to drive coroutines and futures, which demonstrates cooperative multitasking.

- **Language:** Python (3.12, managed with `uv`)
- **Focus areas:** OS I/O multiplexing (`select`/`poll`/`epoll`/`kqueue`, file descriptors), non-blocking I/O, event-driven concurrency, cooperative multitasking, and how `async`/`await` works under the hood
- **Build/test command:** `uv run pytest tests/` and `uv run main.py`, both run from the `loop/` directory

## Milestones

1. **Callback loop** (Stages 0–2). A ready queue, `call_soon`, and timers.
2. **I/O reactor** (Stages 3–4). Readiness dispatch over file descriptors using `selectors`.
3. **Cooperative multitasking** (Stages 5–7). Generators, `yield from`, Futures, and Tasks.
4. **async/await executor** (Stages 8–9). Native coroutines, `create_task`, and `gather`.
5. **Beast mode** (Stages 10–13). A TCP echo server; cancellation, exception propagation, and asyncio parity.

## Similar Projects & Libraries

Read these for inspiration; do not copy them. The listed entry points are the best places to start.

- [CPython `asyncio`](https://github.com/python/cpython/tree/main/Lib/asyncio) (Python) — the canonical reference. Study `base_events.py` (specifically `_run_once`), `selector_events.py`, `futures.py`, and `tasks.py`.
- [uvloop](https://github.com/MagicStack/uvloop) (Cython/C) — an asyncio loop built on libuv. See `uvloop/loop.pyx` for how it maps watchers and timers.
- [libuv](https://github.com/libuv/libuv) (C) — the loop behind Node.js. Read `src/unix/core.c` (`uv_run`), `src/timer.c`, and `src/unix/loop-watcher.c`.
- [Redis `ae.c`](https://github.com/redis/redis/blob/unstable/src/ae.c) (C) — a compact production loop with a ready queue, a timer heap, and `poll`.
- [Trio](https://github.com/python-trio/trio) (Python) — structured concurrency. See `_core/_run.py` and `_core/_traps.py`.
- [Curio](https://github.com/dabeaz/curio) (Python) — a minimal generator-based kernel. See `curio/kernel.py` and `curio/io.py`.
- [gevent](https://github.com/gevent/gevent) (Python) — a greenlet-based hub loop; useful as a contrast because it switches implicitly.
- [Tokio](https://github.com/tokio-rs/tokio) (Rust) — a work-stealing executor. See `runtime/scheduler/` and `io/`.
- [Boost.Asio](https://github.com/boostorg/asio) (C++) — the proactor/completion model, which differs from the readiness model used here.

## Contents

- [x] [Stage 0: Setup](#stage-0-setup)
- [x] [Stage 1: A bare loop with `call_soon`](#stage-1-a-bare-loop-with-call_soon)
- [ ] [Stage 2: Timers (`call_later`)](#stage-2-timers-call_later)
- [ ] [Stage 3: Readiness polling with `selectors`](#stage-3-readiness-polling-with-selectors)
- [ ] [Stage 4: The complete loop tick](#stage-4-the-complete-loop-tick)
- [ ] [Stage 5: Generators as coroutines](#stage-5-generators-as-coroutines)
- [ ] [Stage 6: `yield from` delegation](#stage-6-yield-from-delegation)
- [ ] [Stage 7: Futures and Tasks](#stage-7-futures-and-tasks)
- [ ] [Stage 8: Native coroutines](#stage-8-native-coroutines)
- [ ] [Stage 9: `gather`](#stage-9-gather)
- [ ] [Stage 10: Async socket I/O primitives](#stage-10-async-socket-io-primitives)
- [ ] [Stage 11: Echo server end-to-end](#stage-11-echo-server-end-to-end)
- [ ] [Stage 12: Cancellation & exception propagation](#stage-12-cancellation--exception-propagation)
- [ ] [Stage 13: Drop-in asyncio comparison](#stage-13-drop-in-asyncio-comparison)

## Stage 0: Setup

- **Goal:** A `uv`-managed Python 3.12 project with pytest, a `loop/` package skeleton, and a `main.py` entry point.
- **Test:** `uv run pytest tests/test_smoke.py`.
- **Focus:** Tooling and test-driven stage discipline.

### Prerequisites

- `uv` is installed, and both `loop/pyproject.toml` and `.python-version` (3.12) exist.
- You know the basics of pytest.

### Concepts to learn first

- Always run commands through `uv run`, so `.python-version` pins the interpreter.
- The project has zero runtime dependencies: use only the standard library (`selectors`, `heapq`, `time`, `socket`).

### Interfaces

- `loop/__init__.py` exports `EventLoop`.
- The package is split across `loop/loop.py` (Stages 1–4), `loop/futures.py` (Stage 7), and `loop/sock.py` (Stage 10), with tests under `tests/`.

### Edge cases & pitfalls

- Do not run `pip install`; doing so corrupts `uv.lock`.
- Keep tests hermetic by using `os.pipe()` or `socket.socketpair()` instead of the network.

### Hints

- Which fixture gives every test a fresh `EventLoop`?
- Confirm that `uv run main.py` works end-to-end before you start Stage 1.

### References

- [uv docs](https://docs.astral.sh/uv/) · [pytest docs](https://docs.pytest.org/en/stable/)

### Done when

- [ ] `uv run pytest` exits 0 with the smoke test.
- [ ] `uv run main.py` runs.
- [ ] The package skeleton matches the layout above.

## Stage 1: A bare loop with `call_soon`

- **Goal:** The smallest possible `EventLoop`: a ready queue of callbacks, plus `call_soon()`, `run_forever()`, and an exit-when-idle behavior.
- **Test:** `uv run pytest tests/test_call_soon.py`.
- **Focus:** Event-driven programming and the loop lifecycle.

### Prerequisites

- Stage 0 is done, and `EventLoop` can be imported.

### Concepts to learn first

- A loop is essentially a queue plus a `while` loop: pop work and run it. Later, event sources simply enqueue more work.
- Use `collections.deque` for O(1) operations at both ends, and avoid `list.pop(0)`.
- Liveness means there is nothing left to do. This definition later generalizes to include timers and file descriptors.

### Interfaces

- `EventLoop()` · `call_soon(cb, *args)` · `run_forever()` · `stop()`

### Edge cases & pitfalls

- An exception raised inside a callback must not kill the loop.
- A reentrant call to `run_forever` must be rejected; guard it with a `_running` flag.
- Decide what `stop()` means: does it drop queued callbacks or drain them? Document your choice.

### Hints

- Mirror the asyncio names now, so Stage 13 is easier.
- What exactly gets enqueued is where the real design decisions live.

### References

- [30-line asyncio loop](https://dev.to/ritesh_fcb86fb4b3890c81e4/build-a-working-asyncio-event-loop-in-30-lines-of-plain-python-5gjb) · CPython `base_events.py`

### Done when

- [ ] Callbacks run in order, the loop exits when idle, `stop()` halts it, and callback errors stay contained.
- [ ] `run_forever` returns immediately when nothing is scheduled.

## Stage 2: Timers (`call_later`)

- **Goal:** `call_later(delay, cb)` backed by a monotonic min-heap that sleeps just long enough and fires expired timers in deadline order.
- **Test:** `uv run pytest tests/test_timers.py` — check deadline order and that wall time is about the maximum delay, not the sum of delays.
- **Focus:** Timers as events, and where the loop is allowed to block.

### Prerequisites

- Stage 1 is done, and you are comfortable with `heapq`.

### Concepts to learn first

- A timer is just work whose condition is "the clock has passed the deadline"; each tick promotes expired timers to the ready queue.
- A heap gives O(log n) insertion and O(1) peek.
- `time.monotonic()` never jumps backwards, so use it for deadlines.
- The "how long may I block?" budget you compute here becomes the `select(timeout)` argument in Stage 4.

### Interfaces

- `call_later(delay, cb, *args)`, plus helpers to promote expired timers and compute the block timeout.

### Edge cases & pitfalls

- When two timers share a deadline, the heap compares the next tuple element, so include a sequence number as a tiebreaker.
- Forgetting to sleep until the deadline results in a 100% CPU spin.
- `call_later(0, ...)` should behave like `call_soon`; clamp negative delays.
- In tests, use a tolerance: assert `elapsed >= delay` with a generous upper bound.

### Hints

- What value later replaces `time.sleep()` in the `select()` call?
- How would you prove that a 50 ms timer ran between two 100 ms closures?

### References

- [Build your own Event Loop](https://techtalk.digitalpress.blog/build-your-own-event-loop-in-python/) · [PEP 418](https://peps.python.org/pep-0418/)

### Done when

- [ ] Timers fire in deadline order, wall time is about the maximum delay, and `call_later(0)` fires on the next tick.
- [ ] The loop exits when both the ready queue and the timer heap are empty.
- [ ] The loop does not hot-spin while waiting.

## Stage 3: Readiness polling with `selectors`

- **Goal:** `add_reader` and `add_writer` backed by `selectors.DefaultSelector`, so the loop wakes on file-descriptor readiness instead of polling.
- **Test:** `uv run pytest tests/test_selectors.py` — write to an `os.pipe()` and confirm the reader callback fires.
- **Focus:** I/O multiplexing, file descriptors, and non-blocking I/O.

### Prerequisites

- Stage 2 is done, and the loop can compute a block timeout.

### Concepts to learn first

- Readiness is not completion: the OS reports that a file descriptor is ready, but your callback still performs the read.
- `DefaultSelector` picks `epoll`, `kqueue`, or `select` as appropriate. Its API is `register`, `select(timeout)`, and `unregister`.
- Store the callback as the selector `data`.

### Interfaces

- `add_reader(fd, cb, *args)` / `add_writer(...)` · `remove_reader(fd)` / `remove_writer(fd)`

### Edge cases & pitfalls

- Registering the same file descriptor twice raises `KeyError`; decide whether to replace, ignore, or raise, and test that choice.
- With zero file descriptors and `timeout=None`, `select` blocks forever, so the exit condition must be checked before blocking.
- The selector is level-triggered, so drain the descriptor or you will be woken on every tick.
- Always pair `close` with `remove_*` to avoid stale descriptors after reuse.

### Hints

- Why use `os.pipe()` before moving on to sockets?
- Should dispatch happen inline or be enqueued into the ready path? Which choice makes exception handling simpler?

### References

- [selectors docs](https://docs.python.org/3/library/selectors.html) · [Demystifying AsyncIO](https://slides.com/art049/demystifying-asyncio)

### Done when

- [ ] A pipe write fires the reader callback with the correct bytes, and `remove_reader` stops it.
- [ ] With zero file descriptors, zero timers, and an empty queue, the loop exits instead of hanging.
- [ ] A reader and a writer on the same file descriptor coexist.

## Stage 4: The complete loop tick

- **Goal:** Formalize `_run_once()` so it blends ready callbacks, timer deadlines, and selector waits.
- **Test:** `uv run pytest tests/test_run_once.py` — a pipe reader and a 50 ms timer both fire, and the loop exits when drained.
- **Focus:** Timeout computation and fair scheduling order.

### Prerequisites

- Stage 3 is done.

### Concepts to learn first

- `_run_once` runs in phases: compute the timeout, select, promote I/O, promote timers, then run the ready callbacks. Learn the order from the source.
- The timeout rule: if there is ready work, use 0; otherwise use the next deadline; otherwise use `None` if file descriptors are registered; otherwise exit.
- Because everything funnels through `_ready`, no event source can starve another.

### Interfaces

- `_run_once()` · `_compute_timeout()` returning `0`, a delay, or `None`.

### Edge cases & pitfalls

- Cap how much work each tick drains (snapshot `_ntodo`) so chatty callbacks cannot starve other work.
- Catch `InterruptedError` from `select`.
- Recompute `now` after `select`, so timers that expired during the wait fire this tick.
- Never call `select(None)` when the exit condition already holds.

### Hints

- Line your phases up against asyncio's. Which orderings change timing precision?
- Where is the single choke point for exceptions?

### References

- CPython `base_events.py` (`_run_once`) · [Redis `ae.c`](https://github.com/redis/redis/blob/unstable/src/ae.c) · [libuv core.c](https://github.com/libuv/libuv/blob/v1.x/src/unix/core.c)

### Done when

- [ ] A mixed timer and I/O workload completes, and the loop exits when drained.
- [ ] `_compute_timeout` unit tests cover `0`, approximately the delay, and `None`.
- [ ] A self-rescheduling `call_soon` does not starve a 10 ms timer.

## Stage 5: Generators as coroutines

- **Goal:** Drive generators as tasks, using `next()` to reach a `yield` (suspend) or a `StopIteration` (done).
- **Test:** `uv run pytest tests/test_generators.py` — two tasks interleave and wall time is about the maximum sleep.
- **Focus:** Cooperative multitasking and the mechanics of pausing and resuming.

### Prerequisites

- Stage 4 is done, and you understand generators and `yield`/`send`.

### Concepts to learn first

- A generator is a pausable frame, and the loop is the thing that resumes it.
- Scheduling is cooperative: the task decides when to yield, so a task that never yields freezes the loop.
- `return value` raises `StopIteration(value)`, which is the result channel.

### Interfaces

- `sleep_gen(seconds)` — a generator that yields until a deadline, with a stepper that detects completion.

### Edge cases & pitfalls

- Requeueing on every yield with no wait spins at 100% CPU. That is expected at this stage; timers fix it next.
- Forgetting to handle `StopIteration` reschedules finished tasks forever.
- An uncaught task exception propagates out of `next()`; record it instead of rescheduling.

### Hints

- What is the minimal state a driven generator needs?
- Which timestamp trace would prove true interleaving?

### References

- [30-line loop](https://dev.to/ritesh_fcb86fb4b3890c81e4/build-a-working-asyncio-event-loop-in-30-lines-of-plain-python-5gjb) · [Recreating asyncio](https://jacobpadilla.com/writing/recreating-asyncio)

### Done when

- [ ] Tasks interleave in the expected order, and wall time is about the maximum sleep.
- [ ] Finished generators are never requeued.
- [ ] Composition with `yield from sleep_gen()` works.

## Stage 6: `yield from` delegation

- **Goal:** Support nested generators so sends and throws pass in both directions, and the sub-generator's return value surfaces.
- **Test:** `uv run pytest tests/test_delegation.py` — inner sleep, return value, and exception propagation.
- **Focus:** PEP 380 as the desugaring of `await`.

### Prerequisites

- Stage 5 is done.

### Concepts to learn first

- `yield from` is a transparent bidirectional channel, not a loop.
- `await x` is equivalent to `yield from x.__await__()`.
- The loop only ever sees the innermost yields.

### Edge cases & pitfalls

- Never swallow exceptions mid-chain; establish whether each layer propagates or resolves them.
- Preserve `StopIteration.value` in your stepper.
- Calling `send(x)` before the first `next()` raises `TypeError`.
- `yield sleep_gen(1)` yields the generator object itself (junk) instead of delegating; this is a classic typo.

### Hints

- How does PEP 380 explain send and throw passthrough?
- If the loop receives a raw generator, which mistake produced it?

### References

- [PEP 380](https://peps.python.org/pep-0380/) · [Custom Event Loop guide](https://www.codingpancake.com/2026/07/how-to-implement-custom-event-loop-in.html)

### Done when

- [ ] Return values propagate through one and three nesting levels, and an inner exception propagates.
- [ ] The Stage 5 stepper is unchanged, proving nesting is transparent.
- [ ] No hangs result from confusing `yield` with `yield from`.

## Stage 7: Futures and Tasks

- **Goal:** Add `Future` (a value that is not ready yet) and `Task` (a coroutine driver), so tasks can yield a Future and sleep without spinning.
- **Test:** `uv run pytest tests/test_futures.py` — a timer resolves a Future, the task resumes with the value, and `sleep()` interleaves with almost no spin.
- **Focus:** Cooperative multitasking without polling.

### Prerequisites

- Stages 5 and 6 are done.

### Concepts to learn first

- A Future holds a result, a done flag, and callbacks; `set_result` fires those callbacks.
- Suspend and resume works like this: yield a Future, register a re-wake, stop stepping, resolve the Future, and `send(value)` back in.
- `Future.__await__` is `return (yield self)`, which is the bridge to `await`.
- `loop.call_later(deadline, future.set_result, value)` provides the wake-up.

### Interfaces

```python
class Future:
    def done(self) -> bool: ...
    def result(self): ...
    def set_result(self, value) -> None: ...
    def add_done_callback(self, fn) -> None: ...
    def __await__(self): ...

class Task(Future):
    def __init__(self, coro, loop) -> None: ...

# on EventLoop:
def create_task(self, coro) -> Task: ...
def sleep(self, delay, result=None) -> Future: ...
```

### Edge cases & pitfalls

- The lost-task trap: keep strong references to tasks, and log unretrieved exceptions.
- Yielding a non-Future raises `RuntimeError`.
- Calling `set_result` twice raises.
- Calling `result()` on an unfinished Future raises; the only way to wait is via `yield` or `await`.

### Hints

- How would you prove that the loop no longer spins while a task sleeps?
- Should `Future` know about the loop? Why keep it loop-agnostic?

### References

- CPython `futures.py` and `tasks.py` · [Asyncio Demystified](https://dev.indooroutdoor.io/asyncio-demystified-rebuilding-it-from-scratch-one-yield-at-a-time)

### Done when

- [ ] Yield-Future runs through timer-resolve-resume, and exceptions are stored and re-raised.
- [ ] The `sleep()` interleaving test passes with wall time about the maximum delay and no spin.
- [ ] Yielding a non-Future and calling `set_result` twice both raise.

## Stage 8: Native coroutines

- **Goal:** Make `async def` and `await` run on your loop unchanged, using the same Task, Future, and loop tick.
- **Test:** `uv run pytest tests/test_native_coros.py` — the Stage 7 scenarios rewritten with `async def`.
- **Focus:** How `async`/`await` desugars and how `__await__` interoperates.

### Prerequisites

- Stage 7 is done.

### Concepts to learn first

- `async def` returns a coroutine, not a generator; drive it with `send(None)` and `throw`.
- `await x` is approximately `yield from x.__await__()` (see PEP 492).
- The first resume must send `None`.

### Interfaces

- `run_until_complete(awaitable)` — returns the result or raises.

### Edge cases & pitfalls

- Awaiting a bare generator raises `TypeError`, which is good type discipline.
- A `yield` inside `async def` creates an async generator, which is unsupported here; lint for it.
- A nested `run_until_complete` must raise; guard it with `_running`.

### Hints

- How small is the diff from Stage 7?
- Why keep one generator-based test after the rewrite?

### References

- [PEP 492](https://peps.python.org/pep-0492/) · [Recreating asyncio](https://jacobpadilla.com/writing/recreating-asyncio)

### Done when

- [ ] The same assertions as Stage 7 pass using `async def` syntax.
- [ ] `run_until_complete` returns the value or propagates the exception.
- [ ] The Stage 5 generator tests still pass untouched.

## Stage 9: `gather`

- **Goal:** `gather(*awaitables)` waits on many children concurrently and returns ordered results in about the maximum delay.
- **Test:** `uv run pytest tests/test_gather.py` — 50/100/150 ms sleeps finish in about 150 ms, results follow argument order, and one exception surfaces.
- **Focus:** Fan-out and fan-in, and Future composition.

### Prerequisites

- Stage 8 is done.

### Concepts to learn first

- Wrap children in Tasks, attach callbacks, count them down, and resolve one parent Future.
- Results land in argument order regardless of finish order.
- Choose failure semantics (fail-fast and cancel siblings, or await the rest) and document the choice.

### Interfaces

- `gather(*awaitables) -> Future`; an empty `gather()` resolves `[]` immediately.

### Edge cases & pitfalls

- Bind loop indices with `i=i` to avoid late-binding closure bugs.
- `add_done_callback` fires immediately for already-done Futures; test already-done children.
- After the parent resolves, later completions must be ignored.
- Nested calls such as `gather(gather(...), ...)` should work.

### Hints

- Where else does the countdown-latch pattern recur?
- Does `gather` need the loop, or only child creation?

### References

- CPython `tasks.py` (`gather`) · [Asyncio Demystified](https://dev.indooroutdoor.io/asyncio-demystified-rebuilding-it-from-scratch-one-yield-at-a-time)

### Done when

- [ ] Results are ordered, wall time is about the maximum delay, and empty and nested gather cases pass.
- [ ] Failure semantics are documented and tested.
- [ ] There is no closure index bug.

## Stage 10: Async socket I/O primitives

- **Goal:** Awaitable `sock_recv`, `sock_sendall`, and `sock_accept` implemented as Futures resolved from selector callbacks.
- **Test:** `uv run pytest tests/test_sock_io.py` — an echo over a `socketpair()`, with exact bytes on both sides.
- **Focus:** Non-blocking I/O and readiness as Future resolution.

### Prerequisites

- Stages 3, 4, and 7 are done.

### Concepts to learn first

- `setblocking(False)` makes `recv` raise `BlockingIOError`; try, then register and suspend, and retry on readiness.
- Selector registration is one-shot and is unregistered on first firing.
- Partial sends must loop until everything is sent, and a `recv` that returns `b""` means orderly shutdown.

### Interfaces

- `sock_recv(loop, sock, n) -> bytes` · `sock_sendall(loop, sock, data) -> None` · `sock_accept(loop, listener) -> (conn, addr)`

### Edge cases & pitfalls

- A blocking `recv` freezes the whole loop, so assert non-blocking mode in the primitives.
- Handle spurious wakeups by always using `try/except BlockingIOError`.
- Unregister before resolving to avoid stale descriptors after reuse.
- `sock_recv` returns up to `n` bytes, so tests must frame accordingly.

### Hints

- Why mirror asyncio's `sock_*` signatures?
- Which fits better: functions plus one-shot callbacks, or Future subclasses?

### References

- CPython `selector_events.py` · [socket docs](https://docs.python.org/3/library/socket.html)

### Done when

- [ ] socketpair and loopback TCP echo pass with exact-byte assertions.
- [ ] A concurrent timer fires on schedule during a pending `sock_recv`.
- [ ] Spurious-wakeup and partial-send paths are tested.

## Stage 11: Echo server end-to-end

- **Goal:** A concurrent TCP echo server on your loop, with one task per connection, serving N clients on a single thread.
- **Test:** `uv run pytest tests/test_echo_server.py` — N threaded clients with distinct payloads each receive their own bytes back.
- **Focus:** Concurrent servers without threads, and file-descriptor lifecycle.

### Prerequisites

- Stage 10 is done.

### Concepts to learn first

- An accept loop spawns a task per connection, and interleaving happens at `await` points.
- A slow client suspends only its own task, which is parked on the selector.

### Interfaces

- `serve_forever(loop, listener)` · `handle_client(loop, conn)`

### Edge cases & pitfalls

- Unregister and close on every exit path; a `finally` block is non-negotiable.
- When `recv` returns `b""`, break instead of re-registering.
- For the listener, set `SO_REUSEADDR`, then `bind`, `listen(>=100)`, and non-blocking mode.
- In test teardown, stop the loop, close the listener, and join the thread with a timeout.
- Catch `ConnectionResetError` from killed clients.

### Hints

- Why start with a few clients before scaling to 50 or more?
- How will you detect a file-descriptor leak?

### References

- [Single-threaded non-blocking server](https://prodsens.live/2025/05/12/building-your-own-web-server-part-4-single-threaded-non-blocking-server/) · [Asyncio Demystified](https://dev.indooroutdoor.io/asyncio-demystified-rebuilding-it-from-scratch-one-yield-at-a-time)

### Done when

- [ ] N concurrent distinct echoes pass, slow clients do not block fast ones, and the connection count returns to 0.
- [ ] File-descriptor count is stable across runs, and an RST-killed client does not wedge the server.
- [ ] Wall time demonstrates concurrency.

## Stage 12: Cancellation & exception propagation

- **Goal:** `task.cancel()` injects `CancelledError` at the suspension point, and exceptions propagate through `await` chains to `task.result()`.
- **Test:** `uv run pytest tests/test_cancellation.py` — cancel a sleeping task, and a three-deep raise surfaces exactly.
- **Focus:** Cancellation as a first-class operation and exception flow through frames.

### Prerequisites

- Stages 7 and 8 are done, and you understand `throw()` propagation from Stage 6.

### Concepts to learn first

- Cancellation means calling `coro.throw(CancelledError)` where the task is parked.
- `CancelledError` inherits from `BaseException`, so catch it distinctly from `Exception`.
- A child exception must reach the awaiter and mark the child done; never leave a parked awaiter behind.

### Interfaces

- `Task.cancel() -> bool` · `Task.cancelled() -> bool` · the state semantics of `Task.exception()` and `Task.result()`.

### Edge cases & pitfalls

- A swallowed `CancelledError` (for example, a bare `except BaseException`) turns a cancel into a hang.
- Cancelling a done task returns `False` and does nothing.
- Guard against double-resolve after cancel with `if self.done(): return`.
- Cancelling the last task must still let the loop exit.

### Hints

- Model the states pending, cancelling, and cancelled/finished.
- Which timings hit distinct branches: before a step, mid-sleep, after done, and twice?

### References

- CPython `tasks.py` · [PEP 492](https://peps.python.org/pep-0492/) · [Trio `_run.py`](https://github.com/python-trio/trio/blob/main/src/trio/_core/_run.py)

### Done when

- [ ] A mid-sleep cancel raises `CancelledError`, a three-deep raise propagates, siblings are unaffected, and cancel-done returns `False`.
- [ ] Suppressed cancellation completes normally, and this is tested and documented.
- [ ] No awaiters are wedged, and every test's loop exits.

## Stage 13: Drop-in asyncio comparison

- **Goal:** The same suite runs green against both your loop and real `asyncio` through a thin adapter, with known differences written down.
- **Test:** `uv run pytest tests/test_parity.py` — echo, gather, and cancellation against both backends.
- **Focus:** API parity and differential testing.

### Prerequisites

- Stages 1 through 12 are done.

### Concepts to learn first

- Differential testing means the same inputs, two implementations, and the same assertions.
- Keep the surface minimal: `call_soon`/`call_later`, reader/writer, `create_task`, `sock_*`, and `run_*`/`stop`.
- Optional stretch: subclass `asyncio.AbstractEventLoop` to make it a real backend.

### Interfaces

- A `driver` abstraction that both backends satisfy (`run` plus `sleep`/`gather`/`sock_*`), and a written list of divergences.

### Edge cases & pitfalls

- Assert orderings and results with generous windows; never assert exact interleavings.
- Clean up resources the way each backend expects.
- Cancellation semantics are where parity most likely breaks; capture the differences rather than hiding them.
- Keep the driver's threading model identical across backends.

### Hints

- Which scenario should you start with?
- Categorize failures as a missing feature, a semantic difference, or a timing flake.

### References

- CPython `base_events.py` and `events.py` · [asyncio event loop docs](https://docs.python.org/3/library/asyncio-eventloop.html)

### Done when

- [ ] `tests/test_parity.py` passes on both backends for sleep, gather, echo, and cancellation.
- [ ] `DIFFERENCES.md` documents every divergence with its rationale.
- [ ] The full suite is green: `uv run pytest tests/`.

## Acceptance

A single-threaded, epoll-backed event loop that schedules callbacks and timers, drives native `async def` coroutines through Futures and Tasks, serves many concurrent TCP connections, and handles cancellation and exception propagation. It passes the same test suite as real `asyncio`.
