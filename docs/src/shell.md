# Shell

Building a shell in C.

## Guide

### The Basic Functionalities

1.  **The Read-Eval-Print Loop (REPL):**
    - [x] Display a prompt like `chell> `.
    - [x] Read user input from standard input.
    - [x] Parse the input into a list of cmd - args
2.  **Command Execution:**
    - [x] Handle external commands calls
    - [x] Handle built-in commands (to manage shell process state) : exit - cd.
3.  **Comments**
    - [x] Ignore comments
4.  **Basic I/O Redirection (`<`, `>`):**
    - [x] Implement standard input redirection (`< filename`) and standard output redirection (`> filename`).

### Advanced Functionality

1.  **Background Processes (`&`):**
    - Allow commands to run in the background (e.g., `sleep 5 &`).
2.  **Pipelines (`|`):**
    - Implement command piping (e.g., `ls -l | grep .c`).

3.  **Signal Handling:**
    - Implement signal handler for `SIGINT`(Ctrl+C) and `SIGCHILD`
4.  **More Built-in Commands:**
    - Implement `echo`, `env`, `setenv`, `unsetenv` (the latter two manage the shell's environment variables).
5.  **More signals:**
    - Implement `SIGTSTP` (Ctrl+Z) to suspend foreground processes.
    - Manage a list of active jobs (processes, their states, and job IDs).
    - Implement `fg` (foreground) and `bg` (background) commands to move jobs between states.
6.  **Command History:**
    - Store previously executed commands.
    - History navigation using arrows
7.  **Error Handling:**
    - Improve error messages (`command not found`, `permission denied`, `syntax error`).
8.  **handle strings**
    - Handle string user input tokenization

## References

[code crafters github](https://github.com/codecrafters-io/build-your-own-x?tab=readme-ov-file#build-your-own-shell)
