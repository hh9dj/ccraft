# Stage 0: Setup

## Objective

Before writing a single line of loop code, set up a project that builds and tests with one command. By the end of this stage you'll have a `uv`-managed Python package, an empty `EventLoop` you can import, a pytest fixture that hands every test a fresh loop, and an entry point you can actually run. There's no loop behavior yet — and that's the point. The toolchain should be boring and repeatable, because every later stage will be driven by `uv run pytest`. Focus areas: tooling and test-driven stage discipline.

## Steps

- Confirm `uv` is installed and that `loop/pyproject.toml` and `.python-version` (3.12) exist. Skim the [uv docs](https://docs.astral.sh/uv/) and the [pytest docs](https://docs.pytest.org/en/stable/) first. Why: every later command runs through `uv run`, and the interpreter version is pinned by `.python-version`, so this file is your real ground truth.
- Decide the package layout: `loop/__init__.py` exports `EventLoop`; the implementation is split across `loop/loop.py` (Stages 1–4), `loop/futures.py` (Stage 7), and `loop/sock.py` (Stage 10), with tests under `tests/`.
- Commit to zero runtime dependencies: only the standard library (`selectors`, `heapq`, `time`, `socket`). Why: the whole value of this project is that you can read every line, so keep it inspectable.
- Define a pytest fixture that hands every test a fresh `EventLoop`. Why: isolation — a leaked timer or selector registration from one test must not bleed into the next.
- Keep tests hermetic by using `os.pipe()` or `socket.socketpair()` instead of the network.
- Add `main.py` as the entry point and confirm `uv run main.py` runs end-to-end before starting Stage 1.

## Design Questions

- What belongs on the public `__init__` surface versus internal modules?
- Which fixture owns teardown of the loop and its descriptors?

## Tests

- [x] `uv run pytest` exits 0 with the smoke test.
- [x] `uv run main.py` runs.
- [x] The package skeleton matches the layout above.

## Hints

- Test command: `uv run pytest tests/test_smoke.py` (the full suite stays `uv run pytest tests/`). Your smoke test should collect and pass, and `main.py` should run under `uv run`.
- Do not run `pip install`; doing so corrupts `uv.lock`.
- Keep tests hermetic by using `os.pipe()` or `socket.socketpair()` instead of the network.
- Confirm that `uv run main.py` works end-to-end before you start Stage 1.
