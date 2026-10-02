# Stage 12: Command history

## Objective

Remember executed commands and let the user recall and edit them. The deliverable is an in-memory history buffer with navigation, plus persistence across sessions. Focus areas: terminal line editing (raw mode) and history storage.

## Steps

- Confirm Stage 1's read loop.
- Decide history storage: a bounded array of strings, a ring buffer, or a file-backed list.
- Decide what gets recorded — every submitted line, non-empty only, duplicates collapsed? Document the rule.
- Study terminal raw mode via [termios(3)](https://man7.org/linux/man-pages/man3/termios.3.html) for up/down arrow escape sequences.
- Define the history interface: add, previous, next, and search (up/down traversal semantics).
- Decide persistence: where the history file lives, its format, and when it's written (on `exit`, per line?).
- Restore the terminal mode on every exit path, including signals.

## Design Questions

- What is the cap, and what happens when it is exceeded?
- Do you implement line editing yourself (raw mode) or defer to a library like readline? What does each cost in transparency vs. control?
- Should history be shared between concurrent shells, and what corruptions can result if so?

## Tests

- [ ] History records submitted commands per the documented rule.
- [ ] Navigation moves through history in order and stops at the boundaries.
- [ ] History persists across sessions and the terminal is restored on exit.

## Hints

- Test command: `shell/tests/run.sh`. Submitted commands appear in the in-memory list; up/down traversal returns prior/next entries in order; the cap is enforced; persistence writes and reloads across two shell sessions; the terminal mode is restored after the shell exits.
- Watch for EOF during raw-mode read, a signal arriving while in raw mode leaving the terminal unusable (restore in a handler or `atexit`), very long lines, editing in the middle of a recalled line, and concurrent writers to the history file.
- Look at how [bash](https://github.com/bminor/bash) separates readline from the shell. What's the smallest line editor that still supports the requested arrow-key navigation?
