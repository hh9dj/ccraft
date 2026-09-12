# Project: Event Loop / Async Runtime

Implement a single-threaded event loop (reactor) that monitors multiple I/O sources for readiness and dispatches callbacks or tasks. Optionally add an executor for coroutines/futures to show cooperative multitasking.

- **Language:** Python (3.12, managed with `uv`)
- **Focus areas:** OS I/O multiplexing (`select`/`poll`/`epoll`/`kqueue`, file descriptors), non-blocking I/O, event-driven concurrency, cooperative multitasking, how `async/await` works under the hood
- **Build/test command:** `uv run pytest tests/` and `uv run main.py` (run from `loop/`)

## Milestones

1. **Callback loop** (Stages 0–2) — ready queue, `call_soon`, timers.
2. **I/O reactor** (Stages 3–4) — readiness dispatch over fds via `selectors`.
3. **Cooperative multitasking** (Stages 5–7) — generators, `yield from`, Futures, Tasks.
4. **async/await executor** (Stages 8–9) — native coroutines, `create_task`, `gather`.
5. **Beast mode** (Stages 10–13) — TCP echo server; cancellation, exception propagation, asyncio parity.

## Similar Projects & Libraries

Read these for inspiration; don't copy. Prefer the listed entry points.

- [CPython `asyncio`](https://github.com/python/cpython/tree/main/Lib/asyncio) (Python) — canonical reference: `base_events.py` (`_run_once`), `selector_events.py`, `futures.py`, `tasks.py`.
- [uvloop](https://github.com/MagicStack/uvloop) (Cython/C) — asyncio loop on libuv; see `uvloop/loop.pyx` for watcher/timer mapping.
- [libuv](https://github.com/libuv/libuv) (C) — Node's loop; `src/unix/core.c` (`uv_run`), `src/timer.c`, `src/unix/loop-watcher.c`.
- [Redis `ae.c`](https://github.com/redis/redis/blob/unstable/src/ae.c) (C) — compact production loop: ready queue + timer heap + `poll`.
- [Trio](https://github.com/python-trio/trio) (Python) — structured concurrency; `_core/_run.py`, `_core/_traps.py`.
- [Curio](https://github.com/dabeaz/curio) (Python) — minimal generator-based kernel; `curio/kernel.py`, `curio/io.py`.
- [gevent](https://github.com/gevent/gevent) (Python) — greenlet hub loop; implicit switching contrast.
- [Tokio](https://github.com/tokio-rs/tokio) (Rust) — work-stealing executor; `runtime/scheduler/`, `io/`.
- [Boost.Asio](https://github.com/boostorg/asio) (C++) — proactor/completion model vs readiness.

## Contents

- [ ] [Stage 0: Setup](#stage-0-setup)
- [ ] [Stage 1: A bare loop with `call_soon`](#stage-1-a-bare-loop-with-call_soon)
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

- **Goal:** `uv`-managed Python 3.12 project with pytest, a `loop/` package skeleton, and `main.py` entry point.
- **Test:** `uv run pytest tests/test_smoke.py`.
- **Focus:** tooling; test-driven stage discipline.

### Prerequisites

- `uv` installed; `loop/pyproject.toml` + `.python-version` (3.12) exist.
- Basic pytest.

### Concepts to learn first

- Always run via `uv run` so `.python-version` pins the interpreter.
- Zero runtime deps: stdlib only (`selectors`, `heapq`, `time`, `socket`).

### Interfaces

- `loop/__init__.py` exports `EventLoop`
- `loop/loop.py` (Stages 1–4), `loop/futures.py` (Stage 7), `loop/sock.py` (Stage 10), `tests/`

### Edge cases & pitfalls

- Don't `pip install`; that corrupts `uv.lock`.
- Keep tests hermetic: `os.pipe()` / `socket.socketpair()`, no network.

### Hints

- Which fixture gives every test a fresh `EventLoop`?
- Confirm `uv run main.py` works end-to-end before Stage 1.

### References

- [uv docs](https://docs.astral.sh/uv/) · [pytest docs](https://docs.pytest.org/en/stable/)

### Done when

- [ ] `uv run pytest` exits 0 with the smoke test.
- [ ] `uv run main.py` runs.
- [ ] Package skeleton matches the layout above.

## Stage 1: A bare loop with `call_soon`

- **Goal:** Smallest `EventLoop`: ready-queue of callbacks, `call_soon()`, `run_forever()`, exit-when-idle.
- **Test:** `uv run pytest tests/test_call_soon.py`.
- **Focus:** event-driven programming, loop lifecycle.

### Prerequisites

- Stage 0 done; `EventLoop` importable.

### Concepts to learn first

- A loop is a queue plus a `while`: pop work, run it. Later sources just enqueue.
- `collections.deque` for O(1) ends; avoid `list.pop(0)`.
- Liveness = nothing left to do. Later this generalizes to timers + fds.

### Interfaces

- `EventLoop()` · `call_soon(cb, *args)` · `run_forever()` · `stop()`

### Edge cases & pitfalls

- Exceptions in a callback must not kill the loop.
- Reentrant `run_forever` must be rejected (guard `_running`).
- Decide `stop()` semantics: drop queued callbacks or drain? Document it.

### Hints

- Mirror asyncio names now for Stage 13.
- What gets enqueued is where the real design lives.

### References

- [30-line asyncio loop](https://dev.to/ritesh_fcb86fb4b3890c81e4/build-a-working-asyncio-event-loop-in-30-lines-of-plain-python-5gjb) · CPython `base_events.py`

### Done when

- [ ] Ordered execution, exit-when-idle, `stop()` halts, callback errors contained.
- [ ] `run_forever` returns immediately when nothing is scheduled.

## Stage 2: Timers (`call_later`)

- **Goal:** `call_later(delay, cb)` with a monotonic min-heap; sleep just enough; fire expired timers in deadline order.
- **Test:** `uv run pytest tests/test_timers.py` — deadline order; wall time ≈ max delay, not sum.
- **Focus:** timers as events; where the loop blocks.

### Prerequisites

- Stage 1 done; comfort with `heapq`.

### Concepts to learn first

- A timer is work whose condition is "clock passed deadline"; promote expired to ready each tick.
- Heap: O(log n) insert, O(1) peek.
- `time.monotonic()` never jumps backwards — use it for deadlines.
- The "how long may I block" budget seeds Stage 4's `select(timeout)`.

### Interfaces

- `call_later(delay, cb, *args)` · helpers to promote expired timers and compute the block timeout.

### Edge cases & pitfalls

- Equal deadlines compare the next tuple element — include a sequence tiebreaker.
- Missing sleep-until-deadline = 100% CPU spin.
- `call_later(0, ...)` behaves like `call_soon`; clamp negatives.
- Tests: use tolerance; assert `elapsed >= delay`, generous upper bound.

### Hints

- What value later replaces `time.sleep()` in `select()`?
- How would you prove a +50 ms timer ran between two +100 ms closures?

### References

- [Build your own Event Loop](https://techtalk.digitalpress.blog/build-your-own-event-loop-in-python/) · [PEP 418](https://peps.python.org/pep-0418/)

### Done when

- [ ] Deadline order, wall ≈ max delay, `call_later(0)` fires next tick.
- [ ] Loop exits when ready queue and timers are empty.
- [ ] No hot spin while waiting.

## Stage 3: Readiness polling with `selectors`

- **Goal:** `add_reader` / `add_writer` backed by `selectors.DefaultSelector`; wake on fd readiness instead of polling.
- **Test:** `uv run pytest tests/test_selectors.py` — write to an `os.pipe()`, reader callback fires.
- **Focus:** I/O multiplexing, fds, non-blocking I/O.

### Prerequisites

- Stage 2 done; loop computes a block timeout.

### Concepts to learn first

- Readiness ≠ completion: the OS says a fd is ready; your callback still does the read.
- `DefaultSelector` picks `epoll`/`kqueue`/`select`; API: `register`, `select(timeout)`, `unregister`.
- Store the callback as the selector `data`.

### Interfaces

- `add_reader(fd, cb, *args)` / `add_writer(...)` · `remove_reader(fd)` / `remove_writer(fd)`

### Edge cases & pitfalls

- Double-register raises `KeyError`; pick replace/ignore/raise and test it.
- Zero fds + `timeout=None` blocks forever — exit condition must check before blocking.
- Level-triggered: drain or you get woken every tick.
- Always pair `close` with `remove_*` (fd reuse).

### Hints

- Why `os.pipe()` before sockets?
- Inline dispatch vs enqueue into the ready path — which simplifies exceptions?

### References

- [selectors docs](https://docs.python.org/3/library/selectors.html) · [Demystifying AsyncIO](https://slides.com/art049/demystifying-asyncio)

### Done when

- [ ] Pipe write → reader fires with correct bytes; `remove_reader` stops it.
- [ ] Zero fds + zero timers + empty queue exits, not hangs.
- [ ] Reader and writer on the same fd coexist.

## Stage 4: The complete loop tick

- **Goal:** Formalize `_run_once()` blending ready callbacks, timer deadlines, and selector waits.
- **Test:** `uv run pytest tests/test_run_once.py` — pipe reader + 50 ms timer both fire; loop exits when drained.
- **Focus:** timeout computation, fair scheduling order.

### Prerequisites

- Stage 3 done.

### Concepts to learn first

- `_run_once` phases: compute timeout → select → promote I/O → promote timers → run ready. Learn order from the source.
- Timeout rule: ready work → 0; else next deadline; else `None` if fds registered, else exit.
- Everything funnels through `_ready`, so no source starves another.

### Interfaces

- `_run_once()` · `_compute_timeout()` → `0` | delay | `None`

### Edge cases & pitfalls

- Cap per-tick drain (`_ntodo` snapshot) so chatty callbacks can't starve.
- Catch `InterruptedError` from `select`.
- Recompute `now` after `select`; timers that expired during the wait fire this tick.
- Never call `select(None)` when the exit condition holds.

### Hints

- Line your phases up against asyncio's; which orderings change precision?
- Where is the single exception choke point?

### References

- CPython `base_events.py` (`_run_once`) · [Redis `ae.c`](https://github.com/redis/redis/blob/unstable/src/ae.c) · [libuv core.c](https://github.com/libuv/libuv/blob/v1.x/src/unix/core.c)

### Done when

- [ ] Mixed timer + I/O workload completes; loop exits when drained.
- [ ] `_compute_timeout` unit tests: 0 / ≈delay / `None`.
- [ ] Self-rescheduling `call_soon` doesn't starve a 10 ms timer.

## Stage 5: Generators as coroutines

- **Goal:** Drive generators as tasks: `next()` to `yield` (suspend) or `StopIteration` (done).
- **Test:** `uv run pytest tests/test_generators.py` — two tasks interleave; wall ≈ max sleep.
- **Focus:** cooperative multitasking, pause/resume mechanics.

### Prerequisites

- Stage 4 done; generators know `yield`/`send`.

### Concepts to learn first

- Generator = pausable frame; the loop is the resumer.
- Cooperative: the task decides when to yield; a non-yielding task freezes the loop.
- `return value` raises `StopIteration(value)` — the result channel.

### Interfaces

- `sleep_gen(seconds)` — generator yielding until deadline; stepper detects completion.

### Edge cases & pitfalls

- Requeue-on-yield with no wait spins 100% — expected here; timers fix it next.
- Forgetting `StopIteration` reschedules finished tasks forever.
- Uncaught task exceptions propagate out of `next()` — record, don't reschedule.

### Hints

- Minimal state a driven generator needs?
- Which timestamp trace proves true interleaving?

### References

- [30-line loop](https://dev.to/ritesh_fcb86fb4b3890c81e4/build-a-working-asyncio-event-loop-in-30-lines-of-plain-python-5gjb) · [Recreating asyncio](https://jacobpadilla.com/writing/recreating-asyncio)

### Done when

- [ ] Interleaved order, wall ≈ max sleep.
- [ ] Finished generators never requeued.
- [ ] `yield from sleep_gen()` composition works.

## Stage 6: `yield from` delegation

- **Goal:** Nested generators: sends/throws pass both ways; sub-generator's return value surfaces.
- **Test:** `uv run pytest tests/test_delegation.py` — inner sleep, return value, exception propagation.
- **Focus:** PEP 380 as the desugaring of `await`.

### Prerequisites

- Stage 5 done.

### Concepts to learn first

- `yield from` is a transparent bidirectional channel, not a loop.
- `await x` ≡ `yield from x.__await__()`.
- The loop only sees the innermost yields.

### Edge cases & pitfalls

- Never swallow exceptions mid-chain; establish propagate-or-resolve.
- Preserve `StopIteration.value` in your stepper.
- `send(x)` before first `next()` raises `TypeError`.
- `yield sleep_gen(1)` yields the generator object (junk) — classic typo.

### Hints

- How does PEP 380 explain send/throw passthrough?
- If the loop receives a raw generator, which mistake produced it?

### References

- [PEP 380](https://peps.python.org/pep-0380/) · [Custom Event Loop guide](https://www.codingpancake.com/2026/07/how-to-implement-custom-event-loop-in.html)

### Done when

- [ ] Return values through 1 and 3 nesting levels; inner exception propagates.
- [ ] Stage 5 stepper unchanged — nesting transparent.
- [ ] No hangs from `yield` vs `yield from` typos.

## Stage 7: Futures and Tasks

- **Goal:** `Future` (a value not ready yet) + `Task` (coroutine driver), so tasks yield a Future and sleep without spinning.
- **Test:** `uv run pytest tests/test_futures.py` — timer resolves a Future; task resumes with the value; `sleep()` interleaves with ~no spin.
- **Focus:** cooperative multitasking without polling.

### Prerequisites

- Stages 5–6 done.

### Concepts to learn first

- Future holds result/done/callbacks; `set_result` fires them.
- Suspend/resume: yield a Future → register re-wake → stop stepping → resolve → `send(value)`.
- `Future.__await__` is `return (yield self)` — the bridge to `await`.
- `loop.call_later(deadline, future.set_result, value)` supplies the wake-up.

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

- Lost-task trap: keep strong refs; log unretrieved exceptions.
- Yielding a non-Future raises `RuntimeError`.
- Double `set_result` raises.
- `result()` on unfinished Future raises — waiting is only via `yield`/`await`.

### Hints

- How to prove the loop no longer spins while a task sleeps?
- Should `Future` know the loop? Why keep it loop-agnostic?

### References

- CPython `futures.py` + `tasks.py` · [Asyncio Demystified](https://dev.indooroutdoor.io/asyncio-demystified-rebuilding-it-from-scratch-one-yield-at-a-time)

### Done when

- [ ] Yield-Future → timer-resolve → resume; exception stored and raised.
- [ ] `sleep()` interleaving test, wall ≈ max delay, no spin.
- [ ] Non-Future yield and double `set_result` raise.

## Stage 8: Native coroutines

- **Goal:** `async def` / `await` run on your loop unchanged — same Task, Future, tick.
- **Test:** `uv run pytest tests/test_native_coros.py` — Stage 7 scenarios rewritten in `async def`.
- **Focus:** how `async`/`await` desugar; `__await__` interop.

### Prerequisites

- Stage 7 done.

### Concepts to learn first

- `async def` returns a coroutine, not a generator; drive with `send(None)`/`throw`.
- `await x` ≈ `yield from x.__await__()` (see PEP 492).
- First resume must send `None`.

### Interfaces

- `run_until_complete(awaitable)` — returns result or raises.

### Edge cases & pitfalls

- Awaiting a bare generator raises `TypeError` (good type discipline).
- `yield` inside `async def` makes an async generator — unsupported here; lint it.
- Nested `run_until_complete` must raise (guard `_running`).

### Hints

- How small is the diff from Stage 7?
- Why keep one generator-based test after the rewrite?

### References

- [PEP 492](https://peps.python.org/pep-0492/) · [Recreating asyncio](https://jacobpadilla.com/writing/recreating-asyncio)

### Done when

- [ ] Same assertions as Stage 7 pass in `async def` syntax.
- [ ] `run_until_complete` returns value / propagates exception.
- [ ] Stage 5 generator tests still pass untouched.

## Stage 9: `gather`

- **Goal:** `gather(*awaitables)` — await many children concurrently, ordered results in ≈max delay.
- **Test:** `uv run pytest tests/test_gather.py` — 50/100/150 ms sleeps finish in ≈150 ms, results in argument order; one exception surfaces.
- **Focus:** fan-out/fan-in, Future composition.

### Prerequisites

- Stage 8 done.

### Concepts to learn first

- Wrap children in Tasks, attach callbacks, count down, resolve one parent Future.
- Results land in argument order regardless of finish order.
- Choose failure semantics (fail-fast/cancel siblings vs await the rest) and document.

### Interfaces

- `gather(*awaitables) -> Future`; empty `gather()` resolves `[]` immediately.

### Edge cases & pitfalls

- Bind loop indices (`i=i`) to avoid late-binding closure bugs.
- `add_done_callback` fires immediately for done Futures — test already-done children.
- After the parent resolves, later completions must be ignored.
- Nesting `gather(gather(...), ...)` should work.

### Hints

- Where else does the countdown-latch pattern recur?
- Does `gather` need the loop, or only child creation?

### References

- CPython `tasks.py` (`gather`) · [Asyncio Demystified](https://dev.indooroutdoor.io/asyncio-demystified-rebuilding-it-from-scratch-one-yield-at-a-time)

### Done when

- [ ] Ordered results, wall ≈ max delay, empty + nested gather pass.
- [ ] Failure semantics documented and tested.
- [ ] No closure index bug.

## Stage 10: Async socket I/O primitives

- **Goal:** Awaitable `sock_recv` / `sock_sendall` / `sock_accept` as Futures resolved from selector callbacks.
- **Test:** `uv run pytest tests/test_sock_io.py` — `socketpair()` client/server echo, exact bytes both sides.
- **Focus:** non-blocking I/O; readiness as Future resolution.

### Prerequisites

- Stage 7 done; Stages 3–4 done.

### Concepts to learn first

- `setblocking(False)` makes `recv` raise `BlockingIOError`; try, then register + suspend, retry on readiness.
- One-shot selector registration, unregistered on first firing.
- Partial sends loop until all sent; `recv` `b""` = orderly shutdown.

### Interfaces

- `sock_recv(loop, sock, n) -> bytes` · `sock_sendall(loop, sock, data) -> None` · `sock_accept(loop, listener) -> (conn, addr)`

### Edge cases & pitfalls

- A blocking `recv` freezes the whole loop — assert non-blocking in the primitives.
- Spurious wakeups: always `try/except BlockingIOError`.
- Unregister before resolving (fd reuse).
- `sock_recv` returns up to `n` bytes — tests frame accordingly.

### Hints

- Why mirror asyncio's `sock_*` signatures?
- Functions + one-shot callbacks vs Future subclasses — which fits?

### References

- CPython `selector_events.py` · [socket docs](https://docs.python.org/3/library/socket.html)

### Done when

- [ ] socketpair + loopback TCP echo with exact-byte assertions.
- [ ] A concurrent timer fires on schedule during a pending `sock_recv`.
- [ ] Spurious-wakeup and partial-send paths tested.

## Stage 11: Echo server end-to-end

- **Goal:** Concurrent TCP echo server on your loop — one task per connection, N clients, single thread.
- **Test:** `uv run pytest tests/test_echo_server.py` — N threaded clients with distinct payloads each get their own bytes back.
- **Focus:** concurrent servers without threads; fd lifecycle.

### Prerequisites

- Stage 10 done.

### Concepts to learn first

- Accept loop + per-connection task; interleaving happens at `await` points.
- A slow client suspends only its own task (parked on the selector).

### Interfaces

- `serve_forever(loop, listener)` · `handle_client(loop, conn)`

### Edge cases & pitfalls

- Unregister + close on every exit path; `finally` non-negotiable.
- `recv` → `b""`: break, don't re-register.
- Listener: `SO_REUSEADDR`, `bind`, `listen(>=100)`, non-blocking.
- Test teardown: stop loop, close listener, join thread with timeout.
- Catch `ConnectionResetError` from killed clients.

### Hints

- Why start with a few clients before 50+?
- How will you detect an fd leak?

### References

- [Single-threaded non-blocking server](https://prodsens.live/2025/05/12/building-your-own-web-server-part-4-single-threaded-non-blocking-server/) · [Asyncio Demystified](https://dev.indooroutdoor.io/asyncio-demystified-rebuilding-it-from-scratch-one-yield-at-a-time)

### Done when

- [ ] N concurrent distinct echoes; slow clients don't block fast ones; connection count returns to 0.
- [ ] fd count stable across runs; RST-killed client doesn't wedge the server.
- [ ] Wall time proves concurrency.

## Stage 12: Cancellation & exception propagation

- **Goal:** `task.cancel()` injects `CancelledError` at the suspension point; exceptions propagate through `await` chains to `task.result()`.
- **Test:** `uv run pytest tests/test_cancellation.py` — cancel a sleeping task; 3-deep raise surfaces exactly.
- **Focus:** cancellation as a first-class op; exception flow through frames.

### Prerequisites

- Stages 7–8 done; Stage 6 `throw()` propagation understood.

### Concepts to learn first

- Cancel = `coro.throw(CancelledError)` where the task is parked.
- `CancelledError` inherits `BaseException`; catch it distinctly from `Exception`.
- A child exception must reach the awaiter and mark the child done — never leave a parked awaiter.

### Interfaces

- `Task.cancel() -> bool` · `Task.cancelled() -> bool` · `Task.exception()` / `Task.result()` state semantics.

### Edge cases & pitfalls

- Swallowed `CancelledError` (bare `except BaseException`) converts cancel to hang.
- Cancelling a done task returns `False`, does nothing.
- Guard double-resolve after cancel (`if self.done(): return`).
- Cancelling the last task must still let the loop exit.

### Hints

- Model the pending → cancelling → cancelled/finished states.
- Which timings hit distinct branches (before step, mid-sleep, done, twice)?

### References

- CPython `tasks.py` · [PEP 492](https://peps.python.org/pep-0492/) · [Trio `_run.py`](https://github.com/python-trio/trio/blob/main/src/trio/_core/_run.py)

### Done when

- [ ] Mid-sleep cancel → `CancelledError`; 3-deep raise propagates; siblings unaffected; cancel-done returns False.
- [ ] Suppressed cancellation completes normally, tested and documented.
- [ ] No wedged awaiters; every test's loop exits.

## Stage 13: Drop-in asyncio comparison

- **Goal:** Same suite runs green against your loop and real `asyncio` via a thin adapter; known differences written down.
- **Test:** `uv run pytest tests/test_parity.py` — echo + gather + cancellation against both backends.
- **Focus:** API parity; differential testing.

### Prerequisites

- Stages 1–12 done.

### Concepts to learn first

- Differential testing: same inputs, two implementations, same assertions.
- Minimal surface: `call_soon`/`call_later`, reader/writer, `create_task`, `sock_*`, `run_*`/`stop`.
- Optional stretch: subclass `asyncio.AbstractEventLoop` as a real backend.

### Interfaces

- A `driver` abstraction both backends satisfy (`run` + `sleep`/`gather`/`sock_*`); a written divergences list.

### Edge cases & pitfalls

- Assert orderings/results and generous windows — never exact interleavings.
- Clean up resources each backend's way.
- Cancellation semantics are where parity most likely breaks — capture, don't hide.
- Keep the driver's threading model identical across backends.

### Hints

- Which scenario to start with?
- Categorize failures: missing feature, semantic difference, or timing flake.

### References

- CPython `base_events.py` + `events.py` · [asyncio event loop docs](https://docs.python.org/3/library/asyncio-eventloop.html)

### Done when

- [ ] `tests/test_parity.py` passes on both backends for sleep, gather, echo, cancellation.
- [ ] `DIFFERENCES.md` documents every divergence with rationale.
- [ ] Full suite green: `uv run pytest tests/`.

## Acceptance

A single-threaded, epoll-backed event loop that schedules callbacks and timers, drives native `async def` coroutines via Futures/Tasks, serves many concurrent TCP connections, handles cancellation and exception propagation — and passes the same suite as real `asyncio`.
