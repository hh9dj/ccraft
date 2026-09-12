# Project: Event Loop / Async Runtime

Implement a single-threaded event loop (reactor) that monitors multiple I/O sources (e.g., network sockets, files) for readiness and dispatches user-defined callbacks or tasks when events occur. Optionally, build an "executor" on top to manage coroutines/futures, demonstrating cooperative multitasking.

- **Language:** Python (3.12, managed with `uv`)
- **Focus areas:** OS I/O multiplexing (`select`/`poll`/`epoll`/`kqueue`, file descriptors), non-blocking I/O, event-driven concurrency, cooperative multitasking, how `async/await` works under the hood
- **Build/test command:** `uv add --dev pytest` (Stage 0), then `uv run pytest tests/` and `uv run main.py`

## Milestones

1. **Callback loop** (Stages 0–2) — a runnable scheduler with `call_soon` / `call_later` (timers).
2. **I/O reactor** (Stages 3–4) — readiness-based dispatch over file descriptors via `selectors`.
3. **Cooperative multitasking** (Stages 5–7) — generators, `yield from`, Futures, Tasks.
4. **async/await executor** (Stages 8–9) — native coroutines + `__await__` interop, `create_task`, `gather`.
5. **Beast mode** (Stages 10–13) — non-blocking TCP echo server on your loop; cancellation, exception propagation, asyncio parity.

## Similar Projects & Libraries

Real implementations that solve the same problem; read their source for inspiration, don't copy it. Prefer the readable entry points listed here.

