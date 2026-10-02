# Stage 12: Cancellation & exception propagation

## Objective

Now handle task lifecycle beyond success. Cancelling a task injects `CancelledError` at its suspension point, and exceptions raised deep in an `await` chain surface at the task's result. The deliverable is correct state handling — pending, cancelling, done — with no wedged awaiters and no hangs when the last task is cancelled. Focus areas: cancellation as a first-class operation and exception flow through frames.

## Steps

- Confirm Stages 7 and 8 are done and you understand `throw()` propagation from Stage 6.
- Study CPython `tasks.py`, [PEP 492](https://peps.python.org/pep-0492/), and [Trio `_run.py`](https://github.com/python-trio/trio/blob/main/src/trio/_core/_run.py). Why: cancellation means calling `coro.throw(CancelledError)` where the task is parked, and `CancelledError` inherits from `BaseException`, so you must catch it distinctly from `Exception`.
- Define `Task.cancel() -> bool` · `Task.cancelled() -> bool`, and settle the state semantics of `Task.exception()` and `Task.result()`.
- Model the states pending, cancelling, and cancelled/finished.
- Ensure a child exception reaches the awaiter and marks the child done; never leave a parked awaiter behind.
- Guard against double-resolve after cancel, and cancel-done returning `False`. Why: a swallowed `CancelledError` (for example, a bare `except BaseException`) turns a cancel into a hang.
- Ensure cancelling the last task still lets the loop exit.

## Design Questions

- Which timings hit distinct branches — before a step, mid-sleep, after done, and twice?

## Tests

- [ ] A mid-sleep cancel raises `CancelledError`, a three-deep raise propagates, siblings are unaffected, and cancel-done returns `False`.
- [ ] Suppressed cancellation completes normally, and this is tested and documented.
- [ ] No awaiters are wedged, and every test's loop exits.

## Hints

- Test command: `uv run pytest tests/test_cancellation.py`.
- A swallowed `CancelledError` turns a cancel into a hang.
- Cancelling a done task returns `False` and does nothing; guard against double-resolve after cancel with `if self.done(): return`.
- Cancelling the last task must still let the loop exit.
- Which timings hit distinct branches — before a step, mid-sleep, after done, and twice?
