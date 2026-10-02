# Stage 8: Native coroutines

## Objective

Now run ordinary `async def` / `await` code on your engine with no new scheduling machinery. Native coroutines must flow through the same Task, Future, and tick you built for generators. The work here is mapping the coroutine protocol onto the driver you already have, plus a `run_until_complete` entry point. Focus areas: how `async`/`await` desugars and how `__await__` interoperates.

## Steps

- Confirm Stage 7 is done.
- Study [PEP 492](https://peps.python.org/pep-0492/) and [Recreating asyncio](https://jacobpadilla.com/writing/recreating-asyncio). Why: `async def` returns a coroutine, not a generator; you drive it with `send(None)` and `throw`; `await x` is approximately `yield from x.__await__()`; the first resume must send `None`.
- Define `run_until_complete(awaitable)` — returns the result or raises.
- Map the coroutine protocol onto the Stage 7 task driver.
- Guard nested `run_until_complete` with `_running`, and reject awaiting a bare generator (`TypeError`).
- Lint for `yield` inside `async def`, which creates an async generator that is unsupported here.

## Design Questions

- How small is the diff from Stage 7?

## Tests

- [ ] The same assertions as Stage 7 pass using `async def` syntax.
- [ ] `run_until_complete` returns the value or propagates the exception.
- [ ] The Stage 5 generator tests still pass untouched.

## Hints

- Test command: `uv run pytest tests/test_native_coros.py`.
- Awaiting a bare generator raises `TypeError` (good type discipline).
- A `yield` inside `async def` creates an async generator, which is unsupported here — lint for it.
- A nested `run_until_complete` must raise.
- Why keep one generator-based test after the rewrite?
