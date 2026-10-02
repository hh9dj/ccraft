# Stage 9: `gather`

## Objective

Time for concurrency composition. `gather(*awaitables)` starts many awaitables at once, watches them finish in any order, and resolves once with results in argument order. It's fan-out and fan-in built purely from tasks and Future callbacks, and it shows that waiting on many things costs the max delay rather than the sum. Focus areas: fan-out and fan-in, and Future composition.

## Steps

- Confirm Stage 8 is done.
- Study CPython `tasks.py` (`gather`) and [Asyncio Demystified](https://dev.indooroutdoor.io/asyncio-demystified-rebuilding-it-from-scratch-one-yield-at-a-time). Why: children are wrapped in Tasks, callbacks are attached, a countdown resolves one parent Future, and results land in argument order regardless of finish order.
- Define `gather(*awaitables) -> Future`; an empty `gather()` resolves `[]` immediately.
- Choose failure semantics — fail-fast and cancel siblings, or await the rest — and document the choice.
- Bind loop indices correctly to avoid late-binding closure bugs.
- Handle already-done children, since `add_done_callback` fires immediately for them; ignore later completions once the parent resolves.

## Design Questions

- Does `gather` need the loop, or only child creation?
- Where else does the countdown-latch pattern recur?

## Tests

- [ ] Results are ordered, wall time is about the maximum delay, and empty and nested gather cases pass.
- [ ] Failure semantics are documented and tested.
- [ ] There is no closure index bug.

## Hints

- Test command: `uv run pytest tests/test_gather.py`. 50/100/150 ms sleeps should finish in about 150 ms; results follow argument order; one exception surfaces; empty and nested `gather(gather(...), ...)` cases pass.
- Bind loop indices with `i=i` to avoid late-binding closure bugs.
- `add_done_callback` fires immediately for already-done Futures — test already-done children.
- After the parent resolves, later completions must be ignored.
