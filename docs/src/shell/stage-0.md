# Stage 0: Setup, build & test harness

## Objective

Before writing any shell behavior, make the project buildable and testable with one command each, so every later stage is verified the same way. There's no new shell behavior here — the deliverable is a repeatable compile plus a behavior harness that drives the binary with piped input and checks stdout, stderr, and exit codes. Focus areas: toolchain discipline and test-driven stage progression.

## Steps

- Confirm a C compiler (`cc`/`gcc`/`clang`) is available and read the existing layout under `shell/`.
- Decide the build command and write it down. It must compile `shell/main.c` plus the library translation units under `shell/lib/` (with header include path `shell/lib`).
- Decide the test runner. There's no harness today, so define one: a shell script `shell/tests/run.sh` that builds, then feeds input to `shell/cshell` and compares output and exit status against recorded expectations.
- Define how a case declares a passing result and how the script reports a summary; make it exit non-zero on the first failure.
- Keep the binary and any fixtures out of version control (`.gitignore`).
- Optionally wrap both commands in a `just` recipe so they match the repo's `just docs` convention.

## Design Questions

- Is there a build system (Make/CMake/just) yet, or only a bare `cc` invocation?
- What does a single test case look like — stdin, argv, expected stdout, expected stderr, expected exit code?
- Golden files, in-script heredocs, or a table? Which makes adding a case per stage cheapest?
- Should the recipe be `just shell build` / `just shell test`, or two top-level recipes?

## Tests

- [ ] The binary builds cleanly with the documented command.
- [ ] `shell/tests/run.sh` exists, runs, and fails on a deliberately wrong expectation.
- [ ] Generated binaries/fixtures are git-ignored.

## Hints

- Test commands: `cc -Wall -Wextra -I shell/lib shell/main.c shell/lib/*.c -o shell/cshell` and `shell/tests/run.sh`. The compiler must emit no warnings with `-Wall -Wextra`, and the harness must start, run at least one smoke case, and report a summary.
- Headers include each other by bare name (e.g. `"data_structures.h"`), so the include path matters; a missing `-I` shows up as a cascade of "file not found".
- Compiling `lib/*.c` from the repo root versus `shell/` changes relative paths.
- [CodeCrafters build-your-own-shell](https://github.com/codecrafters-io/build-your-own-shell) splits its early stages the same way. What's the smallest possible smoke case that proves the harness works?
