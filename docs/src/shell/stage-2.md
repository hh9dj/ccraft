# Stage 2: Tokenize into a command and arguments

## Objective

Now split a raw input line into a command name, an argument vector, and the shell's own structural fields (input/output file placeholders). The deliverable is a parsed representation the executor can consume without touching the raw string. Focus areas: lexical scanning and data-structure design.

## Steps

- Confirm Stage 1 reads and loops on lines.
- Decide the parsed shape. The existing `Command` struct in `shell/lib/commands.h` carries `args`, `input`, and `output`; decide whether that shape survives the later stages (pipelines, backgrounding) or needs a redesign now.
- Decide the scanner's separators and what a "token" is; the existing `consume_token` stops on whitespace and `#`.
- Define the `StrArray` growth contract (append, capacity) in `shell/lib/data_structures.c` and confirm ownership and freeing rules.
- Decide how empty input maps to a command with zero args, and how that flows back to the loop.
- Define the parser's public interface and keep it stable: `Command *tokenize(char line[])`.

## Design Questions

- Should `Command` be one command or a pipeline of commands? Which choice avoids a rewrite at Stage 8?
- What is the minimal token model that still admits quotes later (Stage 14)?
- Does `tokenize` own the returned memory, and who frees it?

## Tests

- [ ] Tokenization preserves argument order and drops empty tokens.
- [ ] Zero-argument input produces a valid empty-argument command.
- [ ] No leaks under AddressSanitizer.

## Hints

- Test command: `shell/tests/run.sh`. `ls -l` should yield two args in order; extra spaces/tabs shouldn't create empty args; a trailing newline is stripped; a command with no args yields one arg; ownership/free is exercised under `-fsanitize=address` without leaks.
- Watch for leading, multiple, and trailing whitespace; tabs vs spaces; NUL termination of each token.
- Watch for reallocating the `StrArray` while pointers into it are held, and freeing the line twice.
- Read the tokenizer in [xv6 `sh.c`](https://github.com/mit-pdos/xv6-riscv/blob/riscv/user/sh.c). If quotes are coming, is a "split on whitespace" function the right foundation, or too narrow?
