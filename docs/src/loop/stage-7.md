# Stage 7: Futures and Tasks

## Objective

Now you'll represent a value that isn't ready yet. A `Future` is a placeholder that something else (a timer, a socket) resolves later. A `Task` is a coroutine driver that yields a Future, parks, and is resumed with the value once it resolves. `sleep()` stops spinning and truly suspends. This is the primitive `await` is built on and the boundary between your loop and user code. Focus areas: cooperative multitasking without polling.

## Steps

- Confirm Stages 5 and 6 are done.
- A Future holds a result, a done flag, and callbacks — `set_result` fires those callbacks. Suspend/resume works by yielding a Future, registering a re-wake, stopping stepping, resolving the Future, then `send(value)` back in. Read CPython `futures.py` and `tasks.py` and [Asyncio Demystified](https://dev.indooroutdoor.io/asyncio-demystified-rebuilding-it-from-scratch-one-yield-at-a-time). Why: `Future.__await__` is `return (yield self)`, the bridge to `await`.
- Define the interfaces:
  - `Future`: `done()`, `result()`, `set_result(value)`, `add_done_callback(fn)`, `__await__()`.
  - `Task(Future)`: `__init__(coro, loop)`.
  - On `EventLoop`: `create_task(coro) -> Task`, `sleep(delay, result=None) -> Future`.
- Provide the wake-up via `loop.call_later(deadline, future.set_result, value)`.
- Handle the lost-task trap: keep strong references to tasks and log unretrieved exceptions.
- Decide the error contract: yielding a non-Future raises `RuntimeError`, calling `set_result` twice raises, and `result()` on an unfinished Future raises — the only way to wait is via `yield` or `await`.

## Design Questions

- Should `Future` know about the loop — why keep it loop-agnostic?

## Tests

- [ ] Yield-Future runs through timer-resolve-resume, and exceptions are stored and re-raised.
- [ ] The `sleep()` interleaving test passes with wall time about the maximum delay and no spin.
- [ ] Yielding a non-Future and calling `set_result` twice both raise.

## Hints

- Test command: `uv run pytest tests/test_futures.py`. A timer resolves a Future, the task resumes with the value, and `sleep()` interleaves with almost no spin.
- The lost-task trap: keep strong references and log unretrieved exceptions.
- Yielding a non-Future raises `RuntimeError`; calling `set_result` twice raises; `result()` on an unfinished Future raises.
- How would you prove that the loop no longer spins while a task sleeps?
