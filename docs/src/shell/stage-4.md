# Stage 4: State-changing builtins (`exit`, `cd`, `pwd`)

## Objective

Now add builtins that must run in the shell process itself because they change its state or terminate it. `exit` ends the loop, `cd` changes the process working directory, and `pwd` reports it. The deliverable is a dispatch layer that picks builtin-vs-external before forking. Focus areas: shell state, environment changes, and dispatch architecture.

## Steps

- Confirm Stage 3 runs external commands.
- Decide the dispatch model: a table of `{name, fn}` entries checked before `exec`, or an if/else chain.
- Define the builtin interface (arg vector in, status out) and register `exit`, `cd`, `pwd`.
- For `cd`, study [chdir(2)](https://man7.org/linux/man-pages/man2/chdir.2.html) and decide how absolute, relative, and home (`~` / no-arg) targets are handled.
- For `exit`, decide the accepted argument forms and default status.
- For `pwd`, decide whether to call `getcwd(3)` or print `$PWD`.

## Design Questions

- Where does the builtin check live so both foreground and (later) pipeline/background paths share it?
- What should `cd` return on failure, and should it update `PWD`/`OLDPWD`?
- Which is correct after a symlink change, and why do real shells track `PWD`?

## Tests

- [ ] `cd` changes the directory for subsequent commands (proving it did not fork).
- [ ] `pwd` reflects the change.
- [ ] `exit N` sets the shell's exit status.

## Hints

- Test command: `shell/tests/run.sh`. `pwd` prints the current directory; `cd /tmp` then `pwd` prints `/tmp`; `cd` to a bad path errors and leaves the directory unchanged; `exit 7` leaves the shell with status 7.
- A builtin run in a child would not affect the parent's `cwd` — that's a classic bug.
- Consider `cd` failure that must not report success, `pwd` after deleting the current directory, and `exit` mid-pipeline.
- Look at how [dash](http://git.kernel.org/pub/scm/utils/dash/dash.git) separates builtins from the exec path. Why do only state-changing builtins need in-process execution?
