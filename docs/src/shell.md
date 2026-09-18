# Shell

Building a shell in C.

## Guide

### Basic Functionality

1. **The Read-Eval-Print Loop (REPL):**
    - [x] Display a prompt such as `chell> `.
    - [x] Read user input from standard input.
    - [x] Parse the input into a list of commands and arguments.
2. **Command Execution:**
    - [x] Run external commands.
    - [x] Run built-in commands that need to change the shell's own state, such as `exit` and `cd`.
3. **Comments:**
    - [x] Ignore comments.
4. **Basic I/O Redirection (`<`, `>`):**
    - [x] Implement standard input redirection (`< filename`) and standard output redirection (`> filename`).

### Advanced Functionality

1. **Background Processes (`&`):**
    - Allow commands to run in the background (for example, `sleep 5 &`).
2. **Pipelines (`|`):**
    - Implement command piping (for example, `ls -l | grep .c`).
3. **Signal Handling:**
    - Implement handlers for `SIGINT` (Ctrl+C) and `SIGCHLD`.
4. **More Built-in Commands:**
    - Implement `echo`, `env`, `setenv`, and `unsetenv`. The last two manage the shell's environment variables.
5. **More Signals:**
    - Implement `SIGTSTP` (Ctrl+Z) to suspend foreground processes.
    - Keep a list of active jobs, including each process, its state, and its job ID.
    - Implement the `fg` (foreground) and `bg` (background) commands to move jobs between states.
6. **Command History:**
    - Store previously executed commands.
    - Navigate history with the arrow keys.
7. **Error Handling:**
    - Improve error messages such as `command not found`, `permission denied`, and `syntax error`.
8. **String Handling:**
    - Handle tokenization of quoted strings in user input.

## References

- [CodeCrafters build-your-own-x, shell section](https://github.com/codecrafters-io/build-your-own-x?tab=readme-ov-file#build-your-own-shell)
