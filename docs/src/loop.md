# Project: Event Loop / Async Runtime

Implement a single-threaded event loop (reactor) that monitors multiple I/O sources (e.g., network sockets, files) for readiness and dispatches user-defined callbacks or tasks when events occur. Optionally, build an "executor" on top to manage coroutines/futures, demonstrating cooperative multitasking.

- **Language:** Python (3.12, managed with `uv`)
- **Focus areas:** OS I/O multiplexing (`select`/`poll`/`epoll`/`kqueue`, file descriptors), non-blocking I/O, event-driven concurrency, cooperative multitasking, how `async/await` works under the hood
- **Build/test command:** `uv add --dev pytest` (Stage 0), then `uv run pytest tests/` and `uv run main.py`

## Milestone checkpoints

1. **Callback loop** — a runnable scheduler with `call_soon` / `call_later` (timers).
2. **I/O reactor** — readiness-based dispatch over file descriptors via `selectors`.
3. **Cooperative multitasking** — generators, `yield from`, Futures, Tasks.
4. **async/await executor** — native coroutines + `__await__` interop, `create_task`, `gather`.
5. **Beast mode** — non-blocking TCP echo server on your loop; cancellation, exception propagation, asyncio parity.


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

### Implementation logic

1. Add pytest as a dev dependency: `uv add --dev pytest`.
2. Create the package layout:
   ```
   loop/
     __init__.py      # exports EventLoop (placeholder for now)
   tests/
     test_smoke.py
   ```
3. `test_smoke.py` should do the minimum: `from loop import EventLoop` and assert a trivial property (e.g. `EventLoop()` constructs and has an empty ready queue).
4. Decide the module split you'll grow into (empty files are fine now):
   - `loop/loop.py` — the event loop itself (Stages 1–4)
   - `loop/futures.py` — Future/Task (Stage 7)
   - `loop/sock.py` — async socket primitives (Stage 10)
5. Run `uv run pytest` and confirm green.

### Edge cases & pitfalls

- Don't `pip install` anything — `uv` owns the environment; mixing tools corrupts `uv.lock`.
- Running `pytest` without `uv run` may pick the wrong interpreter (system 3.14 vs pinned 3.12) and behave subtly differently.
- Keep tests fast and hermetic: no network in early stages; use `os.pipe()` and `socket.socketpair()` which work entirely in-process.

### Hints

- Add a `conftest.py` in `tests/` early with a fixture that constructs a fresh `EventLoop` per test — you'll reuse it in every subsequent stage.
- Consider `uv run pytest -x --tb=short` as your default dev loop; later stages fail in ways that are easier to read with short tracebacks.
- This is also the stage to verify the whole command chain end-to-end: `uv run main.py` should still print its hello message.

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

### Implementation logic

1. `EventLoop.__init__`: `self._ready = deque()`, `self._running = False`, `self._stopping = False`.
2. `call_soon(callback, *args)`: append a `(callback, args)` tuple to `_ready`. Return a handle if you like (asyncio returns a `Handle`) — keep it minimal now.
3. `run_forever()`:
   ```
   self._running = True
   while not self._stopping and self._ready:
       cb, args = self._ready.popleft()
       cb(*args)
   self._running = False
   ```
4. `stop()`: set `_stopping = True` — takes effect on the next iteration check.
5. Test shape:
   ```python
   order = []
   loop = EventLoop()
   loop.call_soon(order.append, "a")
   loop.call_soon(order.append, "b")
   loop.run_forever()
   assert order == ["a", "b"]
   ```
6. Second test: a callback calling `loop.stop()` mid-queue — assert later-scheduled callbacks never run.

### Edge cases & pitfalls

- **Exceptions in callbacks:** wrap the `cb(*args)` call in `try/except`, collect the exception (log + store), and keep going. One bad callback must not kill the loop. (This becomes more structured in Stage 12.)
- **Reentrancy:** a callback that calls `call_soon` must be fine — it just appends to the same deque. But a callback calling `run_forever` again should be rejected (raise if `_running`).
- **`stop()` semantics:** decide whether callbacks scheduled before `stop()` but not yet run get dropped (asyncio drops them). Document your choice in a comment.
- Don't pop from the deque while iterating it — the `while self._ready: popleft()` pattern avoids this.

### Hints

