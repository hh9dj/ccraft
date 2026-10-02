# Stage 1: Prompt and read loop

## Objective

Turn the program into an interactive loop: print a prompt, read one line of input, and repeat. No command is executed yet beyond echoing or handling the raw line — the deliverable is the outer loop and its termination behavior. Focus areas: REPL structure, streams, and EOF handling.

## Steps

- Confirm Stage 0's build and harness work.
- Decide the prompt format and where it's written. The existing `prompt()` in `shell/main.c` prints the working directory; decide whether that stays.
- Decide how a line is read — the existing `read_line()` uses `getline` — and what should happen on end-of-file (Ctrl+D) versus a read error.
- Establish the loop's shape: prompt, read, process, repeat, with the loop exiting only on EOF or `exit`.
- Confirm the loop flushes output so the prompt appears before input is read.
- Make the loop ignore or handle blank lines without crashing.

## Design Questions

- Is the prompt written to stdout or stderr, and does that matter for piping?
- Should EOF exit cleanly, and with what exit code?

## Tests

- [ ] A scripted stdin run exits 0 at EOF.
- [ ] Blank input lines are handled without a crash.
- [ ] The prompt appears in the expected stream before processing.

## Hints

- Test command: `shell/tests/run.sh`. Piping an empty stdin should print the prompt once and exit 0; piping one line should print prompt-then-handling; a blank line shouldn't crash; EOF exits.
- `getline` returns `-1` at EOF and sets `feof`, which is distinct from a genuine read error.
- A missing newline at EOF still yields a usable line, and redirecting stdout changes prompt visibility.
- Study the loop in [xv6 `sh.c`](https://github.com/mit-pdos/xv6-riscv/blob/riscv/user/sh.c) and [Brennan's walkthrough](https://brennan.io/2015/01/16/write-a-shell-in-c/). Does the prompt belong on stderr for scriptability?
