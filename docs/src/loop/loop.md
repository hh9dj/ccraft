# Project: Event Loop / Async Runtime

In this project you'll build a single-threaded event loop — also called a reactor — that watches many I/O sources for readiness and dispatches callbacks or tasks when events occur. Once that works, you'll build an executor on top of it to drive coroutines and futures, which is how you'll discover cooperative multitasking from the inside.

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

Read these for inspiration; don't copy them. The listed entry points are the best places to start, and comparing your code to theirs is often the fastest way to understand a tricky corner.

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

- [x] [Stage 0: Setup](./stage-0.md)
- [x] [Stage 1: A bare loop with `call_soon`](./stage-1.md)
- [x] [Stage 2: Timers (`call_later`)](./stage-2.md)
- [ ] [Stage 3: Readiness polling with `selectors`](./stage-3.md)
- [ ] [Stage 4: The complete loop tick](./stage-4.md)
- [ ] [Stage 5: Generators as coroutines](./stage-5.md)
- [ ] [Stage 6: `yield from` delegation](./stage-6.md)
- [ ] [Stage 7: Futures and Tasks](./stage-7.md)
- [ ] [Stage 8: Native coroutines](./stage-8.md)
- [ ] [Stage 9: `gather`](./stage-9.md)
- [ ] [Stage 10: Async socket I/O primitives](./stage-10.md)
- [ ] [Stage 11: Echo server end-to-end](./stage-11.md)
- [ ] [Stage 12: Cancellation & exception propagation](./stage-12.md)
- [ ] [Stage 13: Drop-in asyncio comparison](./stage-13.md)

## Acceptance

By the end you'll have a single-threaded, epoll-backed event loop that schedules callbacks and timers, drives native `async def` coroutines through Futures and Tasks, serves many concurrent TCP connections, and handles cancellation and exception propagation — passing the same test suite as real `asyncio`.
