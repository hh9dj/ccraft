# Project: Event Loop / Async Runtime

Implement a single-threaded event loop (reactor) that monitors multiple I/O sources (e.g., network sockets, files) for readiness and dispatches user-defined callbacks or tasks when events occur. Optionally, build an "executor" on top to manage coroutines/futures, demonstrating cooperative multitasking.

- **Language:** Python (3.12, managed with `uv`)
- **Focus areas:** OS I/O multiplexing (`select`/`poll`/`epoll`/`kqueue`, file descriptors), non-blocking I/O, event-driven concurrency, cooperative multitasking, how `async/await` works under the hood
- **Build/test command:** `uv run pytest tests/` (add `uv add --dev pytest` in Stage 0) and `uv run main.py`

## Milestone checkpoints

1. **Callback loop** — a runnable scheduler with `call_soon` / `call_later` (timers).
2. **I/O reactor** — readiness-based dispatch over file descriptors via `selectors`.
3. **Cooperative multitasking** — generators, `yield from`, Futures, Tasks.
4. **async/await executor** — native coroutines + `__await__` interop, `create_task`, `gather`.
5. **Beast mode** — real non-blocking TCP echo server on your loop; cancellation, exception propagation, and asyncio parity tests.

## Stage 0: Setup

- **Goal:** `uv` project runs, pytest wired up, package layout (`loop/` package + `main.py` entry point).
- **Test:** `uv add --dev pytest && uv run pytest` — passes with a trivial smoke test (`tests/test_smoke.py` importing the package).
- **Hints:** Python 3.14 is the system default but the project pins 3.12 via `.python-version` — always run through `uv run`. Keep zero runtime dependencies; the whole point is stdlib (`selectors`, `collections.deque`, `heapq`, `time`, `socket`).

## Milestone 1 — Callback loop

- [ ] **Stage 1: A bare loop with `call_soon`**
  - **Goal:** `EventLoop` with a `deque` ready-queue; `call_soon(cb)` appends, `run_forever()` pops and executes until queue empties (or `stop()` is called).
  - **Test:** `uv run pytest tests/test_call_soon.py` — schedule two callbacks, assert execution order and that `run_forever` returns.
  - **Hints:** Use `collections.deque` (O(1) popleft). Catch exceptions per-callback so one failing callback doesn't kill the loop — collect them instead. Decide loop-liveness early: the loop should exit when there's nothing pending (this gets more subtle once timers/I/O arrive).

- [ ] **Stage 2: Timers (`call_later`)**
  - **Goal:** `call_later(delay, cb)` using a `heapq` min-heap of `(deadline, seq, cb)`; expired timers move to the ready queue each iteration.
  - **Test:** test asserting two callbacks fire in deadline order, and total wall time ≈ max delay (proves non-blocking interleaving).
  - **Hints:** Add a monotonic sequence tiebreaker to heap entries so equal deadlines don't compare callbacks (Python can't order functions). Use `time.monotonic()`, not `time.time()`. Compute `select` timeout as `next_deadline - now` — don't busy-spin.

## Milestone 2 — I/O reactor

- [ ] **Stage 3: Readiness polling with `selectors`**
  - **Goal:** `add_reader(fd, cb)` / `add_writer(fd, cb)` backed by `selectors.DefaultSelector`; the loop iteration becomes: run ready callbacks → compute timeout from timers → `selector.select(timeout)` → dispatch ready fds → fire expired timers.
  - **Test:** write to one end of a pipe (`os.pipe`), register a reader on the other end, assert the callback fires with correct data.
  - **Hints:** `DefaultSelector` picks `epoll` on Linux, `kqueue` on macOS — mention this in a comment. Store the callback as selector `data`. This is the real "reactor" step: the OS sleeps the thread for you, replacing the polling `time.sleep(0.001)` hack.

- [ ] **Stage 4: The complete loop tick**
  - **Goal:** Refactor into `_run_once()`: (1) drain ready queue, (2) compute timeout (0 if ready non-empty, else next timer deadline, else None), (3) `select(timeout)`, (4) dispatch I/O callbacks, (5) move expired timers to ready.
  - **Test:** integration test mixing timers + pipe I/O: a reader and a 50ms timer both fire within one `run_forever()` call.
  - **Hints:** This tick structure is exactly asyncio's (see `BaseEventLoop._run_once`). Edge cases: timeout must be 0 when ready callbacks are pending (don't block on select with work queued); handle `InterruptedError` from `select` (signals); loop exit condition = no ready, no timers, no registered fds.

## Milestone 3 — Cooperative multitasking

- [ ] **Stage 5: Generators as coroutines**
  - **Goal:** Drive generator objects in the ready queue with `next(task)`; a task that `yield`s suspends and is re-queued. Implement a generator-based `sleep` that yields its deadline.
  - **Test:** two generator "tasks" print interleaved output; assert interleaving order and that total runtime ≈ max sleep, not the sum.
  - **Hints:** This is the conceptual core — a `yield` is a bookmark the loop resumes later. Handle `StopIteration` to mark task completion. Don't re-queue a finished task.

- [ ] **Stage 6: `yield from` delegation**
  - **Goal:** Sub-generators: `yield from sleep(1)` propagates yields up to the loop and return values back down via `StopIteration.value`.
  - **Test:** a delegating generator awaits an inner sleep and receives its return value.
  - **Hints:** `yield from` is the desugaring of `await`. Read PEP 380's expansion if the semantics feel fuzzy — it's a state machine for bidirectional `send`/`throw` passthrough.

