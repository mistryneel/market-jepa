# Progress

## Milestone status

| Milestone | Status | Verified by |
|---|---|---|
| M0 Scaffolding | ✅ Done, awaiting human review | Clean-clone run; CI green on 3 platforms; every commit checked in an isolated export; two adversarial review rounds (39 + 25 findings) addressed |
| M1 Data layer | Not started. Sources researched (DATA_SOURCES.md); **licence decisions pending** (HUMAN_TODO §A) | — |
| M2 Point-in-time store | Not started (design: DESIGN §4, §8; D-017, D-021) | — |
| M3 Universe, labels, splits | Not started | — |
| M4 Evaluator, metrics, baselines | Not started | — |
| M5 Run registry, CLI, docs | Not started | — |

## M0 checkpoint (2026-11-12)

### What works

- **uv project** `mjepa-harness` (package `mjepa_harness`, CLI `mjepa`). Python 3.12.13 is
  uv-managed and identical on every machine. The lockfile is committed, and every
  compiled dependency has linux-aarch64, linux-x86_64 and macOS-arm64 wheels.
- **CLI:**
  - `mjepa --help` and `--version`;
  - `doctor`: Python, platform, libraries, configs, pre-registration, data-dir safety, and credential presence (never values);
  - `paths`;
  - `config validate`, `config show`.
- **Configs:** five strict YAML configs (sources, universe, splits, events, endpoint).
  The models are frozen, reject unknown keys and coercions, and the loader rejects
  duplicate keys; the five files are cross-checked against each other.
- **Pre-registration:** the endpoint bundle is pinned
  (`sha256:00a5d153…`; `preregistration.py`), enforced by `doctor` and by tests, and
  must be cited in DECISIONS.md. `status: draft` with 10 fields deliberately undecided.
- **Secrets:** read from environment variables only, and redacted at record and output
  level. Typer locals are off and CLI error output is redacted and escaped.
- **Unit tests are offline by construction:**
  - an audit-hook socket guard;
  - remote PyArrow filesystems blocked;
  - `MJ_OFFLINE` kill switch;
  - proxy blackhole;
  - CI runs Linux tests in a namespace with no network.

  Integration tests run only with `--run-integration`.
- **Repository hygiene:** tests enforce no committable file ≥ 1 MB, data-like files only
  in `data_ref/` (each with a provenance entry), no env files, and no secret-like strings
  or local credential values. `.gitignore` coverage is tested against the committed file
  alone. An optional pre-commit hook is provided.
- **Adapter contract (no adapters yet):** `plan → fetch → normalize`. `fetch` is a
  template that always runs estimate → kill switch → data-dir guard → credentials →
  `--max-gb`/`--yes`. Plans and manifests:
  - separate exact from estimated sizes and count files of unknown size;
  - record remote versions for a write-once landing zone;
  - are credential-free, use UTC and record lineage.
- **Data-dir guard:** git-aware, so symlinks, `..`, case variants and sibling checkouts
  are caught.
- **Provenance:** package version + git SHA, with a conservative dirty flag (untracked
  source files count; an unknown state is never reported clean).
- **Docs:** DESIGN, RUNBOOK, DECISIONS (D-001…D-026), DATA_SOURCES (researched), HUMAN_TODO,
  and this file.

### How it was verified

| Check | Result |
|---|---|
| `uv run pytest` (worktree, macOS arm64; also under `sandbox-exec` with no network) | 225 passed |
| ruff check, ruff format --check, mypy --strict (src + tests) | clean |
| Every commit exported with `git archive` and checked from scratch (uv sync --locked, ruff, mypy, pytest) | all pass (one environment-dependent test caught and fixed) |
| CI on GitHub (ubuntu-24.04 x86_64, ubuntu-24.04-arm aarch64, macos-26 arm64, plus lint/types) | green; Linux tests ran inside a network namespace with no network |
| Clean clone from GitHub, then `uv sync --locked`, `uv run pytest`, `uv run mjepa --help` | see the checkpoint report |
| Adversarial review, round 1: 4 lenses (security, tests, spec fidelity, architecture) × independent verifier | 39 findings, all confirmed or partly confirmed (none refuted); all addressed (code, or a recorded design decision for M2/M3) |
| Re-verification, round 2: each round-1 finding re-tested at HEAD, new regressions hunted, independent verifier | 28 fixed or covered by a recorded design decision, 10 partly fixed, 1 not graded; 25 new findings. All addressed in 5 commits (D-027…D-031), each re-checked in isolation |

### What is mocked or not yet built

- **No data adapters exist yet** (M1). `ADAPTERS` is empty; the contract is exercised
  with a fake adapter in tests.
- **No data has been downloaded.** The research read only documentation and
  metadata.
- **Store, universe, labels, splits, evaluator and registry** are documented
  placeholders.
- **The locked-test gate:** the M0 part exists (`require_locked_preregistration`); the
  gate itself is M3.

### Known issues and limitations

- **Network guard on developer machines.** A plain local `pytest` does not block child
  processes or native code that ignores proxies. CI is airtight: a network namespace on
  Linux and `sandbox-exec` on macOS. The same `sandbox-exec` command works locally
  (RUNBOOK §3).
- **`extra=` log fields** are scrubbed only by our formatter, not at record creation.
- **Not yet built (M1):** the landing-zone writer that calls `ByteBudget.consume()`,
  and the HTTP error handling that re-raises with credential-stripped URLs.
- **Calendars.** The pre-registration bundle records the FOMC/CPI calendars as missing
  until M1 builds them. Committing them changes the bundle fingerprint, which is an
  intended, deliberate pin update.
- **Numerics.** NumPy uses different BLAS on macOS (Accelerate) and Linux (OpenBLAS),
  so covariance numerics will not be bitwise identical across machines; M4 tests will
  use tolerances.
- **Branch history.** `feat/harness-phase0` and `research/eval-catalogue` have
  unrelated root commits (D-014).

### Decisions made at M0

D-001 to D-031 in [DECISIONS.md](DECISIONS.md). These need your confirmation:
- D-008/D-016/D-027: the endpoint definitions and the decision rule (PROPOSED), with 10 fields still undecided;
- the explicit train start;
- D-026: the M1 source strategy (PROPOSED).

### Open questions (details in HUMAN_TODO.md)

1. **Massive.** Will you seek written permission for ML use, and which plan? The core
   equities source is blocked until then.
2. **Macro series.** Primary sources (Treasury, NY Fed, H.15) instead of FRED? And VIX:
   seek Cboe permission or drop it?
3. **Market-1T.** OK to download the 2020-03 slice (2.50 GB) for adapter validation only?
4. **Crypto.** Kraken archive (9.55 GB) as the primary source? Treat the project as
   academic or commercial?
5. **Endpoint.** Confirm the proposals and decide the 10 open fields before locking.
6. **Repo licence; uv 0.13 upgrade; Python 3.12 vs 3.13.**

### Next downloads: estimated size and cost

See [HUMAN_TODO.md §E](HUMAN_TODO.md) and [DATA_SOURCES.md](DATA_SOURCES.md). Everything
that can go ahead is free: Market-1T 2.50 GB, Fed and BLS calendars, EDGAR, Treasury
and NY Fed rates, and Kraken 9.55 GB. Massive is $199/month (individual; likely not
permissible) or $1,999–2,499/month (business), and is **blocked on written ML
permission**.
