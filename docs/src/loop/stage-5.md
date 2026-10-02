# Stage 5: Generators as coroutines

## Objective

Here's where cooperative multitasking begins. Instead of running callbacks only to completion, your loop can now drive generators as tasks that suspend at `yield` and resume later. Two tasks that each sleep should interleave so total wall time is the max sleep, not the sum. The loop becomes a scheduler of pausable frames rather than just functions. Focus areas: cooperative multitasking and the mechanics of pausing and resuming.

## Steps

- Confirm Stage 4 is done and you understand generators and `yield`/`send`.
- Think of a generator as a pausable frame and the loop as the thing that resumes it. Scheduling is cooperative, so a task that never yields freezes the loop. `return value` raises `StopIteration(value)`, which is how a result gets out. Read the [30-line loop](https://dev.to/ritesh_fcb86fb4b3890c81e4/build-a-working-asyncio-event-loop-in-30-lines-of-plain-python-5gjb) and [Recreating asyncio](https://jacobpadilla.com/writing/recreating-asyncio). Why: this is the same stepping protocol `await` will use later.
- Define `sleep_gen(seconds)` — a generator that yields until a deadline — with a stepper that detects completion.
- Add the task-driver behavior: use `next()` to reach a `yield` (suspend) or a `StopIteration` (done), then reschedule or finish accordingly.
- Record uncaught task exceptions instead of rescheduling, and never requeue a finished generator.

## Design Questions

- What is the minimal state a driven generator needs?

## Tests

- [ ] Tasks interleave in the expected order, and wall time is about the maximum sleep.
- [ ] Finished generators are never requeued.
- [ ] Composition with `yield from sleep_gen()` works.

## Hints

- Test command: `uv run pytest tests/test_generators.py`.
- Requeueing on every yield with no wait spins at 100% CPU (expected at this stage; timers fix it next).
- Forgetting `StopIteration` reschedules finished tasks forever.
- An uncaught task exception propagates out of `next()`.
- Which timestamp trace would prove true interleaving?
