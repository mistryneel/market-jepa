# market-jepa research harness (`mjepa_harness`)

Data pipelines and an evaluation harness for a research paper on a **market world
model**: a JEPA-style model that learns a latent state of the US stock cross-section,
conditioned on scheduled events (FOMC decisions, CPI releases, earnings). The headline
claim is about **risk**: after scheduled announcements, forecast the next 5 trading
days' covariance of ~500 liquid US stocks better than strong baselines.

This repository holds the **harness**, not the model. Its job is point-in-time
correctness, no leakage and honest statistics. The pre-registered primary endpoint is
in [`configs/endpoint.yaml`](configs/endpoint.yaml).

## Quick start

```bash
uv sync --locked
uv run pytest
uv run mjepa --help
uv run mjepa doctor
```

Credentials come from environment variables only (see [`.env.example`](.env.example)).
Data lives under `$MJ_DATA_DIR` (default `~/data/market-jepa`) and never enters git.

## Documentation

| Document | What it covers |
|---|---|
| [docs/harness/DESIGN.md](docs/harness/DESIGN.md) | Architecture, point-in-time contract, guards, testing strategy |
| [docs/harness/RUNBOOK.md](docs/harness/RUNBOOK.md) | From a clean clone to a working setup (and, later, baseline reports) |
| [docs/harness/DATA_SOURCES.md](docs/harness/DATA_SOURCES.md) | Each source's coverage, terms, cost and known gaps |
| [docs/harness/DECISIONS.md](docs/harness/DECISIONS.md) | Every design decision, with alternatives and reasons |
| [docs/harness/PROGRESS.md](docs/harness/PROGRESS.md) | Milestone status, what is verified, known issues |
| [docs/harness/HUMAN_TODO.md](docs/harness/HUMAN_TODO.md) | Accounts, keys, purchases and approvals a human must handle |

`docs/evals/` is maintained separately on the `research/eval-catalogue` branch.

## Milestones (Phase 0)

M0 scaffolding · M1 data layer · M2 point-in-time store · M3 universe, labels, splits ·
M4 evaluator, metrics, baselines · M5 run registry, CLI and docs.
