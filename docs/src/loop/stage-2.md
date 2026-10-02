# Stage 2: Timers (`call_later`)

## Objective

Now make time an event source. `call_later(delay, cb)` is backed by a monotonic min-heap that sleeps just long enough and fires expired timers in deadline order. Your loop now has two things to drain — the ready queue and the timer heap — and it must decide how long it's allowed to sleep. That time budget is exactly what becomes the `select` timeout in Stage 4. Focus areas: timers as events and where the loop is allowed to block.

## Steps

- Confirm Stage 1 is done and you're comfortable with `heapq`.
- A timer is just work whose condition is "the clock has passed the deadline"; each tick promotes expired timers to the ready queue. Read [PEP 418](https://peps.python.org/pep-0418/) and [Build your own Event Loop](https://techtalk.digitalpress.blog/build-your-own-event-loop-in-python/). Why: `time.monotonic()` never jumps backwards, so it's the correct clock for deadlines.
- Define `call_later(delay, cb, *args)`, plus helpers to promote expired timers and compute the block timeout.
- Provide a tiebreaker for equal deadlines.
- Decide how `call_later(0, ...)` behaves relative to `call_soon`, and how negative delays are clamped.
- Establish the sleep discipline: the loop must block until the earliest deadline instead of busy-spinning.

## Design Questions

- What tuple ordering prevents the heap from comparing function objects?
- What value later replaces `time.sleep()` in the `select()` call?

## Tests

- [x] Timers fire in deadline order, wall time is about the maximum delay, and `call_later(0)` fires on the next tick.
- [x] The loop exits when both the ready queue and the timer heap are empty.
- [x] The loop does not hot-spin while waiting.

## Hints

- Test command: `uv run pytest tests/test_timers.py`. Use a tolerance — assert `elapsed >= delay` with a generous upper bound.
- Equal-deadline timers need a sequence-number tiebreaker.
- Forgetting to sleep until the deadline causes a 100% CPU spin.
- `call_later(0)` should behave like `call_soon`; clamp negative delays.
- How would you prove that a 50 ms timer ran between two 100 ms closures?
