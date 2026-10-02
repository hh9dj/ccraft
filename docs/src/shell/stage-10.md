# Stage 10: More builtins (`echo`, `env`, `setenv`, `unsetenv`)

## Objective

Now add the utility builtins and the shell's own environment management. `echo` prints its arguments, `env` lists the current environment, and `setenv`/`unsetenv` mutate it. The deliverable is a builtin set that reads and writes the shell's environment so children inherit the changes. Focus areas: environment variables and the process environment block.

## Steps

- Confirm Stage 4's builtin dispatch works.
- Decide the environment representation: the inherited `environ`/`getenv`/`setenv` from libc, or a shell-owned table.
- Define `echo` semantics: argument order, separator, and handling of `-n`/escapes (document what you support).
- Define `env` output format and ordering; decide whether it reflects the current environment after `setenv`/`unsetenv`.
- Define `setenv NAME VALUE` and `unsetenv NAME` argument validation and error status.
- Decide whether these run in-process (they change inherited environment) and how that interacts with pipelines and redirection.

## Design Questions

- If `setenv` is a builtin mutating the shell, will `fork`+`exec` children see the change automatically? Why or why not?
- Does `echo` need to expand parameters now, or only print literals until Stage 14?
- What is the correct error when the name is missing or invalid?

## Tests

- [ ] `echo` and `env` produce documented output.
- [ ] `setenv`/`unsetenv` persist in the shell's environment.
- [ ] Changes are visible to subsequently exec'd children.

## Hints

- Test command: `shell/tests/run.sh`. `echo a b c` prints `a b c`; `env` contains a variable set by `setenv FOO bar`; `env` omits it after `unsetenv FOO`; a child command (`sh -c 'echo $FOO'`) sees the exported variable; invalid `setenv` usage errors.
- Watch for `setenv` with an empty value vs. unset, names with `=`, ordering/format of `env`, memory owned by `environ`, and builtins in a pipeline where the child's environment change is discarded.
- Study how [dash](http://git.kernel.org/pub/scm/utils/dash/dash.git) maintains variables. Why do external commands inherit the environment "for free" after an in-process `setenv`?
