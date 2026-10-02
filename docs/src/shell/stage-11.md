# Stage 11: Job control (`SIGTSTP`, `jobs`, `fg`, `bg`)

## Objective

Manage a table of active jobs with IDs, PIDs, and states, and move them between foreground and background. `Ctrl+Z` must suspend the foreground job, `jobs` must list them, and `fg`/`bg` must resume them. The deliverable is real job control with process groups and terminal ownership. Focus areas: process groups, terminal control, and job state machines.

## Steps

- Confirm Stage 9 handles signals and reaping.
- Study [tcsetpgrp(3)](https://man7.org/linux/man-pages/man3/tcsetpgrp.3.html), [setpgid(2)](https://man7.org/linux/man-pages/man2/setpgid.2.html), [WUNTRACED/WCONTINUED](https://man7.org/linux/man-pages/man2/waitpid.2.html), and [SIGTSTP/SIGCONT](https://man7.org/linux/man-pages/man7/signal.7.html).
- Define the `Job` type: id, process-group id, state (running/stopped), command text, and its processes.
- Decide the job table lifecycle: insert on launch, update on stop/continue, remove on reap, and recycle job numbers.
- Define the builtins: `jobs` (format, `+`/`-` current job markers), `fg` (move job to foreground, wait), and `bg` (continue in background).
- Define how `SIGTSTP` is delivered and how the shell marks the job stopped (`waitpid` with `WUNTRACED`).
- Decide what happens to jobs on shell exit (send `SIGHUP`? warn?).

## Design Questions

- One job per pipeline, or per process? Which correctly maps to process groups?
- What does the shell do with terminal control when handing over to `fg`, and how does it take it back?
- What state transitions must be handled — running→stopped, stopped→running, and completion while stopped?

## Tests

- [ ] `jobs` lists jobs with ids, states, and commands.
- [ ] `fg`/`bg` move jobs between states correctly.
- [ ] Terminal control is taken and released around `fg`.

## Hints

- Test command: `shell/tests/run.sh`. A foreground `sleep` stopped with `SIGTSTP` appears in `jobs` as stopped; `bg %1` marks it running; `fg %1` brings it to the foreground and blocks; the job number is recycled after it finishes; a child started in the background can't read the terminal (document `SIGTTIN` behavior).
- Watch for `fg`/`bg` on a nonexistent job, a job that finishes while stopped, terminal modes saved/restored around `fg`, a background job reading stdin getting `SIGTTIN`, and job number reuse confusion.
- Study [bash `jobs.c`](https://github.com/bminor/bash) and its process-group handling. Why does the shell put each pipeline into its own process group?
