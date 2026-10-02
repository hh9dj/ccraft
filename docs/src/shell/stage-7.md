# Stage 7: Background processes (`&`)

## Objective

Run a command without waiting when it ends in `&`, printing a job identifier and returning the prompt immediately. The deliverable is a non-blocking launch path plus awareness that the child is still alive. Focus areas: process lifecycle without `wait` and the groundwork for job lists.

## Steps

- Confirm Stages 3 and 6 execute and redirect.
- Decide how the parser marks a command as backgrounded; add that field to the parsed shape.
- Define the launch path: fork and exec but skip `waitpid`.
- Decide the job-numbering scheme and where the number comes from; note it must be recycled later (Stage 11).
- Decide the immediate output: status message, PID, job id, and whether it goes to stdout or stderr.
- Keep the shell from exiting while background children still hold the terminal, and document the choice.

## Design Questions

- Is `&` a terminator of the command or a token within the argument vector?
- What happens to the child if the shell never reaps it — and how does that lead into `SIGCHLD` at Stage 9?

## Tests

- [ ] Backgrounded commands do not block the prompt.
- [ ] A job identifier is assigned and reported.
- [ ] Later foreground commands continue to work.

## Hints

- Test command: `shell/tests/run.sh`. `sleep 1 &` should return the prompt immediately (wall time well under 1s); the reported job id/PID is present; a foreground command after it still works; the background process eventually finishes without leaving the shell wedged.
- Watch for pid reuse, zombie accumulation, `&` with redirection, a background job that writes to the terminal and interleaves with the prompt, and reaping before the next prompt (Stage 9).
- Read the job machinery in [bash `jobs.c`](https://github.com/bminor/bash) and [dash](http://git.kernel.org/pub/scm/utils/dash/dash.git). Why does a job number differ from a PID?