- [CPython `asyncio`](https://github.com/python/cpython/tree/main/Lib/asyncio) (Python) — the canonical reference. Study `base_events.py` (`_run_once`, `_compute_timeout`, `call_soon`/`call_later`), `selector_events.py` (`_sock_recv`/`_sock_sendall`/`_accept_connection`), `futures.py` (`Future`, `__await__`), and `tasks.py` (`Task.__step`, `cancel`, `gather`). Stages 1–13 mirror these files one by one.
- [uvloop](https://github.com/MagicStack/uvloop) (Cython/C) — a drop-in asyncio event-loop implementation built on libuv. Study how it maps `add_reader`/`add_writer`/timers onto libuv handles in `uvloop/loop.pyx`, and what real-world performance optimizations exist beyond the toy loop.
- [libuv](https://github.com/libuv/libuv) (C) — the cross-platform event loop behind Node.js. Study `src/unix/core.c` (`uv_run`, the `run_once`-equivalent lifecycle), `src/timer.c` (timer heap), and `src/unix/loop-watcher.c` (I/O watchers). This is the "how a production reactor is structured" view.
- [Redis `ae.c`](https://github.com/redis/redis/blob/unstable/src/ae.c) (C) — a compact, very readable single-file event loop with `select`/`epoll`/`kqueue` backends, a ready queue, and timer processing. A great second data point for Stage 4's `_run_once`.
- [Trio](https://github.com/python-trio/trio) (Python) — an asyncio alternative with structured concurrency and a rigorous cancellation model. Study `src/trio/_core/_run.py` (`Runner`, `_run_impl`), `_io_epoll.py`/`_io_kqueue.py`, and `_core/_traps.py` for how cancellation scopes (nurseries) replace bare `cancel()`.
- [Curio](https://github.com/dabeaz/curio) (Python) — David Beazley's minimal async library built directly on generators/coroutines. Study `curio/kernel.py` for a small, pedagogical kernel and `curio/io.py` for socket primitives; compare its explicit `await`-based cancellation to Stage 12.
- [gevent](https://github.com/gevent/gevent) (Python) — greenlets + a hub event loop (`src/gevent/_hub_primitives.py`, `libev`/`libuv` cores). Useful contrast: implicit cooperative switching via monkey-patching vs. your explicit `await` suspension points.
- [Tokio](https://github.com/tokio-rs/tokio) (Rust) — a modern multi-threaded async runtime. Study `tokio/src/runtime/scheduler/` (work-stealing executor) and `tokio/src/io/` (readiness-driven I/O) to see how far the single-threaded reactor model scales; the two-layer runtime/executor split is worth understanding.
- [Boost.Asio](https://github.com/boostorg/asio) (C++) — a proactor-based alternative to the Unix readiness model. Study its `io_context` design to understand completion-based I/O (Windows IOCP, `io_uring`), the model your `selectors`-based loop deliberately does not use.

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

- **Goal:** A runnable `uv`-managed Python 3.12 project with pytest wired up, a `loop/` package skeleton, and `main.py` as the eventual entry point — so every later stage has a real failing test command to hang off.
- **Test:** `uv run pytest tests/test_smoke.py` — passes once the package imports and one trivial assertion holds.
- **Focus:** Project tooling; sets the "test-driven stages" discipline for everything after.


### Prerequisites

- `uv` installed (`uv --version`). The project already has `pyproject.toml`, `.python-version` (3.12), and `uv.lock`.
- Basic pytest knowledge: fixtures, asserts. Nothing async yet — that's what the rest of the project is for.

### Concepts to learn first

- What `uv` manages: `.python-version` pins the interpreter (3.12 here) even though the system Python is 3.14 — **always run code through `uv run`**, never bare `python3`.
- Why zero runtime dependencies: the entire point of this project is to build the machinery using only the standard library (`selectors`, `collections.deque`, `heapq`, `time`, `socket`, `threading` for test helpers only).

### Interfaces

The package skeleton to design toward (empty modules are fine now):

- `loop/__init__.py` — exports `EventLoop`
- `loop/loop.py` — the event loop itself (Stages 1–4)
- `loop/futures.py` — `Future` / `Task` (Stage 7)
- `loop/sock.py` — async socket primitives (Stage 10)
- `tests/` — pytest suite

### Edge cases & pitfalls

- Don't `pip install` anything — `uv` owns the environment; mixing tools corrupts `uv.lock`.
- Running `pytest` without `uv run` may pick the wrong interpreter (system 3.14 vs pinned 3.12) and behave subtly differently.
- Keep tests fast and hermetic: no network in early stages; use `os.pipe()` and `socket.socketpair()` which work entirely in-process.

### Hints

- Which shared fixture will every stage reuse? Plan a fresh `EventLoop` per test from the start.
- What should your default dev-loop command be, and does it keep tracebacks short?
- Before moving on, confirm the whole chain works end-to-end (`uv run main.py`).

### References

- [uv docs](https://docs.astral.sh/uv/)
- [pytest docs](https://docs.pytest.org/en/stable/)

### Done when

- [ ] `uv run pytest` exits 0 with the smoke test.
- [ ] `uv run main.py` works.
- [ ] `loop/` package skeleton + empty module files exist and match the layout you'll grow into.


## Stage 1: A bare loop with `call_soon`

- **Goal:** The smallest useful `EventLoop`: a ready-queue of callbacks with `call_soon()` to schedule and `run_forever()` to drain — single-threaded, event-driven, exit-when-idle.
- **Test:** `uv run pytest tests/test_call_soon.py` — schedule callbacks, assert execution order and that `run_forever()` returns when the queue is empty.
- **Focus:** Concurrency (event-driven programming), the loop lifecycle.


### Prerequisites

- Stage 0 done: package layout + pytest working, `EventLoop` importable from `loop`.

### Concepts to learn first

- **The event loop as a queue:** at heart, an event loop is a `while` loop that pops work from a queue and runs it. Everything later (timers, I/O, coroutines) just adds _sources that enqueue work_.
- **`collections.deque`:** O(1) `popleft()`/`append()` — use it, not a list (`list.pop(0)` is O(n)).
- **Loop liveness:** the loop exits when there's nothing left to do. Right now "nothing" = empty ready queue; Stages 2–4 will generalize this to "no ready callbacks AND no timers AND no watched fds".
- Why callbacks and not threads: single-threaded means no locks, no races — the only concurrency is interleaving between callback boundaries.

### Interfaces

- `EventLoop()` — constructs with an empty ready queue.
- `call_soon(callback, *args)` — schedule a callback to run soon.
- `run_forever()` — run until stopped or idle.
- `stop()` — request the loop to stop.

### Edge cases & pitfalls

- **Exceptions in callbacks:** wrap the `cb(*args)` call in `try/except`, collect the exception (log + store), and keep going. One bad callback must not kill the loop. (This becomes more structured in Stage 12.)
- **Reentrancy:** a callback that calls `call_soon` must be fine — it just appends to the same deque. But a callback calling `run_forever` again should be rejected (raise if `_running`).
- **`stop()` semantics:** decide whether callbacks scheduled before `stop()` but not yet run get dropped (asyncio drops them). Document your choice in a comment.
- Don't pop from the deque while iterating it — the `while self._ready: popleft()` pattern avoids this.

### Hints

- The shape of a minimal loop is a queue plus a `while`. What gets enqueued is where the real design lives.
- Should your names mirror asyncio's (`call_soon`, `call_later`, `run_forever`, `stop`)? What does that buy you in Stage 13?
- Which scenario is not worth testing until timers/I/O exist, and why?

### References

- [Build a working asyncio event loop in 30 lines of plain Python](https://dev.to/ritesh_fcb86fb4b3890c81e4/build-a-working-asyncio-event-loop-in-30-lines-of-plain-python-5gjb)
- [Build your own Event Loop in Python](https://techtalk.digitalpress.blog/build-your-own-event-loop-in-python/) — Scheduler with ready/sleeping queues
- CPython `Lib/asyncio/base_events.py` — `run_forever`/`stop` semantics

### Done when

- [ ] `uv run pytest tests/test_call_soon.py` passes: ordered execution, exit-when-idle, `stop()` halts processing, callback exceptions don't kill the loop.
- [ ] No busy state: `run_forever` returns immediately when nothing is scheduled.


## Stage 2: Timers (`call_later`)

- **Goal:** `call_later(delay, callback)` — schedule work for the future using a deadline min-heap; the loop sleeps *just enough* to reach the next deadline without burning CPU, and fires expired timers in deadline order.
- **Test:** `uv run pytest tests/test_timers.py` — timers fire in deadline order; total wall time ≈ max delay, not the sum (proving non-blocking interleaving).
- **Focus:** Concurrency (timers as first-class events), loop design (where does the loop block?).


### Prerequisites

- Stage 1 done: ready queue + `run_forever` work.
- Comfort with `heapq` (min-heap over tuples).

### Concepts to learn first

- **Timers are events too:** a delayed callback is just work whose *condition* is "wall clock passed the deadline". The loop's job is to find expired deadlines each tick and promote them to the ready queue.
- **Why a heap, not a sorted list:** O(log n) insert, O(1) peek of the next deadline; timers are created at arbitrary times.
- **`time.monotonic()` vs `time.time()`:** wall-clock time can jump (NTP, DST); monotonic never goes backwards. Deadlines must be monotonic or a clock adjustment could starve or fast-fire timers.
- **Blocking budget:** this is the first time the loop has a choice about *how long to wait* when the ready queue is empty. That computed timeout becomes the seed of Stage 4's `select(timeout)`.

### Interfaces

- `call_later(delay, callback, *args)` — schedule a callback for a future deadline.
- Internal helpers to design: how expired timers are promoted to the ready queue, and how the loop computes how long it may block.

### Edge cases & pitfalls

- **Comparing unorderable entries:** if two timers share a deadline, Python compares the next tuple element — a raw `callback` object raises `TypeError`. Always include the monotonic integer sequence tiebreaker.
- **Busy spinning:** without the sleep-until-deadline step, an empty ready queue + pending timer = 100% CPU hot loop. Assert in your test that CPU time stays low if you want to be strict.
- **Zero/negative delay:** `call_later(0, ...)` should behave like `call_soon` (fires on the next tick, not synchronously). Clamp negatives to 0.
- **Timer cancellation** (lookahead): you don't need it yet, but note that cancellation will need a "cancelled" flag checked at pop time — heaps can't delete arbitrary entries cheaply.
- **Timing precision in tests:** OS scheduler jitter means `sleep(0.05)` can take 60ms. Assert deadlines are met with tolerance (`elapsed >= delay`) and ordering, but use generous upper bounds (`elapsed < delay + 0.5`).

### Hints

- Compare your deadline-promotion approach against the TechTalk Scheduler article's `sleeping` list.
- What value will later be handed to `selector.select()` instead of `time.sleep()`, and how does naming it now simplify Stage 4?
- How would you show that a timer at +50 ms ran *between* two timer-backed closures at +100 ms?

### References

- [Build your own Event Loop in Python](https://techtalk.digitalpress.blog/build-your-own-event-loop-in-python/) — `call_later` + heap + promote pattern
- [Beginner's Tutorial: Building a Custom asyncio Event Loop](https://geekyhumans.com/beginners-tutorial-building-a-custom-asyncio-event-loop-in-python/) — MiniLoop with `_scheduled` heap
- `time.monotonic` docs: [PEP 418](https://peps.python.org/pep-0418/)

### Done when

- [ ] `uv run pytest tests/test_timers.py` passes: deadline order, wall-time ≈ max delay, `call_later(0, ...)` fires next tick.
- [ ] Loop exits when ready queue and timers are both empty.
- [ ] No hot spin: loop with a pending 100ms timer doesn't consume meaningful CPU while waiting.


## Stage 3: Readiness polling with `selectors`

- **Goal:** The loop learns to wait on the OS: `add_reader(fd, callback)` / `add_writer(fd, callback)` backed by `selectors.DefaultSelector`, so a blocked loop wakes the instant a file descriptor is ready instead of polling.
- **Test:** `uv run pytest tests/test_selectors.py` — write to one end of an `os.pipe()`, assert the reader callback registered on the other end fires with the right bytes.
- **Focus:** Operating Systems (I/O multiplexing: `select`/`poll`/`epoll`/`kqueue`, file descriptors), Networking (non-blocking I/O).


### Prerequisites

- Stage 2 done: ready queue + timer heap work; the loop computes a "how long may I block" timeout.
- Basic idea of a file descriptor: an int handle for pipes, sockets, files. Reads on an empty pipe block — unless you ask the OS "which fds are ready?" first.

### Concepts to learn first

- **Readiness vs completion:** Unix I/O multiplexing tells you a fd is *ready* (a `recv` won't block), it doesn't do the I/O for you. Your callback still does the `os.read`. (Contrast with Windows IOCP / io_uring completion models.) See the selectors docs in References.
- **`selectors.DefaultSelector`:** stdlib wrapper that picks the best backend — `epoll` on Linux, `kqueue` on macOS, `select` fallback. Same API everywhere: `register(fd, EVENT_READ|EVENT_WRITE, data)`, `select(timeout)` → `[(key, mask)]`, `unregister(fd)`.
- **Why `data=callback`:** the selector stores an opaque payload per fd; storing the callback makes dispatch trivial: `key.data(key.fileobj, mask)`.

### Interfaces

- `add_reader(fd, callback, *args)` / `add_writer(fd, callback, *args)`
- `remove_reader(fd)` / `remove_writer(fd)`

### Edge cases & pitfalls

- **A fd registered twice:** `register` raises `KeyError`. Decide: `add_reader` on an already-watched fd replaces, ignores, or raises — asyncio raises unless you remove first. Test your choice.
- **Selector with zero fds + `timeout=None`:** blocks forever. Your loop-exit condition must now be "no ready AND no timers AND no registered fds" — or tests hang. Add a safety timeout in tests.
- **Level-triggered semantics:** `epoll` default is level-triggered: a fd stays "ready" until drained. If your callback doesn't read all data, you'll get woken every tick — fine for now, but don't busy-spin on it (Stage 4's timeout=0-when-ready rule matters here).
- **Fds are ints, callbacks hold refs:** closing an fd without `unregister` leaks the selector registration and can recycle the fd number onto a new socket — always pair `close` with `remove_*` (Stage 11 will punish you otherwise).

### Hints

- Why start with `os.pipe()` rather than sockets?
- Should I/O readiness run inline or enqueue into the same ready path as everything else? What does a single execution path buy for exception handling?
- How does CPython's `base_events.py` store the callback in the selector's `data`?

### References

- [Python `selectors` docs](https://docs.python.org/3/library/selectors.html)
- [Build your own Event Loop in Python](https://techtalk.digitalpress.blog/build-your-own-event-loop-in-python/) — `select()`-based scheduler
- [Demystifying AsyncIO slides](https://slides.com/art049/demystifying-asyncio) — fd table → selector → dispatch trace
- [Single-threaded non-blocking server with selectors/epoll](https://prodsens.live/2025/05/12/building-your-own-web-server-part-4-single-threaded-non-blocking-server/)

### Done when

- [ ] `uv run pytest tests/test_selectors.py` passes: pipe write → reader fires with correct bytes; `remove_reader` stops callbacks.
- [ ] Loop with zero fds + zero timers + empty ready queue exits instead of blocking forever.
- [ ] Reader/writer on the same fd coexist (read mask + write mask both dispatch).


## Stage 4: The complete loop tick

- **Goal:** Formalize the tick as `_run_once()` — one method that blends ready callbacks, timer deadlines, and selector waits exactly like asyncio's — so every later feature rides a single correct scheduling core.
- **Test:** `uv run pytest tests/test_run_once.py` — mixed workload: a pipe reader plus a 50 ms timer both fire inside one `run_forever()`; loop exits cleanly when all sources drain.
- **Focus:** OS I/O multiplexing (timeout computation), event-driven concurrency (fair scheduling order).


### Prerequisites

- Stage 3 done: selector registered, rough tick works for the pipe test.

### Concepts to learn first

- **The `_run_once` algorithm** (CPython `base_events.py`): (1) compute timeout, (2) `select(timeout)`, (3) move I/O callbacks to ready, (4) move expired timers to ready, (5) run ready callbacks (bounded per tick in asyncio via `_ntodo` — you can drain fully for now). Order matters; learn it from the References link, not from memory.
- **Timeout selection rule:** ready work pending → timeout 0 (never block with work queued); else time-to-next-timer; else `None` (block until I/O) — but only if fds are registered, otherwise exit.
- **Fairness:** I/O callbacks and timers both funnel through `_ready`, so a flood of ready fds can't starve timers forever — they interleave tick by tick.

### Interfaces

- `_run_once()` — one scheduling tick. Design its phases yourself: compute timeout, wait, promote I/O and timers, run ready callbacks.
- `_compute_timeout()` — returns `0`, a delay, or `None` to mean "block until I/O".

### Edge cases & pitfalls

- **Unbounded drain starvation:** draining the whole deque without the `ntodo` snapshot lets a chatty callback starve timers/I/O. asyncio caps per-tick work; copy that.
- **`select` interrupted by signals:** catches `InterruptedError` and treats as empty events (retry next tick).
- **Timeout drift:** recompute `now` after `select` returns — the wait itself took time; timers that expired *during* the block must fire this tick.
- **Empty-selector `select(None)`:** hangs forever — the exit condition in `run_forever` must be checked *before* calling `_run_once`, never inside the blocking call.

### Hints

- Line your `_run_once` up against asyncio's and compare the phase order; which orderings change deadline precision?
- What should `_compute_timeout()` return with pending ready work, with only a 100 ms timer, with only fds?
- Where is your single exception-handling choke point, and why does that keep `_run_once` clean?

### References

- CPython `Lib/asyncio/base_events.py` — `BaseEventLoop._run_once` (the canonical implementation)
- [Build your own Event Loop in Python](https://techtalk.digitalpress.blog/build-your-own-event-loop-in-python/) — `run()` mixing ready/sleeping/select
- [Beginner's Tutorial: MiniLoop](https://geekyhumans.com/beginners-tutorial-building-a-custom-asyncio-event-loop-in-python/) — ready vs scheduled separation
- [Redis `ae.c`](https://github.com/redis/redis/blob/unstable/src/ae.c) — a compact production `run_once`: ready queue + timer heap + `poll` (see Similar Projects)
- [libuv `src/unix/core.c`](https://github.com/libuv/libuv/blob/v1.x/src/unix/core.c) — `uv_run` lifecycle and loop phases (see Similar Projects)

### Done when

- [ ] `uv run pytest tests/test_run_once.py` passes: mixed timer + I/O workload completes; loop exits when all sources drain.
- [ ] `_compute_timeout` unit tests: 0 with pending ready work, ≈delay with only timers, None with only fds.
- [ ] A self-rescheduling `call_soon` callback doesn't starve a 10 ms timer (bounded per-tick drain).


## Stage 5: Generators as coroutines

- **Goal:** Drive generator objects as tasks: `next(task)` runs until `yield` (suspend) or `StopIteration` (done) — proving a bare `yield` is a pause-button the loop can interleave across tasks.
- **Test:** `uv run pytest tests/test_generators.py` — two generator tasks interleave output; wall time ≈ max sleep, not the sum.
- **Focus:** Concurrency (cooperative multitasking), Language Design (how pausing/resuming works under the hood).


### Prerequisites

- Stage 4 done: solid `_run_once`; callbacks run reliably.
- Python generators: `yield` suspends, `next()`/`send()` resumes.

### Concepts to learn first

- **Generator = pausable frame:** calling a generator function doesn't run it — it returns a frame object holding locals + instruction pointer. `next()` runs to the next `yield`, then control returns to the caller (the loop). The loop is the *resumer*. See the CodingPancake guide's "Mechanics of Yield" section.
- **Cooperative multitasking:** unlike threads, *the task decides* when to yield. No locks needed, but a task that never yields freezes the loop — the fundamental tradeoff of the whole project.
- **`StopIteration` as return channel:** a `return value` inside a generator raises `StopIteration(value)`. The loop catches it to learn the task's result. This is load-bearing for Stage 6.

### Interfaces

- `sleep_gen(seconds)` — a generator that yields until its deadline passes.
- Task stepping is a design choice: how a generator is driven to its next suspension, and how completion is detected.

### Edge cases & pitfalls

- **Busy-spin by construction:** requeue-on-yield with no waiting means the loop spins at 100% CPU. That's *expected* here — it's the motivation for timer-backed Futures next. Don't "fix" it with `time.sleep` inside the loop; that would serialize everything.
- **Forgetting `StopIteration`:** if you requeue unconditionally, finished tasks spin forever yielding nothing. The `except StopIteration: don't reschedule` branch is the whole completion protocol.
- **`yield` vs `yield from`:** a bare `yield` suspends one frame; `yield from sub()` delegates so the *inner* generator's yields reach the loop. Mixing them up breaks suspension depth.
- **Exceptions inside tasks:** an uncaught exception in a generator propagates out of `next()` — catch it in `_step`, record it, don't reschedule. (Stage 12 builds the full propagation story.)

### Hints

- What is the minimal state a driven generator needs, and why is that the whole model?
- Why resist introducing a `Task` class before Futures exist?
- Which timestamp trace would convince you two tasks truly interleaved?

### References

- [Build a working asyncio event loop in 30 lines](https://dev.to/ritesh_fcb86fb4b3890c81e4/build-a-working-asyncio-event-loop-in-30-lines-of-plain-python-5gjb) — the exact toy loop shape
- [How Python Asyncio Works: Recreating it from Scratch](https://jacobpadilla.com/writing/recreating-asyncio) — event loop as task list + `next(task)`
- [Asyncio from scratch (bolu.dev)](http://bolu.dev/python/programming/2024/05/23/asyncio-from-scratch.html) — cooperative multitasking with generators section

### Done when

- [ ] `uv run pytest tests/test_generators.py` passes: interleaved execution order, wall time ≈ max sleep.
- [ ] Finished generators are never requeued (no infinite spin after completion).
- [ ] `yield from` composition works: task → `sleep_gen` → loop yields propagate.


## Stage 6: `yield from` delegation

- **Goal:** Make nested generator calls work properly: `result = yield from sub()` passes sends/throws both directions and delivers the sub-generator's return value — the exact semantics `await` will later reuse.
- **Test:** `uv run pytest tests/test_delegation.py` — a delegating generator awaits an inner sleep, receives its return value, and propagates an inner exception outward.
- **Focus:** Language Design (`yield from` / PEP 380 as the desugaring of `await`), exception flow through coroutine chains.


### Prerequisites

- Stage 5 done: single-level generators suspend/resume; `StopIteration.value` carries return values.

### Concepts to learn first

- **`yield from` is bidirectional plumbing:** values yielded by the sub-generator go straight to the loop; values sent *in* via `send()` go straight down to the sub-generator; `throw()` propagates down; the sub-generator's `return X` surfaces as the *value of the `yield from` expression*. It's not syntax sugar for a loop — it's a transparent channel. Read PEP 380's expansion in References.
- **Why this matters for `await`:** `await x` is defined as `yield from x.__await__()`. Nailing delegation now means Stage 8's native coroutines work for free.
- **The delegation chain:** outer task → middle `yield from` → inner sleep. The loop only ever sees the *innermost* yields. Every frame in between is transparent.

### Edge cases & pitfalls

- **Swallowing exceptions mid-chain:** a `try/except` around `yield from` that catches everything and doesn't re-raise leaves the outer task suspended forever once Futures arrive (Stage 7) — establish the "always propagate or resolve" discipline now.
- **`return` with a value inside a generator being driven by bare `next()`:** works fine (`StopIteration.value`), but code that catches `StopIteration` and ignores `.value` silently drops results — check your stepper preserves it.
- **Sending non-None into a just-started generator:** `gen.send(x)` before first `next()` raises `TypeError`. Your stepper always resumes with `next()`/`send(None)` — remember this rule for Stage 7's `Task.send(result)`.
- **Confusing `yield` with `yield from` in task bodies:** `yield sleep_gen(1)` yields the *generator object itself* to the loop (junk); `yield from sleep_gen(1)` delegates. A classic typo — the Stage 5 tests catch it as a hang.

### Hints

- How does PEP 380's expansion explain `send`/`throw` passthrough?
- Which parts of delegation are automatic with `yield from` versus manual with a yield loop?
- If the loop ever receives a raw generator object, which mistake produced it?

### References

- [PEP 380 — Syntax for Delegating to a Subgenerator](https://peps.python.org/pep-0380/)
- [Custom Event Loop guide — Delegating Generators section](https://www.codingpancake.com/2026/07/how-to-implement-custom-event-loop-in.html)
- [Asyncio Demystified](https://dev.indooroutdoor.io/asyncio-demystified-rebuilding-it-from-scratch-one-yield-at-a-time) — `yield from` as await's ancestor

### Done when

- [ ] `uv run pytest tests/test_delegation.py` passes: return-value delivery through 1 and 3 nesting levels; exception propagation out of a nested chain.
- [ ] The Stage 5 stepper is unchanged — nesting is transparent to the loop.
- [ ] No test hangs from a `yield`-vs-`yield from` typo (all inner yields reach the loop).


## Stage 7: Futures and Tasks

- **Goal:** The executor core: a `Future` (a value that isn't ready yet) plus a `Task` (a coroutine driver) so tasks *sleep without spinning* — yielding a Future suspends the task until something resolves it, ending Stage 5's busy-loop.
- **Test:** `uv run pytest tests/test_futures.py` — task yields a Future, a timer resolves it, task resumes with the result value; `sleep()` built on timers interleaves two tasks with ~zero CPU spin.
- **Focus:** Concurrency (cooperative multitasking without polling), OS timers as wake-up sources.


### Prerequisites

- Stage 5–6 done: generators suspend via `yield`; `yield from` delegates; `StopIteration.value` carries results.

### Concepts to learn first

- **Future = promise of a value:** `Future` holds `_result`, `_done`, and a callback list. `set_result()` flips done and fires callbacks. `add_done_callback(fn)` runs `fn` immediately if already done, else queues it. (TypeScript Promise analogy is exact.)
- **The suspend/resume protocol:** task runs `coro.send(None)`; if the coroutine yields a `Future`, the Task registers a re-wake callback on it and *stops stepping*. When the Future resolves, the callback does `coro.send(future.result)` — execution continues after the `yield` with the value. The loop never polls the task in between.
- **`Future.__await__`:** defined as `return (yield self)` — yielding *oneself* to the driver. This single line is the entire bridge to `await` in Stage 8.
- **Who resolves timer Futures:** `loop.call_later(deadline, future.set_result, value)` — the timer heap from Stage 2 becomes the wake-up mechanism. No spinning.

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

`sleep` returns an awaitable `Future`; it is not itself a coroutine. Decide how the loop's exit condition accounts for pending Futures.

### Edge cases & pitfalls

- **The lost-task trap:** a Task nobody holds a reference to can be GC'd mid-flight; worse, its exception dies silently. Keep a strong-ref set (`loop._tasks`) until completion, and log unretrieved exceptions (asyncio's "exception was never retrieved" warning).
- **Yielding a non-Future:** decide loudly (raise `RuntimeError`) rather than silently requeueing — silent acceptance masks `yield`-vs-`yield from` typos from Stage 6.
- **`set_result` twice:** second call should raise (`InvalidStateError` in asyncio) — a double-resolving timer indicates a logic bug.
- **Callback reentrancy:** `set_result` runs callbacks synchronously; a callback that resolves another Future recurses. Fine at this scale, but be aware the stack grows with chain length.
- **Blocking inside `result()`:** never block waiting — `result()` on an unfinished Future raises. Waiting happens *only* via `yield`/`await`.

### Hints

- How does the indooroutdoor.io build replace a parked task in the queue with the Future it yielded, and reschedule on resolution?
- How would you prove the loop is no longer spinning while a task sleeps?
- Should `Future` know about the loop at all? What does keeping it loop-agnostic buy in Stage 10?

### References

- [Asyncio Demystified — Future & Scheduler](https://dev.indooroutdoor.io/asyncio-demystified-rebuilding-it-from-scratch-one-yield-at-a-time)
- [How Python Asyncio Works — Task + `__await__`](https://jacobpadilla.com/writing/recreating-asyncio)
- [asyncio runtime from scratch — Task wrapper](http://bolu.dev/python/programming/2024/05/23/asyncio-from-scratch.html)
- CPython `Lib/asyncio/futures.py` + `tasks.py` (`Task.__step`)

### Done when

- [ ] `uv run pytest tests/test_futures.py` passes: yield-Future → timer-resolve → resume-with-value; exception stored and raised on `.result()`.
- [ ] `sleep()`-based interleaving test: two tasks, wall ≈ max delay, no busy spin.
- [ ] Yielding a non-Future raises loudly; double `set_result` raises.


## Stage 8: Native coroutines

- **Goal:** Prove `async def` / `await` run on your loop *unchanged* — same `Task`, same `Future`, same tick — because the keywords are just syntax over the generator protocol you already built.
- **Test:** `uv run pytest tests/test_native_coros.py` — the Stage 7 scenarios rewritten with `async def` mains; identical assertions pass unmodified.
- **Focus:** Language Design (how `async`/`await` desugar), executor interop via `__await__`.


### Prerequisites

- Stage 7 done: `Future.__await__` exists, `Task._step` drives via `send()`, timer-backed `sleep` works.

### Concepts to learn first

- **`async def` changes the type, not the machinery:** calling an `async def` function returns a coroutine object — pausable/resumable like a generator, but *not* a generator (no `next()`; must use `send(None)`/`throw`). Your `Task._step` already uses `send`, so it works as-is.
- **`await x` ≈ `yield from x.__await__()`:** for a Future, `__await__` yields the Future itself to the driver — the identical object your Stage 7 code yielded manually. For a coroutine, `__await__` chains into the sub-coroutine. Read PEP 492 alongside PEP 380.
- **First-send rule:** a coroutine must be started with `send(None)`; sending a real value first raises `TypeError`. `Task._step` already honors this (first call passes `None`).

### Interfaces

- `run_until_complete(awaitable)` — drive an awaitable to completion, return its result or raise its exception.
- `sleep` stays a plain function returning a `Future`; it is already awaitable.

### Edge cases & pitfalls

- **`await` on a bare generator fails:** native coroutines require awaitables (`__await__`) or coroutines. A test accidentally awaiting a generator function raises `TypeError` — good, that's the type discipline `async` buys you over Stage 5's free-for-all.
- **Mixing `yield` and `await`:** `yield` inside `async def` makes it an *async generator* — a different protocol your loop doesn't support. Lint for it: any `yield` in an `async def` body is a bug at this stage.
- **`coro.send` vs `gen.send`:** identical API, but coroutine frames can't be introspected like generators — debug prints of "current yield" stop working; rely on Task-level logging instead.
- **`run_until_complete` reentrancy:** calling it from inside a running loop (nested) must raise — guard with the `_running` flag from Stage 1.

### Hints

- Compare your change against the jacobpadilla refactor section — how small is the diff really?
- If only syntax changed, what does that say about `async`/`await`?
- Why keep one generator-based test around after the rewrite?

### References

- [PEP 492 — Coroutines with async and await](https://peps.python.org/pep-0492/)
- [How Python Asyncio Works — await refactor](https://jacobpadilla.com/writing/recreating-asyncio)
- [Asyncio Demystified — await section](https://dev.indooroutdoor.io/asyncio-demystified-rebuilding-it-from-scratch-one-yield-at-a-time) ("`async` and `await` do no magic whatsoever")
- [asyncio runtime from scratch — syntactic sugar section](http://bolu.dev/python/programming/2024/05/23/asyncio-from-scratch.html)

### Done when

- [ ] `uv run pytest tests/test_native_coros.py` passes: same interleaving/result/exception assertions as Stage 7, now in `async def` syntax.
- [ ] `run_until_complete` drives a main coroutine to a return value and propagates its exception.
- [ ] Generator-based Stage 5 tests still pass untouched (protocol equivalence proven).


## Stage 9: `gather`

- **Goal:** `gather(*awaitables)` — await many children concurrently, collecting ordered results in ~max delay instead of the sum.
- **Test:** `uv run pytest tests/test_gather.py` — three sleeps (50/100/150 ms) complete in ≈150 ms with results in argument order; one child's exception surfaces correctly.
- **Focus:** Concurrency (fan-out/fan-in coordination), Future composition.


### Prerequisites

- Stage 8 done: native coroutines, `run_until_complete`, `create_task` all work.

### Concepts to learn first

- **Fan-out/fan-in:** `gather` wraps each child in a Task (fan-out), attaches a completion callback to each, counts down, and resolves a single parent Future with the ordered result list (fan-in). The parent is just another Future — awaitable, composable, nestable.
- **Result ordering vs completion ordering:** results land in *argument* order regardless of finish order — requires pre-allocated slots + index capture per child.
- **Failure semantics (a design decision):** asyncio's default cancels siblings on first exception; a simpler valid choice is "record the first exception, still await the rest" or "fail fast, leave siblings running". Pick one, document it, test it — Stage 12 revisits with cancellation.

### Interfaces

- `gather(*awaitables) -> Future` — resolves with results in argument order; empty `gather()` resolves immediately with `[]`.

### Edge cases & pitfalls

- **Late-binding closure bug:** `lambda c: _child_done(i, c)` in a loop captures the *variable* `i` — all callbacks see the last index. Bind with a default arg (`i=i`) or `functools.partial`.
- **Children finishing before callbacks attach:** `add_done_callback` fires immediately for done Futures (Stage 7 contract) — so this is safe, but only because you implemented that rule. Test gather with already-done children.
- **Exception double-count:** after the parent resolves with an exception, later children completing must be ignored (`if parent.done(): return`) or they'd `set_result` twice → raise.
- **Nesting:** `gather(gather(a, b), c)` should work — parent Futures are awaitables like any other. Add a nesting test; it exercises the protocol generically.

### Hints

- Where else does the countdown-latch pattern (counter + indexed slots) recur, and why is it general?
- Should `gather` need the loop at all, or only child creation? How does that affect Stage 13?
- What failure semantics will you choose, and why must that decision come before the tests?

### References

- CPython `Lib/asyncio/tasks.py` — `gather` (read the `_done_callback` closure for the canonical latch)
- [Asyncio Demystified](https://dev.indooroutdoor.io/asyncio-demystified-rebuilding-it-from-scratch-one-yield-at-a-time) — waiting on multiple futures

### Done when

- [ ] `uv run pytest tests/test_gather.py` passes: ordered results, wall ≈ max delay, empty gather, nested gather.
- [ ] Failure semantics documented in the docstring and covered by a test.
- [ ] No closure index bug (results land in argument order even when children finish out of order).


## Stage 10: Async socket I/O primitives

- **Goal:** Awaitable socket operations — `sock_recv`, `sock_sendall`, `sock_accept` — built as Futures resolved from selector callbacks, replacing timer-polling with true OS readiness waits.
- **Test:** `uv run pytest tests/test_sock_io.py` — async client/server over `socket.socketpair()`; client sends, server echoes, both sides assert exact bytes.
- **Focus:** Networking (non-blocking I/O), OS readiness as Future resolution source.


### Prerequisites

- Stage 7 done: Future/Task protocol solid. Stage 3–4 done: selector + `_run_once` reliable.

### Concepts to learn first

- **Non-blocking sockets:** `sock.setblocking(False)` makes `recv` raise `BlockingIOError` instead of waiting. The correct pattern: try the op; on `BlockingIOError`, register the fd with the selector and suspend; on readiness, retry. Never call a blocking socket method on the loop thread.
- **One-shot selector registration:** each await registers a fresh reader/writer callback that unregisters itself on first firing — unlike Stage 3's persistent pipe reader. This prevents stale callbacks firing for the *next* await on the same fd.
- **Partial sends / empty recvs:** `send` may write fewer bytes than given (loop until all sent); `recv` returning `b""` means orderly shutdown (resolve with `b""`, don't re-register — that's Stage 11's close path).

### Interfaces

- `sock_recv(loop, sock, n) -> bytes`
- `sock_sendall(loop, sock, data) -> None`
- `sock_accept(loop, listener) -> (conn, addr)`

(Functions or loop methods — pick one style and stay consistent.)

### Edge cases & pitfalls

- **Forgetting `setblocking(False)`:** one blocking `recv` on the loop thread freezes *everything* — timers, other clients, all of it. Assert non-blocking in the primitives (`sock.getblocking()` check or set it yourself).
- **Spurious wakeups:** readiness doesn't guarantee the op succeeds — always `try/except BlockingIOError` and stay registered on failure, or you'll drop the await silently.
- **Fd reuse after close:** unregister *before* resolving the Future — the awaiting task may immediately close the socket, and a stale registration could fire for a recycled fd number.
- **`BlockingIOError` vs `ssl.SSLWantRead`:** plain sockets only here; note TLS as out-of-scope (its want-read/write dance is a whole stage by itself — skip it).
- **Test flakiness:** loopback TCP is fast but not instant; the primitives must not assume data arrives in one segment — `sock_recv` returns *up to* `n` bytes, tests should frame accordingly (length prefix or fixed-size echo).

### Hints

- Why mirror asyncio's `sock_*` signatures exactly? What does Stage 13 gain?
- Functions plus one-shot callbacks vs Future subclasses (the indooroutdoor.io style) — which fits your design, and why?
- If the TCP test hangs, which setup mistake would it resemble?

### References

- [Asyncio Demystified — AcceptSocket/ReadSocket + selectors](https://dev.indooroutdoor.io/asyncio-demystified-rebuilding-it-from-scratch-one-yield-at-a-time)
- [Build your own Event Loop — non-blocking sockets](https://techtalk.digitalpress.blog/build-your-own-event-loop-in-python/)
- Python [`socket`](https://docs.python.org/3/library/socket.html) docs — blocking flag, `socketpair`
- CPython `Lib/asyncio/selector_events.py` — `_sock_recv`, `_sock_sendall` reference implementations

### Done when

- [ ] `uv run pytest tests/test_sock_io.py` passes: socketpair echo + loopback TCP echo with exact-byte assertions.
- [ ] No primitive ever blocks the loop (a concurrent timer fires on schedule during a pending `sock_recv`).
- [ ] Spurious-wakeup and partial-send paths covered by tests (e.g. large payload > socket buffer).


## Stage 11: Echo server end-to-end

- **Goal:** A concurrent TCP echo server running purely on your loop — one `handle_client` task per connection, N simultaneous clients each getting their own bytes back, all on a single thread.
- **Test:** `uv run pytest tests/test_echo_server.py` — spin up the server, open N concurrent blocking clients (threads) with distinct payloads, assert every client receives its own payload; completes far faster than a serial server would.
- **Focus:** Networking (concurrent servers without threads), resource lifecycle (fd registration/cleanup at scale).


### Prerequisites

- Stage 10 done: `sock_recv` / `sock_sendall` / `sock_accept` all work and are covered by tests.

### Concepts to learn first

- **The accept loop:** `while True: conn, addr = await sock_accept(listener); loop.create_task(handle(conn))` — accepting never blocks handling, handling never blocks accepting. This two-line pattern *is* every asyncio server.
- **Per-connection tasks:** each client gets an independent coroutine; interleaving happens at `await` points (waiting for data). No threads, no locks, no shared state beyond the listener.
- **Backpressure intuition:** a slow client only suspends its own task (parked on a selector registration), never the server. Contrast with thread-per-connection memory cost — that's the scalability argument for the whole project.

### Interfaces

- `serve_forever(loop, listener)` — accept loop that spawns a task per connection.
- `handle_client(loop, conn)` — per-connection echo until orderly shutdown.

### Edge cases & pitfalls

- **Fd leaks:** every accepted socket must be unregistered *and* closed on every exit path (client disconnect, exception, test teardown). Leaked fds eventually hit `EMFILE` and the selector keeps firing on dead sockets. The `finally` block is non-negotiable.
- **`recv` → `b""`:** means the client closed — `break`, don't re-register. Re-registering on a closed socket spins the loop forever.
- **Listener setup:** `SO_REUSEADDR`, `bind`, `listen(backlog>=100)`, `setblocking(False)` — missing any one gives "address in use" / blocking-accept / refused-connection failures that look like loop bugs.
- **Test teardown:** stop the loop, close the listener, join the server thread with a timeout. A test that leaves a thread bound to a port poisons every later run. Use fixtures with `yield` + cleanup.
- **Half-close / abrupt RST:** `ConnectionResetError` from `recv` on a killed client — catch, treat like disconnect. Test it by having one client `close()` without `shutdown()` mid-stream.

### Hints

- Why start with a handful of clients before scaling to 50+? What do the two failure scales tell you apart?
- How will you tell a clean run from an fd leak?
- At what connection count would you be convinced the reactor is real?

### References

- [Single-threaded non-blocking server](https://prodsens.live/2025/05/12/building-your-own-web-server-part-4-single-threaded-non-blocking-server/) — accept/register/service structure
- [Asyncio Demystified — echo server finale](https://dev.indooroutdoor.io/asyncio-demystified-rebuilding-it-from-scratch-one-yield-at-a-time)
- [Build your own Event Loop — TCP server + countdown demo](https://techtalk.digitalpress.blog/build-your-own-event-loop-in-python/)

### Done when

- [ ] `uv run pytest tests/test_echo_server.py` passes: N concurrent distinct-payload echoes, slow-client-doesn't-block-fast-clients, connection counter returns to 0.
- [ ] No fd leaks: fd count stable across repeated runs; `RST`-killing a client doesn't wedge the server.
- [ ] Wall time proves concurrency (≈ single-client time, not N×).


## Stage 12: Cancellation & exception propagation

- **Goal:** Tasks that can be cancelled mid-await (`task.cancel()` → `CancelledError` at the suspension point) and exceptions that propagate faithfully through `await` chains to `task.result()` — without ever wedging the loop.
- **Test:** `uv run pytest tests/test_cancellation.py` — cancel a sleeping task mid-flight and assert `CancelledError`; raise inside a 3-deep coroutine chain and assert the exact exception surfaces at the awaiting task.
- **Focus:** Concurrency (cancellation as a first-class operation), Language Design (exception flow through coroutine frames).


### Prerequisites

- Stage 7–8 done: `Task._step` drives via `send()`; exceptions are stored in the Future and re-raised on `.result()`.
- Stage 6 done: `yield from`/`await` chains propagate `throw()` down the frame stack (re-read that section — cancellation *is* `throw`).

### Concepts to learn first

- **Cancellation = `throw()` at the suspension point:** `task.cancel()` injects `CancelledError` into the coroutine exactly where it's parked (`coro.throw(CancelledError)` instead of `coro.send(...)`). The coroutine may catch it (cleanup) and either re-raise (cancelled) or return a value (cancellation suppressed — asyncio allows this deliberately).
- **`CancelledError` vs regular exceptions:** it inherits from `BaseException` (like `KeyboardInterrupt`), not `Exception` — so bare `except Exception` doesn't swallow it. Your `Task._step` must catch `BaseException` separately from `StopIteration` and record cancellation state distinctly from failure.
- **Propagation rule:** an exception in a child Task must reach whoever awaits it *and* mark the child done — never leave an awaiter parked on a Future that will never resolve. A wedged awaiter is the signature bug of hand-rolled executors.

### Interfaces

- `Task.cancel() -> bool`
- `Task.cancelled() -> bool`
- `Task.exception()` / `Task.result()` state semantics (value vs exception vs cancelled).
- Optional: `shield(fut)` — document whether you implement it or defer.

### Edge cases & pitfalls

- **Swallowed `CancelledError`:** `except Exception: pass` in user code *won't* catch it (BaseException) — but `except BaseException: pass` will, converting a cancel into a hang unless re-raised. Document this; test that a suppressing coroutine completes normally (that's legal, not a bug).
- **Cancelling a done task:** must return `False` and do nothing — throwing into a finished coroutine raises `RuntimeError`/`StopIteration` weirdness.
- **Double-resolve after cancel:** the original Future the task was parked on may *later* resolve and fire `_step` — guard with `if self.done(): return` at the top of both step paths.
- **Unretrieved-cancelled warnings:** like Stage 7's lost-exception trap, a cancelled task nobody inspects should log — otherwise cancellations vanish silently in production.
- **Loop liveness:** cancelling the *last* pending task must still let `run_forever` exit (no orphaned timer/fd registrations keeping the loop alive).

### Hints

- How does CPython model the pending → cancelling → cancelled/finished state machine?
- Which cancellation timings hit distinct branches (before first step, mid-sleep, already done, twice)?
- Why does any error state that fails to reach the root Task frame become a permanent suspension?

### References

- CPython `Lib/asyncio/tasks.py` — `Task.cancel`, `Task.cancelled`, `Task.__step`
- [PEP 492](https://peps.python.org/pep-0492/) — `CancelledError` semantics
- [Custom Event Loop guide — exception propagation pitfalls](https://www.codingpancake.com/2026/07/how-to-implement-custom-event-loop-in.html)
- Python [`coroutine.throw`](https://docs.python.org/3/reference/expressions.html#await-expression) docs
- [Trio `_core/_run.py`](https://github.com/python-trio/trio/blob/main/src/trio/_core/_run.py) — cancellation scopes / nurseries, a stricter model than bare `task.cancel()` (see Similar Projects)
- [Curio `kernel.py`](https://github.com/dabeaz/curio/blob/master/curio/kernel.py) — explicit, `await`-driven cancellation and traps in a small kernel (see Similar Projects)

### Done when

- [ ] `uv run pytest tests/test_cancellation.py` passes: mid-sleep cancel → `CancelledError`; 3-deep raise propagates exactly; siblings unaffected; cancel-done-task returns False.
- [ ] Suppressed cancellation (catch + return value) completes the task normally — tested and documented.
- [ ] No wedged awaiters: every test's loop exits; no test needs a timeout-kill to finish.


## Stage 13: Drop-in asyncio comparison

- **Goal:** Prove behavioral parity: the same test suite runs green against *both* your loop and real `asyncio` through a thin adapter — and every known difference is written down, not lurking.
- **Test:** `uv run pytest tests/test_parity.py` — a parametrized fixture runs the echo + gather + cancellation scenarios against `MyEventLoop` and `asyncio.run` alike.
- **Focus:** API design (mirroring `asyncio`'s surface), verification methodology (differential testing).


### Prerequisites

- Stages 1–12 done: callbacks, timers, selector I/O, Futures/Tasks, native coroutines, gather, sockets, echo server, cancellation all work on your loop.

### Concepts to learn first

- **Differential testing:** same inputs, two implementations, same assertions. Differences found this way are either bugs in yours or documented gaps — both are wins. This is how you'd validate any reimplementation (compilers, runtimes, protocols).
- **The minimal `asyncio` surface you mirror:** `call_soon`, `call_later`, `add_reader`/`add_writer`/`remove_reader`, `create_task`, `sock_recv`/`sock_sendall`/`sock_accept`, `run_forever`/`run_until_complete`/`stop`. If your names already match (they should — Stages 1–10 followed asyncio naming), the adapter is ~20 lines.
- **`AbstractEventLoop` (optional, stretch):** subclassing `asyncio.AbstractEventLoop` and registering an event-loop policy makes your loop a literal `asyncio` backend. Powerful but fiddly; attempt only after the parametrized tests pass.

### Interfaces

- A `driver` abstraction both backends satisfy, exposing `run(coro)` plus `sleep` / `gather` / `sock_*`; one implementation for your loop, one for `asyncio`.
- A written list of known divergences, each with behavior, rationale, and planned/wontfix.

### Edge cases & pitfalls

- **Timing-sensitive assertions:** your loop and asyncio have different scheduling overhead — never assert exact interleavings or tight wall-time bounds in parity tests; assert orderings, result sets, and generous time windows.
- **Resource cleanup asymmetry:** asyncio closes transports on loop close; yours needs manual closes (Stage 11 discipline). Parity-test fixtures must clean up *both* backends' way or one side leaks ports/threads.
- **Cancellation semantic gaps:** this is where parity most likely breaks (Stage 9/12 documented choices). A red parity test here isn't failure — it's the differences doc writing itself. Capture, don't hide.
- **Threading in fixtures:** running your loop in a helper thread while asyncio runs inline is fine, but keep the driver's threading model identical across cases or you test the harness, not the loops.

### Hints

- Which scenario is easiest to start with, and how does it shake out fixture bugs before sockets/cancellation?
- When a parity test fails, how will you categorize it: missing feature, semantic difference, or timing flake?
- Which divergences are expected corner cases (signals, exception groups, `contextvars`, thread-safety)?

### References

- [Demystifying AsyncIO slides — hypercorn-on-custom-loop finale](https://slides.com/art049/demystifying-asyncio)
- CPython `Lib/asyncio/base_events.py` + `events.py` (`AbstractEventLoop` interface)
- [asyncio event loop docs](https://docs.python.org/3/library/asyncio-eventloop.html) — the API surface checklist

### Done when

- [ ] `uv run pytest tests/test_parity.py` passes on both backends for sleep, gather, echo, and cancellation scenarios.
- [ ] `DIFFERENCES.md` (or README section) documents every known divergence with behavior + rationale.
- [ ] Full suite green: `uv run pytest tests/` — all stages, one command, the project's acceptance gate.

## Acceptance

A single-threaded, epoll-backed event loop that schedules callbacks and timers, drives native `async def` coroutines through Futures/Tasks, serves hundreds of concurrent TCP connections, handles cancellation and exception propagation correctly — and passes the same test suite as real `asyncio`.
