# Stage 5: Comments

## Objective

Next, ignore input from an unquoted `#` to end of line, so scripts can carry comments. The deliverable is that comment text never reaches the argument vector, while a `#` inside a quoted string (Stage 14) stays literal. Focus areas: lexer correctness and forward-compatibility with quoting.

## Steps

- Confirm Stage 2 tokenizes.
- Decide where comment handling belongs: in the scanner or as a post-pass over the line.
- Define the behavior for a line that is only a comment, and for a comment following arguments.
- Confirm the comment marker is a token boundary (the preceding token still ends correctly).
- Note the eventual interaction with `#` inside quotes and shell parameter expansion, and record the decision.

## Design Questions

- A `#` only starts a comment when it is not inside quotes — does putting it in `consume_token` paint you into a corner later?

## Tests

- [ ] Comments are dropped before execution.
- [ ] Lines of only comments do not error or spawn processes.
- [ ] The quoted-`#` case is acknowledged (implemented in Stage 14).

## Hints

- Test command: `shell/tests/run.sh`. `echo hi # trailing` should run `echo hi`; a whole-line comment is a no-op; `#` glued to a word (e.g. `a#b`) follows the documented rule; the shell remains interactive after a comment.
- Consider `#` at position 0, after whitespace, and mid-token.
- A comment inside a quoted argument is deferred; a comment line under `set -x`-style tracing is out of scope; `\#` escaping is deferred to Stage 14.
- See how [bash `parse.y`](https://github.com/bminor/bash) treats comment tokens. Which stage-2 decisions make quotes easy or hard?
