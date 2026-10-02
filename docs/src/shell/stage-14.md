# Stage 14: Quoted-string tokenization

## Objective

Finally, handle quoting so arguments can contain spaces and special characters. Single quotes preserve everything literally, double quotes allow expansion while grouping, and backslashes escape the next character (with rules differing inside each quote type). The deliverable is a tokenizer that produces the same words a POSIX shell would for these cases. Focus areas: shell lexical rules and quote-state machines.

## Steps

- Confirm Stages 2 and 5 tokenize and strip comments.
- Study the POSIX quoting rules and how [bash `parse.y`](https://github.com/bminor/bash) or [mrsh](https://github.com/emersion/mrsh) implement them.
- Define the quote states and transition rules: inside single quotes, inside double quotes, and unquoted. Decide how a quote is represented once removed (concatenation of segments into one word).
- Define backslash semantics: escaping outside quotes, literal backslash inside single quotes, and its reduced role inside double quotes.
- Decide whether expansion (variables) happens now inside double quotes or is deferred; document the boundary.
- Update comment handling so `#` inside quotes is literal.
- Update error handling for unterminated quotes.

## Design Questions

- Is a tokenizer that "splits on whitespace" sufficient, or must it track quote state while scanning? Which Stage 2 choices need revisiting?
- How do adjacent quoted/unquoted fragments compose into a single argument (e.g. `a"b c"d`)?
- Which characters are special inside double quotes, and which are literal?

## Tests

- [ ] Single and double quotes group words and strip the quotes.
- [ ] Backslash escaping matches the documented rules per quote context.
- [ ] Adjacent fragments concatenate into one argument; unterminated quotes error.

## Hints

- Test command: `shell/tests/run.sh`. `echo 'a b'` prints one argument `a b`; `echo "a b"` likewise; `echo a"b c"d` prints `ab cd`; `echo 'a"b'` keeps the double quote literal; a backslash escapes the next char outside quotes; `echo "a\"b"` behaves per the documented double-quote rule; an unterminated quote reports a syntax error.
- Watch for an empty quoted string (`''`) as an argument, quotes in the middle of a word, `\` at end of input, `#` inside quotes, nested quotes of the other type, newlines inside quotes, and quoting around redirection operators.
- Compare against `sh -c` output for each case as a differential check. Why must quote removal and field splitting be considered as separate concerns?
