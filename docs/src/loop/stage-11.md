# Stage 11: Echo server end-to-end

## Objective

Let's prove the runtime on a real workload: a single-threaded TCP echo server with one task per connection that serves many clients concurrently. A slow client should suspend only its own task. The deliverable is end-to-end evidence that the scheduler, timers, selector, and tasks compose correctly under load and file-descriptor lifecycle pressure. Focus areas: concurrent servers without threads, and file-descriptor lifecycle.

## Steps

- Confirm Stage 10 is done.
- Here's the model: an accept loop spawns a task per connection, and interleaving happens at `await` points. A slow client suspends only its own task, which is parked on the selector. Read [Single-threaded non-blocking server](https://prodsens.live/2025/05/12/building-your-own-web-server-part-4-single-threaded-non-blocking-server/) and [Asyncio Demystified](https://dev.indooroutdoor.io/asyncio-demystified-rebuilding-it-from-scratch-one-yield-at-a-time).
- Define `serve_forever(loop, listener)` · `handle_client(loop, conn)`.
- Set up the listener with `SO_REUSEADDR`, then `bind`, `listen(>=100)`, and non-blocking mode.
- Ensure unregister-and-close on every exit path; a `finally` block is non-negotiable. When `recv` returns `b""`, break instead of re-registering, and catch `ConnectionResetError` from killed clients.
- Design teardown: stop the loop, close the listener, and join the thread with a timeout.

## Design Questions

- Who owns closing the connection when a task finishes or errors?
- How will you detect a file-descriptor leak?

## Tests

- [ ] N concurrent distinct echoes pass, slow clients do not block fast ones, and the connection count returns to 0.
- [ ] File-descriptor count is stable across runs, and an RST-killed client does not wedge the server.
- [ ] Wall time demonstrates concurrency.

## Hints

- Test command: `uv run pytest tests/test_echo_server.py`. N threaded clients with distinct payloads should each receive their own bytes back.
- Unregister and close on every exit path — a `finally` block is non-negotiable.
- When `recv` returns `b""`, break instead of re-registering; catch `ConnectionResetError`.
- Set `SO_REUSEADDR`, `bind`, `listen(>=100)`, and non-blocking mode.
- Why start with a few clients before scaling to 50 or more?
