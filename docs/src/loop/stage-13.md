# Stage 13: Drop-in asyncio comparison

## Objective

Finally, validate against the reference. Run the same scenarios — sleep, gather, echo, cancellation — against both your loop and real `asyncio` through a thin driver, and document every divergence. The point is to confirm your semantics match production where they should, and to name the places where they intentionally differ. Focus areas: API parity and differential testing.

## Steps

- Confirm Stages 1 through 12 are done.
- Study CPython `base_events.py` and `events.py` and the [asyncio event loop docs](https://docs.python.org/3/library/asyncio-eventloop.html). Why: differential testing means the same inputs, two implementations, and the same assertions.
- Define a `driver` abstraction that both backends satisfy (`run` plus `sleep`/`gather`/`sock_*`), and write a list of divergences.
- Keep the driver's threading model identical across backends, and clean up resources the way each backend expects.
- Assert orderings and results with generous windows; never assert exact interleavings.
- Categorize failures as a missing feature, a semantic difference, or a timing flake. Why: cancellation semantics are where parity most likely breaks — capture the differences rather than hiding them.
- Optional stretch: subclass `asyncio.AbstractEventLoop` to make it a real backend.

## Design Questions

- Keep the surface minimal — `call_soon`/`call_later`, reader/writer, `create_task`, `sock_*`, and `run_*`/`stop`?
- Which scenario should you start with?

## Tests

- [ ] `tests/test_parity.py` passes on both backends for sleep, gather, echo, and cancellation.
- [ ] `DIFFERENCES.md` documents every divergence with its rationale.
- [ ] The full suite is green: `uv run pytest tests/`.

## Hints

- Test commands: `uv run pytest tests/test_parity.py`, then the full suite `uv run pytest tests/`.
- Assert orderings and results with generous windows, never exact interleavings.
- Clean up resources the way each backend expects.
- Cancellation semantics are where parity most likely breaks.
- Keep the driver's threading model identical across backends.
