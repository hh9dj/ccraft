# serve the docs book with live reload (mdbook watches and reloads the browser)
docs:
    #!/usr/bin/env bash
    set -euo pipefail
    cd "{{ justfile_directory() }}"
    mdbook serve docs --open
