# Stage 10: Async socket I/O primitives

## Objective

Now connect the readiness model to the awaitable model. You'll wrap `recv`, `sendall`, and `accept` as awaitable operations that park on the selector and resume on readiness, handling partial sends and spurious wakeups. This is where non-blocking sockets become usable from coroutines. Focus areas: non-blocking I/O and readiness as Future resolution.

## Steps

- Confirm Stages 3, 4, and 7 are done.
- Study CPython `selector_events.py` and the [socket docs](https://docs.python.org/3/library/socket.html). Why: `setblocking(False)` makes `recv` raise `BlockingIOError`; the pattern is to try, then register and suspend, then retry on readiness.
- Define the interfaces: `sock_recv(loop, sock, n) -> bytes` · `sock_sendall(loop, sock, data) -> None` · `sock_accept(loop, listener) -> (conn, addr)`.
- Decide the registration model: selector registration is one-shot and unregistered on first firing — implement it as functions plus one-shot callbacks, or Future subclasses.
- Handle partial sends by looping until everything is sent, and treat `recv` returning `b""` as orderly shutdown.
- Unregister before resolving to avoid stale descriptors after reuse. Why: a blocking `recv` freezes the whole loop, so assert non-blocking mode in the primitives.

## Design Questions

- Why mirror asyncio's `sock_*` signatures?
- Which fits better — functions plus one-shot callbacks, or Future subclasses?

## Tests

- [ ] Socketpair and loopback TCP echo pass with exact-byte assertions.
- [ ] A concurrent timer fires on schedule during a pending `sock_recv`.
- [ ] Spurious-wakeup and partial-send paths are tested.

## Hints

- Test command: `uv run pytest tests/test_sock_io.py`. An echo over a `socketpair()` should have exact bytes on both sides.
- A blocking `recv` freezes the whole loop, so assert non-blocking mode in the primitives.
- Handle spurious wakeups with `try/except BlockingIOError`.
- Unregister before resolving to avoid stale descriptors after reuse.
- `sock_recv` returns up to `n` bytes, so tests must frame accordingly.
