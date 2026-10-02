# Stage 1: A bare loop with `call_soon`

## Objective

Time to build the scheduler core. In this stage you'll write the smallest possible `EventLoop`: a FIFO queue of callbacks, plus `call_soon()`, `run_forever()`, and an exit-when-idle behavior. `call_soon` puts work in the queue, `run_forever` repeatedly pops one callback and runs it, and the loop exits on its own once the queue is empty. There's no clock and no I/O here — the goal is to isolate the queue-and-run mechanism that every later feature will feed into. Focus areas: event-driven programming and the loop lifecycle.

## Steps

- Confirm Stage 0 is done and `EventLoop` imports cleanly.
- Think of the loop as a queue plus a `while` loop: pop work and run it. Later, event sources simply enqueue more work. "Liveness" means there is nothing left to do — a definition that will grow to include timers and file descriptors. Read the [30-line asyncio loop](https://dev.to/ritesh_fcb86fb4b3890c81e4/build-a-working-asyncio-event-loop-in-30-lines-of-plain-python-5gjb) and CPython `base_events.py` for a feel of the shape.
- Define the interface: `EventLoop()` · `call_soon(cb, *args)` · `run_forever()` · `stop()`.
- Choose the ready-queue data structure and justify it against O(1) operations at both ends.
- Mirror the asyncio names now (`call_soon`, `run_forever`, `stop`) so Stage 13 is easier. Reference: CPython `base_events.py`.
- Decide what `stop()` means: does it drop queued callbacks or drain them? Document your choice.
- Establish exception containment: an exception raised inside a callback must not kill the loop.
- Guard against a reentrant `run_forever` call.

## Design Questions

- What exactly gets enqueued — a callable plus args, a bound closure, or a task record? This is where the real design decisions live.
- What does the queue need to support once timers and I/O are added?
- What is the single choke point where callback errors are caught?
- What state does the loop need to detect that it is already running?

## Tests

- [x] Callbacks run in order, the loop exits when idle, `stop()` halts it, and callback errors stay contained.
- [x] `run_forever` returns immediately when nothing is scheduled.

## Hints

- Test command: `uv run pytest tests/test_call_soon.py`.
- An exception inside a callback must not kill the loop, and a reentrant `run_forever` must be rejected (guard it with a `_running` flag).
- Decide whether `stop()` drops or drains queued callbacks and write down your choice.
- Mirror the asyncio names now so Stage 13 is easier.
