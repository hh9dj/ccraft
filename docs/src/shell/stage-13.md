# Stage 13: Error handling

## Objective

Make failures legible and non-fatal. The shell must report `command not found`, `permission denied`, and `syntax error` clearly, on the right stream, with a nonzero status, while continuing to run. The deliverable is a consistent error-reporting path across parsing, resolution, and execution. Focus areas: `errno` handling, diagnostics, and exit status conventions.

## Steps

- Confirm Stages 3–6 execute commands and redirection.
- Decide the diagnostic format (e.g. `shell: <command>: <message>`) and the stream (stderr).
- Enumerate the failure classes to distinguish: command not found, not executable / permission denied, redirection open failure, parse/syntax error, fork failure, and interrupted syscalls (`EINTR`).
- Define a parse-error path: when input is malformed (e.g. trailing `|`, unterminated quote), report and return to the prompt without forking.
- Ensure errors from a forked child are reported by the child and reflected in the shell's status.
- Confirm the shell never exits on a recoverable error (except `exit`/EOF).

## Design Questions

- Should diagnostics use `perror`/`strerror(errno)` or hand-written messages? When is each appropriate?
- Which exit status does each class map to, and is there a single helper that emits them?

## Tests

- [ ] The three named error classes each produce the documented message and status.
- [ ] Errors go to stderr and do not terminate the shell.
- [ ] Diagnostics include the offending command name.

## Hints

- Test command: `shell/tests/run.sh`. An unknown command prints a `command not found` diagnostic to stderr with nonzero status; executing a non-executable file reports `permission denied`; malformed input reports `syntax error` and returns to the prompt; `EINTR`-prone syscalls retry rather than abort.
- Watch for `errno` clobbered before it's read, a child that dies before `exec`, errors inside a pipeline, reporting from a signal context (unsafe), and error text for empty input.
- Compare the diagnostics in [mrsh](https://github.com/emersion/mrsh) and [busybox ash](https://github.com/mirror/busybox). Why should a parse error be detected before any `fork`?
