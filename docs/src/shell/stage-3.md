# Stage 3: External command execution and `PATH`

## Objective

Time to actually run programs: `fork`, `execvp` the parsed command, and wait for it to finish. A bare name must resolve through `PATH`; an unknown name must produce a "command not found" error rather than crashing. Focus areas: process creation, `exec` family semantics, and `PATH` resolution.

## Steps

- Confirm Stage 2 produces an argument vector.
- Study [fork(2)](https://man7.org/linux/man-pages/man2/fork.2.html), [execvp(3)](https://man7.org/linux/man-pages/man3/execvp.3.html), and [waitpid(2)](https://man7.org/linux/man-pages/man2/waitpid.2.html).
- Define the execution path in `shell/lib/commands.c`: `void execute_cmd(Command *cmd)`.
- Decide how `PATH` lookup happens: delegate to `execvp`, or resolve manually with `access(2)` first. Relate this to the `type` builtin you may add later.
- Define the parent's wait behavior and the child's exit-status handling.
- Decide how the shell avoids forking for builtins (builtins are Stage 4; note the shared dispatch point now).

## Design Questions

- Who forks — the executor or the caller — and what does the child do on `exec` failure?
- What exit code should the shell report when the command does not exist?
- What does a signal-terminated child report?

## Tests

- [ ] External commands execute and their output reaches the terminal.
- [ ] Unknown commands produce an error and do not terminate the shell.
- [ ] Exit status of the child is observable by the shell.

## Hints

- Test command: `shell/tests/run.sh`. `/bin/echo hi` prints `hi`; `ls` with an argument lists the expected file; a nonexistent command prints an error to stderr and the shell keeps running; the reported status reflects a non-zero child exit.
- If `execvp` fails in the child, the child must `_exit` — not `return`, which would double-run the loop.
- Consider `PATH` empty or unset, `fork` failure, zombie children if `wait` is skipped, and a command containing `/` that bypasses `PATH`.
- Compare with the exec path in [mrsh](https://github.com/emersion/mrsh) and [xv6 `sh.c`](https://github.com/mit-pdos/xv6-riscv/blob/riscv/user/sh.c). Why must the child never return from `exec` failure into the shell's loop?