- This is the exact shape of the "30-line asyncio" toy loops — a deque and a `while` (see the DEV Community reference). The magic later isn't in this loop; it's in what gets enqueued.
- Study asyncio's naming as you go: `call_soon`, `call_later`, `run_forever`, `stop` — mirroring the real API makes Stage 13 (parity) almost free.
- Skip a re-queue-himself-forever callback test for now (infinite loop) — that scenario only makes sense once timers/I/O let the loop block between work.

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

### Implementation logic

1. `EventLoop.__init__`: `self._timers = []` (heap of `(deadline, seq, callback, args)`).
2. `call_later(delay, callback, *args)`:
   ```python
   deadline = time.monotonic() + delay
   heapq.heappush(self._timers, (deadline, next(self._timer_seq), callback, args))
   ```
   The `seq` tiebreaker is essential — see pitfalls.
3. `_fire_expired_timers()`:
   ```python
   now = time.monotonic()
   while self._timers and self._timers[0][0] <= now:
       _, _, cb, args = heapq.heappop(self._timers)
       self.call_soon(cb, *args)
   ```
   Promote, don't run in place — timers go through the same ready-queue path as everything else.
4. Loop exit condition update: run while `self._ready or self._timers`.
5. Timeout computation (for now, with plain `time.sleep`):
   - If `_ready` is non-empty: timeout = 0 (no waiting).
   - Elif `_timers`: timeout = `max(0, next_deadline - now)`.
6. `run_forever` tick: fire expired timers → drain ready → if both empty, sleep until next deadline (or return if no timers either).

### Edge cases & pitfalls

- **Comparing unorderable entries:** if two timers share a deadline, Python compares the next tuple element — a raw `callback` object raises `TypeError`. Always include the monotonic integer sequence tiebreaker.
- **Busy spinning:** without the sleep-until-deadline step, an empty ready queue + pending timer = 100% CPU hot loop. Assert in your test that CPU time stays low if you want to be strict.
- **Zero/negative delay:** `call_later(0, ...)` should behave like `call_soon` (fires on the next tick, not synchronously). Clamp negatives to 0.
- **Timer cancellation** (lookahead): you don't need it yet, but note that cancellation will need a "cancelled" flag checked at pop time — heaps can't delete arbitrary entries cheaply.
- **Timing precision in tests:** OS scheduler jitter means `sleep(0.05)` can take 60ms. Assert deadlines are met with tolerance (`elapsed >= delay`) and ordering, but use generous upper bounds (`elapsed < delay + 0.5`).

### Hints

