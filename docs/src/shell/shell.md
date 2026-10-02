# Project: Shell

In this project you'll build a minimal POSIX-style command interpreter in C, starting from a bare prompt and growing it into a real shell with redirection, pipelines, and job control.

- **Language:** C
- **Focus areas:** Operating Systems (processes, system calls, I/O redirection, signals, environment variables)
- **Build/test command:** `cc -Wall -Wextra -I shell/lib shell/main.c shell/lib/*.c -o shell/cshell` then `./shell/cshell`; behavior tests run via `shell/tests/run.sh`

## Milestones

1. **REPL & execution core** (Stages 0–6). Build/test harness, prompt and read loop, tokenizer, external commands, state-changing builtins, comments, and basic `<`/`>` redirection.
2. **Processes, signals & plugins** (Stages 7–11). Background processes, pipelines, `SIGINT`/`SIGCHLD`, more builtins, and full job control with `SIGTSTP`/`jobs`/`fg`/`bg`.
3. **UX & language features** (Stages 12–14). Command history, error reporting, and quoted-string tokenization.

## Similar Projects & Libraries

Read these for inspiration; don't copy them. Start with the smaller shells and work up to bash once the ideas feel familiar.

- [bash](https://github.com/bminor/bash) (C) — the reference POSIX shell. Study `jobs.c` (job control), `execute_cmd.c` (redirection and pipelines), and `parse.y`.
- [dash](http://git.kernel.org/pub/scm/utils/dash/dash.git) (C) — small, POSIX-only. A good model for a compact parser and executor.
- [mrsh](https://github.com/emersion/mrsh) (C) — a readable, modern POSIX shell; study its AST and expansion layers.
- [xv6 `sh.c`](https://github.com/mit-pdos/xv6-riscv/blob/riscv/user/sh.c) (C) — a tiny, self-contained shell: the best first read for parsing/exec/redirection.
- [busybox ash](https://github.com/mirror/busybox) (C) — one-file shell variant; study how it keeps everything in a single translation unit.
- [Oil Shell (oils)](https://github.com/oils-for-unix/oils) (Python/C++) — heavily documented; useful for understanding shell parsing edge cases.
- [GNU coreutils](https://github.com/coreutils/coreutils) (C) — the external commands your shell will exec.
- [Stephen Brennan, "Write a Shell in C"](https://brennan.io/2015/01/16/write-a-shell-in-c/) — tutorial walkthrough of the REPL/exec core.
- [CodeCrafters build-your-own-shell](https://github.com/codecrafters-io/build-your-own-shell) — stage definitions for a guided progression.

## Contents

> Checked stages are implemented in `shell/`. Stage 0 (the `shell/tests/run.sh`
> harness) is not written yet, so the per-stage acceptance boxes remain unchecked
> until it can verify them. Stage 4 is unchecked because `pwd` is not implemented.

- [ ] [Stage 0: Setup, build & test harness](./stage-0.md)
- [x] [Stage 1: Prompt and read loop](./stage-1.md)
- [x] [Stage 2: Tokenize into a command and arguments](./stage-2.md)
- [x] [Stage 3: External command execution and `PATH`](./stage-3.md)
- [ ] [Stage 4: State-changing builtins (`exit`, `cd`, `pwd`)](./stage-4.md)
- [x] [Stage 5: Comments](./stage-5.md)
- [x] [Stage 6: Basic I/O redirection (`<`, `>`)](./stage-6.md)
- [ ] [Stage 7: Background processes (`&`)](./stage-7.md)
- [ ] [Stage 8: Pipelines (`|`)](./stage-8.md)
- [ ] [Stage 9: Signal handling (`SIGINT`, `SIGCHLD`)](./stage-9.md)
- [ ] [Stage 10: More builtins (`echo`, `env`, `setenv`, `unsetenv`)](./stage-10.md)
- [ ] [Stage 11: Job control (`SIGTSTP`, `jobs`, `fg`, `bg`)](./stage-11.md)
- [ ] [Stage 12: Command history](./stage-12.md)
- [ ] [Stage 13: Error handling](./stage-13.md)
- [ ] [Stage 14: Quoted-string tokenization](./stage-14.md)

## Acceptance

By the end you'll have a single-binary POSIX-style shell that runs a REPL, tokenizes commands and quoted arguments, resolves external programs via `PATH`, implements state-changing and utility builtins, supports `<`/`>`/`|` and background execution, and manages foreground jobs and signals with `jobs`/`fg`/`bg` — all driven by the `shell/tests/run.sh` harness, with no runtime dependencies beyond libc.
