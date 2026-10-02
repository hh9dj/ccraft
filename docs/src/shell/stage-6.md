# Stage 6: Basic I/O redirection (`<`, `>`)

## Objective

Now redirect a command's standard input from a file with `<` and its standard output to a file with `>`. The deliverable is that redirection is applied in the child between `fork` and `exec`, so it doesn't disturb the shell's own descriptors. Focus areas: file descriptors, `dup2`, and open/close lifecycle.

## Steps

- Confirm Stages 3 and 4 execute commands and builtins.
- Study [open(2)](https://man7.org/linux/man-pages/man2/open.2.html), [dup2(2)](https://man7.org/linux/man-pages/man2/dup2.2.html), and [close(2)](https://man7.org/linux/man-pages/man2/close.2.html).
- Confirm the parser already records `input`/`output` on `Command` (Stage 2) and decide whether `>` truncates and what creation mode it uses.
- Define the redirection application step and the error path when the file cannot be opened.
- Decide precedence when both `<` and `>` appear, and what happens with duplicates.
- Handle the builtin-vs-external question: do redirected builtins also need the child path? What does that imply for Stage 4's in-process rule?

## Design Questions

- Where in the fork/exec sequence must redirection happen so the parent's fds stay clean?
- What exit status and message should a failed open produce, and does it happen in parent or child?

## Tests

- [ ] `>` truncates/creates and `>` output is captured exactly.
- [ ] `<` feeds the file to the command's stdin.
- [ ] The shell's own streams survive a redirected command.

## Hints

- Test command: `shell/tests/run.sh`. `echo hi > out` creates `out` containing `hi`; `cat < in` reads `in`; `cat < in > out` works; a missing input file errors without crashing; the shell's own stdout is unaffected after a redirected command.
- Opening the file before `fork` leaks an fd on `fork` failure.
- Watch for forgetting to `close` the original dup'd fd, mode bits for created files (umask), redirecting a builtin that runs in-process, and `>` to a path without permission.
- The redirection code in [Brennan's tutorial](https://brennan.io/2015/01/16/write-a-shell-in-c/) and [mrsh](https://github.com/emersion/mrsh) is a good comparison. Why must redirection not run in the parent for external commands?
