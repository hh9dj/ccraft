# Stage 4: The complete loop tick

## Objective

Now fuse the three event sources you have — ready callbacks, timers, and file descriptors — into one coherent tick. A single `_run_once()` computes how long it may block, performs one `select`, promotes expired timers and ready fds, then drains the ready queue. The deliverable is a complete reactor with a defined ordering and timeout rule, fair enough that no source can starve another. Focus areas: timeout computation and fair scheduling order.

## Steps

- Confirm Stage 3 is done.
- Study the phases of asyncio's `_run_once`: compute the timeout, select, promote I/O, promote timers, then run the ready callbacks. Read CPython `base_events.py` (`_run_once`), [Redis `ae.c`](https://github.com/redis/redis/blob/unstable/src/ae.c), and [libuv `core.c`](https://github.com/libuv/libuv/blob/v1.x/src/unix/core.c).
- Define `_run_once()` and `_compute_timeout()` returning `0`, a delay, or `None`. Why: the timeout rule is "ready work means 0; otherwise the next deadline; otherwise `None` if fds are registered; otherwise exit."
- Funnel every event source through `_ready` so no source can starve another.
- Cap how much work each tick drains.
- Handle `InterruptedError` from `select`, and recompute `now` after the wait so timers that expired during it fire this tick.
- Never call `select(None)` when the exit condition already holds.

## Design Questions

- Which phase orderings change timing precision?
- What is the single choke point for exceptions?
- How is the ready snapshot sized so chatty callbacks cannot starve other work?

## Tests

- [ ] A mixed timer and I/O workload completes, and the loop exits when drained.
- [ ] `_compute_timeout` unit tests cover `0`, approximately the delay, and `None`.
- [ ] A self-rescheduling `call_soon` does not starve a 10 ms timer.

## Hints

- Test command: `uv run pytest tests/test_run_once.py`. A pipe reader and a 50 ms timer should both fire.
- Chatty callbacks can starve other work unless each tick is capped.
- `InterruptedError` must be caught, and `now` must be recomputed after `select`.
- Never call `select(None)` when the exit condition already holds.
- Line your phases up against asyncio's — which orderings change timing precision?
