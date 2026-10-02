# Stage 8: Pipelines (`|`)

## Objective

Connect two or more commands so stdout of one becomes stdin of the next, with all stages running concurrently. The deliverable is a pipeline data model plus process/pipe orchestration that closes descriptors correctly in parent and children. Focus areas: `pipe(2)`, descriptor hygiene, and concurrent process management.

## Steps

- Confirm Stages 3, 6, and 7 work, and note that `Command` currently models a single command.
- Study [pipe(2)](https://man7.org/linux/man-pages/man2/pipe.2.html) and the standard pipe+dup2 idiom.
- Redefine the parsed shape to hold an ordered list of stages, each with its own args and redirections.
- Define the pipeline executor: create N-1 pipes, fork N children, assign each child its input/output ends, and close every unused end.
- Decide wait behavior: wait for all stages, and what status the pipeline reports (first, last, or all?).
- Decide how builtins inside a pipeline are handled, since an in-process builtin can't be a pipe stage without some care.

## Design Questions

- Does `Command` become a list of stages, or do you wrap it in a `Pipeline`? Which keeps Stage 2's parser usable?
- How do `<`/`>` bind relative to `|` priority?
- Where is the single place descriptors are closed, so no fd leaks across a long pipeline?
- Does a piped builtin run in a forked child, and what state changes are then lost?

## Tests

- [ ] Two- and three-stage pipelines produce correct output.
- [ ] No descriptor leaks after many pipelines.
- [ ] The pipeline's exit status follows the documented choice.

## Hints

- Test command: `shell/tests/run.sh`. `ls | wc -l` produces the count; `printf 'a\nb\n' | grep a` filters correctly; a three-stage pipeline works; the shell doesn't hang or leak fds (run with `-fsanitize=address` and/or check `/proc/self/fd`); a failed middle stage doesn't wedge.
- Forgetting to close the write end in readers causes a hang, as does closing the wrong end.
- Watch for `SIGPIPE`/`EPIPE`, `head` closing early, a builtin as a stage, and a single stage with no pipe.
- Compare the pipeline loop in [xv6 `sh.c`](https://github.com/mit-pdos/xv6-riscv/blob/riscv/user/sh.c) and [mrsh](https://github.com/emersion/mrsh). Why does each process need to close every pipe end it doesn't use?
