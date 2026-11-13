# Runbook

How to set up the harness, check it, and (from M1) fetch data and run baselines.
Sections for later milestones are filled in as they land.

## 1. Prerequisites

* `git` and [uv](https://docs.astral.sh/uv/) 0.11.7 or later; CI pins 0.11.7, the
  version that wrote `uv.lock` (D-023). Install uv with
  `curl -LsSf https://astral.sh/uv/install.sh | sh`, or `brew install uv` on macOS.
* Nothing else. uv downloads its own managed CPython 3.12.13 on first sync, the same
  build on every machine (`python-preference = "only-managed"`). Every dependency ships
  wheels for Linux aarch64 (DGX Spark), Linux x86_64 and macOS arm64, so nothing is
  compiled.
* On the DGX Spark, record the machine facts once: `uname -m` (expect aarch64),
  `ldd --version` (expect glibc 2.39), `getconf PAGESIZE` and `nvidia-smi`.

## 2. Set up from a clean clone

```bash
git clone https://github.com/mistryneel/market-jepa.git
cd market-jepa
git checkout feat/harness-phase0
uv sync --locked
```

`uv sync --locked` creates `.venv/` from `uv.lock`, exactly. It fails rather than
silently re-resolving if `pyproject.toml` and `uv.lock` disagree.

## 3. Check the install

```bash
uv run pytest                 # unit tests: offline, about 5 seconds
uv run ruff check .           # lint
uv run ruff format --check .  # formatting
uv run mypy                   # strict type check of src/ and tests/
uv run mjepa --help
uv run mjepa doctor           # environment report; exits 1 if a hard check fails
```

`mjepa doctor` reports Python, platform, library versions, config validity, the
endpoint fingerprint and status, data-directory safety, and which credentials are set.
It never shows credential values. Missing credentials are warnings: each data source
asks for its own when you use it. `pre-registration: warn` means the endpoint is still
`status: draft`; `FAIL` means the endpoint bundle no longer matches its pin.

Optional: block commits that would add data or secrets, for your clone. The hook scans
exactly what is staged (an export of the index), not the working tree:

```bash
git config core.hooksPath scripts/hooks   # runs tests/test_repo_hygiene.py on every commit
```

On a Mac you can also run the unit tests with the network switched off, as CI does:

```bash
sandbox-exec -p '(version 1)(allow default)(deny network-outbound (remote ip))' .venv/bin/python -m pytest
```

## 4. Credentials

Credentials come from environment variables only. Never commit them.

```bash
cp .env.example .env          # .env is git-ignored
$EDITOR .env                  # fill in what you have; leave the rest empty
uv run --env-file .env mjepa doctor
```

Prefix any command with `uv run --env-file .env` to load the file into its environment.
You can also `export` the variables in your shell. How to obtain each credential is in
[HUMAN_TODO.md](HUMAN_TODO.md).

## 5. Data directory

All data lives under `$MJ_DATA_DIR`, default `~/data/market-jepa`. On the DGX Spark,
point it at the large disk, for example `export MJ_DATA_DIR=/data/market-jepa`. The
harness refuses a data directory inside the repository unless git ignores it.

```bash
uv run mjepa paths            # shows raw/, manifests/, pit/, catalog/, locked/, ...
```

## 6. Configs

```bash
uv run mjepa config validate  # all five configs, cross-file checks, fingerprints
uv run mjepa config show endpoint
```

`configs/endpoint.yaml` is the pre-registered primary endpoint. Changing it, or
`configs/splits.yaml`, or an event calendar it scores, changes the endpoint-bundle
fingerprint. That fails `mjepa doctor` and `tests/test_preregistration.py` until two
things are done in the same commit: `PREREGISTERED_BUNDLE_FINGERPRINT` in
`src/mjepa_harness/preregistration.py` is updated, and a dated entry citing the new
value is added to [DECISIONS.md](DECISIONS.md).

## 7. Integration tests (from M1)

```bash
uv run --env-file .env pytest --run-integration -m integration
```

They touch live APIs and run only with `--run-integration`; without it they are reported
as skipped. Each one also skips itself when its credentials are missing. Never run them
in CI.

## 8. Fetching data (M1)

*To be written in M1.* Every fetch command plans first, prints an estimate (files, GB,
time) and refuses more than `--max-gb` (default 2) unless you pass `--yes`.

## 9. Running baselines and reading results (M4–M5)

*To be written in M4–M5.*

## 10. Troubleshooting

| Symptom | Fix |
|---|---|
| `doctor`: python FAIL | `uv python install 3.12 && uv sync --locked` |
| `doctor`: data dir FAIL, "NOT git-ignored" | Set `MJ_DATA_DIR` to a path outside the repo |
| `config error: ...` | The message names the file and field. Typos and unknown keys are errors by design |
| `uv sync --locked` fails | `pyproject.toml` changed without `uv lock`. Run `uv lock` and commit `uv.lock` |
| A unit test raises "must not touch the network" | It needs `@pytest.mark.integration` and `require_env(...)`, or a synthetic fixture |
| `doctor`: pre-registration FAIL | The endpoint bundle changed. Revert, or update the pin plus DECISIONS.md (section 6) |
| `uv` says the lockfile is incompatible | Use the uv minor recorded in D-023 (CI pins it), or upgrade lock and pins together |
