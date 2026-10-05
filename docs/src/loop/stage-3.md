# Stage 3: Readiness polling with `selectors`

## Objective

Next, make file descriptors an event source so the loop reacts to I/O readiness instead of guessing. `add_reader`/`add_writer` register an fd and a callback with the selector; the OS tells the loop when the fd is readable or writable, and the loop dispatches the callback. Your loop now blocks in `select` rather than `sleep`, and the exit condition must account for registered fds. This is the shift from time-driven to I/O-driven. Focus areas: I/O multiplexing, file descriptors, and non-blocking I/O.

## Steps

- Confirm Stage 2 is done and the loop can compute a block timeout.
- Study readiness semantics: readiness is not completion — the OS reports that a descriptor is ready, but your callback still performs the read. Read the [selectors docs](https://docs.python.org/3/library/selectors.html). Why: `DefaultSelector` picks `epoll`, `kqueue`, or `select` as appropriate, and exposes `register`, `select(timeout)`, and `unregister`.
- Define the interface: `add_reader(fd, cb, *args)` / `add_writer(...)` · `remove_reader(fd)` / `remove_writer(fd)`.
- Decide the duplicate-registration policy.
- Extend the exit condition to account for registered fds.
- Decide how each ready fd's data is drained, given the level-triggered model. Why: an undrained descriptor wakes the loop on every tick.
- Pair `close` with `remove_*` so descriptors are not left stale after reuse.

## Design Questions

- Where is the callback stored — as the selector `data`, or in a side table?
- When the same fd is registered twice (a `KeyError`), do you replace, ignore, or raise — and which will you test?
- With zero fds and `timeout=None`, `select` blocks forever, so when is the exit condition checked?

## Tests

- [x] A pipe write fires the reader callback with the correct bytes, and `remove_reader` stops it.
- [x] With zero file descriptors, zero timers, and an empty queue, the loop exits instead of hanging.
- [x] A reader and a writer on the same file descriptor coexist.

## Hints

- Test command: `uv run pytest tests/test_selectors.py`. A write to an `os.pipe()` fires the reader callback with the correct bytes. See [Demystifying AsyncIO](https://slides.com/art049/demystifying-asyncio) for framing.
- With zero fds and `timeout=None`, `select` blocks forever, so check the exit condition first.
- The level-triggered selector re-wakes until the descriptor is drained.
- Always pair `close` with `remove_*` to avoid stale descriptors after reuse.
- Why use `os.pipe()` before moving on to sockets? Should dispatch happen inline or be enqueued into the ready path — which choice makes exception handling simpler?
