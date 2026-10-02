# Stage 9: Signal handling (`SIGINT`, `SIGCHLD`)

## Objective

Make the shell survive terminal signals correctly and reap children promptly. `Ctrl+C` must interrupt the running foreground job, not the shell itself; `SIGCHLD` must let the shell notice finished children without polling. Focus areas: signal disposition, process groups, and asynchronous reaping.

## Steps

- Confirm Stages 7 and 8 launch foreground, background, and pipeline processes.
- Study [signal(7)](https://man7.org/linux/man-pages/man7/signal.7.html), [sigaction(2)](https://man7.org/linux/man-pages/man2/sigaction.2.html), and [waitpid(2)](https://man7.org/linux/man-pages/man2/waitpid.2.html) with `WNOHANG`.
- Decide the disposition for `SIGINT` in the shell (ignore) versus in children (default), and where that's set relative to `fork`.
- Decide the `SIGCHLD` handler's job. Keep async-signal-safety in mind: the handler may only set a flag, not call `printf`/`malloc`.
- Decide when the shell reaps: at the top of each prompt iteration, or in the handler.
- Define what happens to a background job's completion notification (this feeds Stage 11).

## Design Questions

- If the shell ignores `SIGINT`, how does the foreground child still receive it from the terminal?
- Flag-and-reap-later, or `waitpid` inside the handler? Which is safe and why?

## Tests

- [ ] `Ctrl+C` interrupts the foreground job, not the shell.
- [ ] Finished children are reaped; no zombies accumulate.
- [ ] The handler avoids non-async-signal-safe calls.

## Hints

- Test command: `shell/tests/run.sh`. Sending `SIGINT` to a running foreground `sleep` should return the prompt instead of killing the shell; the child's exit status reflects `SIGINT`; a background child that finishes gets reaped (no zombies) before the next prompt; a signal handler is installed for `SIGCHLD`.
- Watch for `EINTR` from `read`/`wait` after a signal, multiple children finishing at once, reaping a stopped child with `WUNTRACED` (Stage 11), `SIGINT` delivered to the whole foreground process group, and only setting `volatile sig_atomic_t` in the handler.
- Read the signal handling in [bash `jobs.c`](https://github.com/bminor/bash). Why is `printf` inside a signal handler undefined behavior?