- [ ] **Stage 7: Futures and Tasks**
  - **Goal:** `Future` with `set_result`, `add_done_callback`, `done()`; `Task(Future)` wraps a coroutine, calls `send(None)` to step it, and when the coroutine yields a Future, registers a callback that re-schedules the task on resolution. Add `loop.create_task(coro)` and a `sleep` implemented as a timer-resolved Future.
  - **Test:** `await`-style flow: task yields a Future, loop resolves it via timer, task resumes with the result. Assert result values and completion order.
  - **Hints:** `Future.__await__` is literally `return (yield self)` — pause the coroutine by yielding the future, resume via callback `task.send(result)`. Catch exceptions from `send()` and store them in the Future; re-raise in `result()`. Beware the "lost task" trap: a task nobody awaits whose exception is silently swallowed.

## Milestone 4 — async/await executor

- [ ] **Stage 8: Native coroutines**
  - **Goal:** Replace generator syntax with `async def` / `await`. Verify `async def` functions work on your loop unchanged — the runtime protocol is identical.
  - **Test:** rewrite the Stage 7 tests with `async def` mains; same assertions pass.
  - **Hints:** `await x` ≈ `yield from x.__await__()`. `async def` just changes the function type (Coroutine vs Generator) — no magic. First `send` must be `send(None)`; you can't `send` a value into a not-yet-started coroutine.

- [ ] **Stage 9: `gather` and waiting on multiple tasks**
  - **Goal:** `gather(*tasks)` returns a Future resolved when all children complete, collecting results (and exceptions).
  - **Test:** three tasks with different sleeps complete in ~max delay with correct result order.
  - **Hints:** Track a completion counter; each child callback decrements and resolves the parent when it hits zero. Decide early-failure semantics (asyncio cancels siblings — a simplified version may just collect the exception).

- [ ] **Stage 10: Async socket I/O primitives**
  - **Goal:** `await sock_recv(sock, n)` / `await sock_accept(sock)` / `await sock_send(sock, data)` implemented as Futures that register with the selector.
  - **Test:** async client/server over `socketpair()`; client sends, server receives, result assertions on both sides.
  - **Hints:** Sockets must be `setblocking(False)` — a blocking call inside the loop freezes everything. On write-readiness, don't forget `EAGAIN`/partial sends. This stage finally replaces Stage 7's polling Futures with real OS readiness events.

## Milestone 5 — Acceptance (beast mode)

- [ ] **Stage 11: Echo server end-to-end**
  - **Goal:** Concurrent TCP echo server running purely on your loop: `async def handle(conn)` per client via `create_task`, hundreds of simultaneous connections on one thread.
  - **Test:** script spins up the server, opens N concurrent client sockets sending different payloads, asserts every client gets its own payload echoed. Compare timing vs a serial server.
  - **Hints:** This mirrors the classic CodeCrafters "build your own event loop" endgame. Handle client disconnect (`recv` returns `b""` → unregister + close). Watch for fd leaks — close sockets and unregister from the selector.

- [ ] **Stage 12: Cancellation, exception propagation, asyncio parity**
  - **Goal:** `task.cancel()` raises `CancelledError` at the await point; exceptions propagate through `await` chains to `task.result()`; a failing task never wedges the loop.
  - **Test:** cancel a sleeping task mid-flight and assert `CancelledError`; raise inside a nested coroutine and assert the exception surfaces at the awaiting task.
  - **Hints:** Cancellation = `coro.throw(CancelledError)` at the right moment. The classic pitfall: a sub-coroutine swallowing exceptions leaves outer tasks suspended forever — always propagate to the root Task frame.

- [ ] **Stage 13: Drop-in asyncio comparison**
  - **Goal:** Run the same echo-server test suite against both your loop and real `asyncio` via a thin abstraction layer; document behavioral differences in the README.
  - **Test:** parametrized pytest fixture running the Stage 11 suite against `MyEventLoop()` and `asyncio.run()`.
  - **Hints:** asyncio's extra machinery is corner cases (cancellation propagation, exception groups, signal handling), not new mechanisms. Optionally implement `asyncio.AbstractEventLoop`'s minimal interface (`call_soon`, `call_later`, `add_reader`, `create_task`, `run_forever`) and plug in via an event loop policy.

## Acceptance

Full parity check: a single-threaded, epoll-backed event loop that schedules callbacks and timers, drives native `async def` coroutines through Futures/Tasks, serves hundreds of concurrent TCP connections, handles cancellation and exception propagation correctly — and passes the same test suite as real `asyncio`.

## References

- [Asyncio Demystified: Rebuilding it From Scratch One Yield at a Time](https://dev.indooroutdoor.io/asyncio-demystified-rebuilding-it-from-scratch-one-yield-at-a-time) — generator → Future → selector progression, echo server
- [How Python Asyncio Works: Recreating it from Scratch](https://jacobpadilla.com/writing/recreating-asyncio) — `__await__`/Task mechanics
- [Build a working asyncio event loop in 30 lines](https://dev.to/ritesh_fcb86fb4b3890c81e4/build-a-working-asyncio-event-loop-in-30-lines-of-plain-python-5gjb) — the minimal toy loop (Stage 5 shape)
- [Build your own Event Loop in Python](https://techtalk.digitalpress.blog/build-your-own-event-loop-in-python/) — callback-style Scheduler with `select`, timers, non-blocking sockets (Stages 1–4 shape)
- [Let's build an asyncio runtime from scratch](http://bolu.dev/python/programming/2024/05/23/asyncio-from-scratch.html) — Task wrapper + `__await__` details
- [Demystifying AsyncIO slides](https://slides.com/art049/demystifying-asyncio) — implementing `AbstractEventLoop`, fd table, full server trace
- [PEP 380](https://peps.python.org/pep-0380/) — `yield from` semantics; [PEP 492](https://peps.python.org/pep-0492/) — async/await protocol
- CPython source: `Lib/asyncio/base_events.py` (`_run_once`) and `Lib/asyncio/futures.py` — the real thing your loop mirrors