- The deadline-heap + promote-to-ready pattern is exactly what the TechTalk Scheduler article does with its `sleeping` list and `call_later`; steal its structure.
- Think of the "computed timeout" as a variable that will later be passed to `selector.select()` instead of `time.sleep()` — Stage 4 makes this swap. Naming it `timeout` now will make the refactor a one-liner.
- Test trick: verify interleaving with two tasks (they don't exist yet — use plain closures): schedule `t1` that records `start = monotonic()` then a timer that fires at +100ms recording `end`; assert a timer scheduled at +50ms ran *between* them. You can emulate with two timers at 50ms/100ms and one `call_soon` first.

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

### Implementation logic

1. `EventLoop.__init__`: add `self._selector = selectors.DefaultSelector()`.
2. `add_reader(fd, callback, *args)` → `self._selector.register(fd, selectors.EVENT_READ, (callback, args))`. Mirror for `add_writer` with `EVENT_WRITE`. Raise/return False if already registered (pick one, document it).
3. `remove_reader(fd)` / `remove_writer(fd)` → `unregister`, tolerating unknown fds.
4. Wire into the tick (rough version; Stage 4 formalizes `_run_once`):
   - compute `timeout` from Stage 2 logic (0 if ready work pending, else time to next timer, else `None` — but cap `None` in tests so the suite can't hang forever).
   - `events = self._selector.select(timeout)`; for each `(key, mask)`: pop callback from `key.data` and `call_soon` it (don't run inline — keep one execution path).
   - then fire expired timers, drain ready.
5. Test shape: `r, w = os.pipe()`, `loop.add_reader(r, on_read)`, `os.write(w, b"hi")` from a `call_later(0.01, ...)` or a thread, `run_forever` with a stop condition once data arrives.

### Edge cases & pitfalls

- **A fd registered twice:** `register` raises `KeyError`. Decide: `add_reader` on an already-watched fd replaces, ignores, or raises — asyncio raises unless you remove first. Test your choice.
- **Selector with zero fds + `timeout=None`:** blocks forever. Your loop-exit condition must now be "no ready AND no timers AND no registered fds" — or tests hang. Add a safety timeout in tests.
- **Level-triggered semantics:** `epoll` default is level-triggered: a fd stays "ready" until drained. If your callback doesn't read all data, you'll get woken every tick — fine for now, but don't busy-spin on it (Stage 4's timeout=0-when-ready rule matters here).
- **Fds are ints, callbacks hold refs:** closing an fd without `unregister` leaks the selector registration and can recycle the fd number onto a new socket — always pair `close` with `remove_*` (Stage 11 will punish you otherwise).

### Hints

- Start with `os.pipe()` not sockets: no ports, no `TIME_WAIT`, fully hermetic. Sockets arrive in Stage 10.
- Keep dispatch uniform: I/O readiness just enqueues into `_ready`. One execution path (drain ready queue) keeps exception handling in one place.
- Peek at CPython's `base_events.py`: `add_reader` stores `(callback, args)` as selector `data` — exactly this shape.

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

### Implementation logic

1. Extract `_run_once(self)`:
   ```python
   def _run_once(self):
       timeout = self._compute_timeout()   # 0 / delay / None
       if self._selector.get_map():
           events = self._selector.select(timeout)
           for key, mask in events:
               cb, args = key.data
               self.call_soon(cb, *args)
       elif timeout:
           time.sleep(timeout)
       self._fire_expired_timers()
       ntodo = len(self._ready)
       for _ in range(ntodo):
           cb, args = self._ready.popleft()
           self._run_callback(cb, args)    # try/except wrapper from Stage 1
   ```
2. `_compute_timeout()`: `0.0` if `_ready` non-empty; elif `_timers`: `max(0, deadline - monotonic())`; elif selector has fds: `None`; else: sentinel meaning "exit".
3. `run_forever()`: `while not stopping and (ready or timers or fds): self._run_once()`.
4. Bound the per-tick callback count (`ntodo` snapshot) so callbacks scheduled *during* the drain run next tick — prevents a self-rescheduling callback from starving I/O/timers within one tick.

### Edge cases & pitfalls

- **Unbounded drain starvation:** draining the whole deque without the `ntodo` snapshot lets a chatty callback starve timers/I/O. asyncio caps per-tick work; copy that.
- **`select` interrupted by signals:** catches `InterruptedError` and treats as empty events (retry next tick).
- **Timeout drift:** recompute `now` after `select` returns — the wait itself took time; timers that expired *during* the block must fire this tick.
- **Empty-selector `select(None)`:** hangs forever — the exit condition in `run_forever` must be checked *before* calling `_run_once`, never inside the blocking call.

### Hints

- Read asyncio's `_run_once` source side-by-side while writing yours; line up the five steps and you'll catch ordering bugs (e.g. firing timers before vs after select changes deadline precision).
- Test the timeout rule directly: with only a 100 ms timer pending, `_compute_timeout()` should return ≈0.1; with ready work pending, exactly 0.
- Keep `_run_callback` as the single exception-handling choke point from Stage 1 — `_run_once` stays clean.

### References

- CPython `Lib/asyncio/base_events.py` — `BaseEventLoop._run_once` (the canonical implementation)
- [Build your own Event Loop in Python](https://techtalk.digitalpress.blog/build-your-own-event-loop-in-python/) — `run()` mixing ready/sleeping/select
- [Beginner's Tutorial: MiniLoop](https://geekyhumans.com/beginners-tutorial-building-a-custom-asyncio-event-loop-in-python/) — ready vs scheduled separation

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

### Implementation logic

1. Represent a task as a plain generator object scheduled via `call_soon`-style stepping. Minimal approach: wrap stepping in a closure:
   ```python
   def _step(gen):
       try:
           next(gen)
       except StopIteration:
           pass          # done — don't reschedule
       else:
           loop.call_soon(lambda: _step(gen))  # suspend → requeue
   ```
2. Generator-based `sleep(seconds)`:
   ```python
   def sleep_gen(seconds):
       deadline = time.monotonic() + seconds
       while time.monotonic() < deadline:
           yield
   ```
   Each `next()` either re-yields (not yet) or returns (expired).
3. Composition with `yield from`: task bodies use `yield from sleep_gen(1)` so the inner yields bubble up to the loop's `next()` call unchanged.
4. Tests assert *interleaving*: task A (2× 50 ms sleeps) and task B (1× 100 ms) produce `A B A`-ish ordering and finish in ≈100 ms total. Add the classic 1 ms `time.sleep` anti-spin? No — generators requeue every tick, so this stage busy-loops by design; note it, fix it in Stage 7 with timer-backed Futures.

### Edge cases & pitfalls

- **Busy-spin by construction:** requeue-on-yield with no waiting means the loop spins at 100% CPU. That's *expected* here — it's the motivation for timer-backed Futures next. Don't "fix" it with `time.sleep` inside the loop; that would serialize everything.
- **Forgetting `StopIteration`:** if you requeue unconditionally, finished tasks spin forever yielding nothing. The `except StopIteration: don't reschedule` branch is the whole completion protocol.
- **`yield` vs `yield from`:** a bare `yield` suspends one frame; `yield from sub()` delegates so the *inner* generator's yields reach the loop. Mixing them up breaks suspension depth.
- **Exceptions inside tasks:** an uncaught exception in a generator propagates out of `next()` — catch it in `_step`, record it, don't reschedule. (Stage 12 builds the full propagation story.)

### Hints

- This is the DEV-community "30-line loop" almost verbatim: queue of `(job, wake_at)`, `next(job)`, requeue or drop. If your code is much longer, you're overcomplicating it.
- Keep tasks as raw generators + closures for now — the `Task` class comes in Stage 7 once Futures exist. Resist building the class early.
- Write the test to print timestamps; watching `A@0ms B@0ms A@50ms done@100ms` is the moment the model clicks.

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

### Implementation logic

1. No loop changes needed — `yield from` is interpreter machinery. This stage is about *using* it correctly and testing the semantics:
   ```python
   def inner():
       yield from sleep_gen(0.05)
       return 42

   def outer():
       result = yield from inner()   # result == 42
       results.append(result)
       yield from sleep_gen(0.05)
   ```
2. Drive `outer()` with the Stage 5 stepper unchanged — prove the loop is oblivious to nesting depth.
3. Exception case:
   ```python
   def failing():
       yield
       raise ValueError("boom")

   def outer2():
       yield from failing()   # ValueError must propagate to the loop's next()
   ```
   Assert the stepper sees `ValueError` (not `StopIteration`), records it, drops the task.
4. Three-level nesting test (outer → middle → inner) to prove arbitrary depth.

### Edge cases & pitfalls

- **Swallowing exceptions mid-chain:** a `try/except` around `yield from` that catches everything and doesn't re-raise leaves the outer task suspended forever once Futures arrive (Stage 7) — establish the "always propagate or resolve" discipline now.
- **`return` with a value inside a generator being driven by bare `next()`:** works fine (`StopIteration.value`), but code that catches `StopIteration` and ignores `.value` silently drops results — check your stepper preserves it.
- **Sending non-None into a just-started generator:** `gen.send(x)` before first `next()` raises `TypeError`. Your stepper always resumes with `next()`/`send(None)` — remember this rule for Stage 7's `Task.send(result)`.
- **Confusing `yield` with `yield from` in task bodies:** `yield sleep_gen(1)` yields the *generator object itself* to the loop (junk); `yield from sleep_gen(1)` delegates. A classic typo — the Stage 5 tests catch it as a hang.

### Hints

- Read the formal `yield from` expansion in PEP 380 once — it's ~15 lines of pseudocode and demystifies `send`/`throw` passthrough completely.
- The CodingPancake guide's delegation table (yield-loop vs `yield from`/`await`) is a good cheat sheet for what's automatic vs manual.
- Keep a debug print of "who yielded what" while developing: if the loop ever receives a raw generator object, some frame used `yield` where it meant `yield from`.

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

### Implementation logic

1. `loop/futures.py`:
   ```python
   class Future:
       def __init__(self):
           self._result = None; self._done = False; self._callbacks = []
       def done(self): return self._done
       def result(self):
           if not self._done: raise RuntimeError("not done")
           if isinstance(self._result, BaseException): raise self._result
           return self._result
       def set_result(self, value):
           self._done = True; self._result = value
           for cb in self._callbacks: cb(self)
       def add_done_callback(self, fn):
           if self._done: fn(self)
           else: self._callbacks.append(fn)
       def __await__(self):
           return (yield self)
   ```
2. `Task(Future)` drives a coroutine:
   ```python
   class Task(Future):
       def __init__(self, coro, loop):
           super().__init__()
           self._coro = coro; self._loop = loop
           self._loop.call_soon(self._step)
       def _step(self, future=None):
           try:
               if future is None: yielded = self._coro.send(None)
               else: yielded = self._coro.send(future.result())
           except StopIteration as e:
               self.set_result(e.value); return
           except BaseException as e:
               self.set_result(e); return     # stored; raised on .result()
           if isinstance(yielded, Future):
               yielded.add_done_callback(self._step)
           else:
               raise RuntimeError(f"coroutine yielded {yielded!r}, expected Future")
   ```
3. `loop.create_task(coro)` → `Task(coro, self)`; timer-backed sleep:
   ```python
   def sleep(self, delay, result=None):
       fut = Future()
       self.call_later(delay, fut.set_result, result)
       return fut
   ```
   Note: `sleep` returns a Future (awaitable via `__await__`), it is *not* itself a coroutine.
4. Fix the exit condition: pending *unresolved Futures with callbacks* keep the loop alive only via their underlying timer/fd registrations — the loop still only tracks ready/timers/fds.

### Edge cases & pitfalls

- **The lost-task trap:** a Task nobody holds a reference to can be GC'd mid-flight; worse, its exception dies silently. Keep a strong-ref set (`loop._tasks`) until completion, and log unretrieved exceptions (asyncio's "exception was never retrieved" warning).
- **Yielding a non-Future:** decide loudly (raise `RuntimeError`) rather than silently requeueing — silent acceptance masks `yield`-vs-`yield from` typos from Stage 6.
- **`set_result` twice:** second call should raise (`InvalidStateError` in asyncio) — a double-resolving timer indicates a logic bug.
- **Callback reentrancy:** `set_result` runs callbacks synchronously; a callback that resolves another Future recurses. Fine at this scale, but be aware the stack grows with chain length.
- **Blocking inside `result()`:** never block waiting — `result()` on an unfinished Future raises. Waiting happens *only* via `yield`/`await`.

### Hints

- Follow the indooroutdoor.io article's Task/Future/Scheduler build closely — it derives exactly this protocol (yielded Future replaces the task in the queue, resolution callback reschedules).
- Test CPU spin explicitly: run two 100 ms sleeps, assert wall ≈100 ms *and* that a counter incremented by a tight `call_soon` re-scheduler barely advances (or measure process CPU time).
- Keep `Future` loop-agnostic (no loop reference) and put loop-awareness only in `Task` — this pays off in Stage 10 where socket Futures resolve from selector callbacks.

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

### Implementation logic

1. Verify — don't rewrite: take the Stage 7 test bodies, convert `def task(): yield from fut` → `async def task(): await fut`, drive with the same `Task` class. If `Task._step` used `next()` anywhere, switch to `.send(None)`.
2. `sleep` stays a plain function returning a `Future` — `await loop.sleep(0.05)` works because `Future` is awaitable. Optionally add an `async def sleep` wrapper for ergonomics; it's equivalent.
3. Add `loop.run_until_complete(coro_or_future)`: wrap in a Task, `run_forever` until that Task completes, return/raise its result. This mirrors `asyncio.run()`'s core and becomes the standard test driver:
   ```python
   def run_until_complete(self, awaitable):
       task = self.create_task(_ensure_coro(awaitable))
       task.add_done_callback(lambda _: self.stop())
       self.run_forever()
       return task.result()
   ```
4. Rewrite the smoke interleaving test with `async def main()` + `create_task` children — this is the shape every later stage uses.

### Edge cases & pitfalls

- **`await` on a bare generator fails:** native coroutines require awaitables (`__await__`) or coroutines. A test accidentally awaiting a generator function raises `TypeError` — good, that's the type discipline `async` buys you over Stage 5's free-for-all.
- **Mixing `yield` and `await`:** `yield` inside `async def` makes it an *async generator* — a different protocol your loop doesn't support. Lint for it: any `yield` in an `async def` body is a bug at this stage.
- **`coro.send` vs `gen.send`:** identical API, but coroutine frames can't be introspected like generators — debug prints of "current yield" stop working; rely on Task-level logging instead.
- **`run_until_complete` reentrancy:** calling it from inside a running loop (nested) must raise — guard with the `_running` flag from Stage 1.

### Hints

- The jacobpadilla article's refactor section (generators → `__await__` + `async`) is the exact diff you're making — compare line by line.
- If everything passes by just changing syntax, say so loudly in a commit message: "async/await is not magic" is the thesis of the whole project.
- Keep one generator-based test alive (don't delete Stage 5's file) as documentation of the equivalence.

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

### Implementation logic

1. `async def gather(*awaitables)` or a function returning a parent `Future`:
   ```python
   def gather(self, *awaitables):
       children = [self.create_task(a) for a in awaitables]
       parent = Future()
       results = [None] * len(children)
       remaining = len(children)
       def _child_done(i, child):
           nonlocal remaining
           if parent.done(): return
           try: results[i] = child.result()
           except BaseException as e:
               parent.set_result(e)   # or set_exception path; document choice
               return
           remaining -= 1
           if remaining == 0:
               parent.set_result(results)
       for i, ch in enumerate(children):
           ch.add_done_callback(lambda c, i=i: _child_done(i, c))
       if not children: parent.set_result([])
       return parent
   ```
2. `await loop.gather(...)` works because the parent is a Future (`__await__`).
3. Empty-`gather()` resolves immediately with `[]`.
4. Timing test: children sleeping 50/100/150 ms → wall ≈150 ms (assert `< 250 ms` with jitter margin, `>= 150 ms`).

### Edge cases & pitfalls

- **Late-binding closure bug:** `lambda c: _child_done(i, c)` in a loop captures the *variable* `i` — all callbacks see the last index. Bind with a default arg (`i=i`) or `functools.partial`.
- **Children finishing before callbacks attach:** `add_done_callback` fires immediately for done Futures (Stage 7 contract) — so this is safe, but only because you implemented that rule. Test gather with already-done children.
- **Exception double-count:** after the parent resolves with an exception, later children completing must be ignored (`if parent.done(): return`) or they'd `set_result` twice → raise.
- **Nesting:** `gather(gather(a, b), c)` should work — parent Futures are awaitables like any other. Add a nesting test; it exercises the protocol generically.

### Hints

- The countdown-latch pattern (counter + indexed slots) recurs in barriers, `wait()`, connection pools — learn it cold here.
- Keep `gather` loop-agnostic if you can (takes Tasks/Futures, returns a Future); only child *creation* needs the loop. This makes Stage 13's parity tests trivially portable.
- Decide failure semantics *before* writing tests: write the docstring first, then the tests, then the code.

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

### Implementation logic

1. `loop/sock.py` (functions take the loop explicitly, or make them methods — pick one):
   ```python
   async def sock_recv(loop, sock, n):
       fut = Future()
       def _on_readable():
           try: data = sock.recv(n)
           except BlockingIOError: return   # spurious wakeup; stay registered
           loop.remove_reader(sock.fileno())
           fut.set_result(data)
       loop.add_reader(sock.fileno(), _on_readable)
       return await fut
   ```
2. `sock_sendall`: same shape with `add_writer` + `sock.send` loop over the buffer; resolve with bytes-sent count when drained.
3. `sock_accept`: `add_reader` on the listening socket; on readiness `conn, addr = sock.accept()`, `conn.setblocking(False)`, resolve `(conn, addr)`.
4. Test with `socketpair()`: both ends non-blocking, server task `await sock_recv`, client `await sock_sendall`, assert echo. Then a real loopback TCP pair (`bind 127.0.0.1:0`) to prove it works over real sockets, not just pairs.

### Edge cases & pitfalls

- **Forgetting `setblocking(False)`:** one blocking `recv` on the loop thread freezes *everything* — timers, other clients, all of it. Assert non-blocking in the primitives (`sock.getblocking()` check or set it yourself).
- **Spurious wakeups:** readiness doesn't guarantee the op succeeds — always `try/except BlockingIOError` and stay registered on failure, or you'll drop the await silently.
- **Fd reuse after close:** unregister *before* resolving the Future — the awaiting task may immediately close the socket, and a stale registration could fire for a recycled fd number.
- **`BlockingIOError` vs `ssl.SSLWantRead`:** plain sockets only here; note TLS as out-of-scope (its want-read/write dance is a whole stage by itself — skip it).
- **Test flakiness:** loopback TCP is fast but not instant; the primitives must not assume data arrives in one segment — `sock_recv` returns *up to* `n` bytes, tests should frame accordingly (length prefix or fixed-size echo).

### Hints

- Mirror asyncio's `sock_recv`/`sock_sendall`/`sock_accept` signatures (`loop.sock_recv(sock, n)`) — Stage 13 parity becomes a drop-in swap.
- The indooroutdoor.io `AcceptSocket`/`ReadSocket` Future subclasses are the same idea expressed as classes; functions + one-shot callbacks are simpler — pick the style you prefer, both are correct.
- Debug with `ss -tlnp` / `netstat` if the TCP test hangs: a missing `listen()` or a full backlog looks exactly like a loop bug.

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

### Implementation logic

1. Server coroutine:
   ```python
   async def serve_forever(loop, listener):
       while True:
           conn, addr = await loop.sock_accept(listener)
           loop.create_task(handle_client(loop, conn))

   async def handle_client(loop, conn):
       try:
           while True:
               data = await loop.sock_recv(conn, 4096)
               if not data: break            # orderly shutdown
               await loop.sock_sendall(conn, data)
       finally:
           loop.remove_reader(conn.fileno())  # tolerate missing
           conn.close()
   ```
2. Test harness: bind `127.0.0.1:0` (OS picks a free port — never hardcode), run the server on your loop in a background thread via `run_forever`, drive N=20–50 clients from `threading` (blocking sockets are fine *in test threads*), `join` with timeouts, assert payloads.
3. Concurrency proof: clients sleep-stagger their sends; assert total wall ≈ single-client time, not N×. Or: one client sends slowly (byte-at-a-time with delays) while others finish fast — slow client must not stall anyone.
4. Keep a connection counter (increment on accept, decrement in `finally`) and assert it returns to 0 — proves no leaked tasks.

### Edge cases & pitfalls

- **Fd leaks:** every accepted socket must be unregistered *and* closed on every exit path (client disconnect, exception, test teardown). Leaked fds eventually hit `EMFILE` and the selector keeps firing on dead sockets. The `finally` block is non-negotiable.
- **`recv` → `b""`:** means the client closed — `break`, don't re-register. Re-registering on a closed socket spins the loop forever.
- **Listener setup:** `SO_REUSEADDR`, `bind`, `listen(backlog>=100)`, `setblocking(False)` — missing any one gives "address in use" / blocking-accept / refused-connection failures that look like loop bugs.
- **Test teardown:** stop the loop, close the listener, join the server thread with a timeout. A test that leaves a thread bound to a port poisons every later run. Use fixtures with `yield` + cleanup.
- **Half-close / abrupt RST:** `ConnectionResetError` from `recv` on a killed client — catch, treat like disconnect. Test it by having one client `close()` without `shutdown()` mid-stream.

### Hints

- Start with N=5 clients and grow to 50+ once green — separates protocol bugs (fail at 1) from lifecycle bugs (fail at 50).
- Watch `ls /proc/<pid>/fd | wc -l` (or `lsof`) across runs: constant fd count = clean; growing = leak. Add an fd-count assertion if you're keen.
- This is the classic CodeCrafters-style endgame ("serve concurrent clients on one thread") — if it holds up at 100+ connections with correct echoes, the reactor is real.

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

### Implementation logic

1. `Task.cancel()`:
   ```python
   def cancel(self):
       if self.done(): return False
       self._cancel_requested = True
       # wake the step machinery with a throw instead of a send:
       self._loop.call_soon(self._step_throw, CancelledError())
       return True

   def _step_throw(self, exc):
       try:
           yielded = self._coro.throw(exc)
       except StopIteration as e:
           self.set_result(e.value)   # suppressed cancellation → completes
       except CancelledError as e:
           self.set_exception_as_cancelled(e)
       except BaseException as e:
           self.set_result(e)
       else:
           # resumed and yielded another Future — re-suspend on it
           yielded.add_done_callback(self._step)
   ```
2. Distinguish states: `cancelled()` flag vs `done()` vs `exception()`. `result()` raises `CancelledError` if cancelled, the stored exception if failed, the value if ok.
3. Shielding (optional, document if skipped): `await shield(fut)` that detaches cancellation — note asyncio has it; you may defer, but write down the decision.
4. Tests: (a) cancel pending sleep → `CancelledError` on `result()`, task `cancelled()` True; (b) 3-deep chain raise → identical exception object type+message at top; (c) sibling tasks unaffected by one cancellation (loop keeps ticking, others complete).

### Edge cases & pitfalls

- **Swallowed `CancelledError`:** `except Exception: pass` in user code *won't* catch it (BaseException) — but `except BaseException: pass` will, converting a cancel into a hang unless re-raised. Document this; test that a suppressing coroutine completes normally (that's legal, not a bug).
- **Cancelling a done task:** must return `False` and do nothing — throwing into a finished coroutine raises `RuntimeError`/`StopIteration` weirdness.
- **Double-resolve after cancel:** the original Future the task was parked on may *later* resolve and fire `_step` — guard with `if self.done(): return` at the top of both step paths.
- **Unretrieved-cancelled warnings:** like Stage 7's lost-exception trap, a cancelled task nobody inspects should log — otherwise cancellations vanish silently in production.
- **Loop liveness:** cancelling the *last* pending task must still let `run_forever` exit (no orphaned timer/fd registrations keeping the loop alive).

### Hints

- Read CPython `Task.cancel` + `Task.__step` + `coro.throw` flow while implementing — the state machine (pending → cancelling → cancelled vs finished) is subtle and theirs is the reference.
- Test cancellation timing variants: cancel before first step, cancel mid-sleep, cancel an already-done task, cancel twice. Each hits a different branch.
- The CodingPancake guide's "swallowing exceptions in yield chains" pitfall is the same bug class: any path where an error state doesn't reach the root Task frame = permanent suspension.

### References

- CPython `Lib/asyncio/tasks.py` — `Task.cancel`, `Task.cancelled`, `Task.__step`
- [PEP 492](https://peps.python.org/pep-0492/) — `CancelledError` semantics
- [Custom Event Loop guide — exception propagation pitfalls](https://www.codingpancake.com/2026/07/how-to-implement-custom-event-loop-in.html)
- Python [`coroutine.throw`](https://docs.python.org/3/reference/expressions.html#await-expression) docs

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

### Implementation logic

1. Define a tiny driver protocol both backends satisfy:
   ```python
   # tests/test_parity.py
   @pytest.fixture(params=["mine", "asyncio"])
   def driver(request): ...
   ```
   - `"mine"`: spins your `EventLoop` in a thread, exposes `run(coro)` via `run_until_complete`, plus `sleep/gather/sock_*` bound to your loop.
   - `"asyncio"`: `asyncio.run(...)` with the real primitives.
2. Port 3–5 core scenarios behind the driver: sleep interleaving (Stage 7), gather ordering (Stage 9), socketpair echo (Stage 10), mid-sleep cancellation (Stage 12). Keep each scenario backend-agnostic (no loop-specific imports inside the test body).
3. Write the differences doc: create a `DIFFERENCES.md` (or README section) listing every divergence found — e.g. "no `shield()`", "cancellation doesn't propagate to gather siblings (fails fast instead)", "no thread-safety (`call_soon_threadsafe` missing)", "timer precision ±X ms vs asyncio's". Each entry: behavior, why, planned or wontfix.
4. (Stretch) Implement `asyncio.AbstractEventLoop` minimal methods and run one existing asyncio-based snippet (e.g. `asyncio.gather` itself) on your loop via a policy — proves interface compatibility, not just behavioral similarity.

### Edge cases & pitfalls

- **Timing-sensitive assertions:** your loop and asyncio have different scheduling overhead — never assert exact interleavings or tight wall-time bounds in parity tests; assert orderings, result sets, and generous time windows.
- **Resource cleanup asymmetry:** asyncio closes transports on loop close; yours needs manual closes (Stage 11 discipline). Parity-test fixtures must clean up *both* backends' way or one side leaks ports/threads.
- **Cancellation semantic gaps:** this is where parity most likely breaks (Stage 9/12 documented choices). A red parity test here isn't failure — it's the differences doc writing itself. Capture, don't hide.
- **Threading in fixtures:** running your loop in a helper thread while asyncio runs inline is fine, but keep the driver's threading model identical across cases or you test the harness, not the loops.

### Hints

- Start with the *easiest* scenario (gather ordering) to shake out fixture bugs before touching sockets/cancellation.
- `asyncio`'s extra code over yours is corner cases (signal handling, exception groups, `contextvars`, thread-safety) — when a parity test passes, note *why* it's equivalent; when it fails, categorize: missing feature vs semantic difference vs timing flake.
- The art049 "Demystifying AsyncIO" finale (running a real ASGI server on a custom loop) is the aspirational version of this stage — your parametrized suite is the pragmatic version.

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
