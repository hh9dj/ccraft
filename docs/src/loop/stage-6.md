# Stage 6: `yield from` delegation

## Objective

Let's make suspension composable. A task should be able to delegate to a sub-generator with `yield from`, so a sleep inside a nested helper still suspends the outer task, return values bubble up, and exceptions propagate down. This is the desugaring of `await`, and it should work without changing the loop's stepping logic from Stage 5. Focus areas: PEP 380 as the desugaring of `await`.

## Steps

- Confirm Stage 5 is done.
- Study [PEP 380](https://peps.python.org/pep-0380/) and the [Custom Event Loop guide](https://www.codingpancake.com/2026/07/how-to-implement-custom-event-loop-in.html). Why: `yield from` is a transparent bidirectional channel, not a loop, and `await x` is equivalent to `yield from x.__await__()`.
- Ensure your Stage 5 stepper handles nested generators unchanged, so sends and throws pass in both directions and the sub-generator's return value surfaces.
- Preserve `StopIteration.value` in the stepper.
- Decide, at each nesting layer, whether exceptions propagate or resolve. Why: swallowing exceptions mid-chain hides failures.

## Design Questions

- How does PEP 380 explain send and throw passthrough?

## Tests

- [ ] Return values propagate through one and three nesting levels, and an inner exception propagates.
- [ ] The Stage 5 stepper is unchanged, proving nesting is transparent.
- [ ] No hangs result from confusing `yield` with `yield from`.

## Hints

- Test command: `uv run pytest tests/test_delegation.py`.
- Never swallow exceptions mid-chain, and preserve `StopIteration.value`.
- Calling `send(x)` before the first `next()` raises `TypeError`.
- `yield sleep_gen(1)` yields the generator object itself (junk) instead of delegating — a classic typo.
- If the loop receives a raw generator, which mistake produced it?
