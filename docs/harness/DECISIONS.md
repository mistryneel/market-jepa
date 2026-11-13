# Decisions

One entry per decision: date, the decision, alternatives considered, and why. Newest
entries go at the bottom. Entries marked **PROPOSED** wait for the human's confirmation.

---

### D-001 · 2026-11-12 · Names: `mjepa-harness`, `mjepa_harness`, `mjepa`
- **Decision:** distribution `mjepa-harness`, import package `mjepa_harness`, console script `mjepa`.
- **Alternatives:** `market_jepa` (forbidden by the brief); `harness` (too generic to install alongside other tools).
- **Why:** the brief requires `mjepa_harness` so we can install the Market-1T authors' `market_jepa` alongside it.

### D-002 · 2026-11-12 · Python 3.12, uv with `uv_build`, committed lockfile
- **Decision:** `requires-python = ">=3.12,<3.13"`, `.python-version` = 3.12, and `uv_build` as the build backend. `uv.lock` is committed. CI uses `uv sync --locked`.
- **Alternatives:** hatchling (also fine, but one more tool); allowing 3.13+ (the brief says 3.12, and an exact minor keeps numerics reproducible across the DGX and laptops).
- **Why:** one toolchain from lock to build; `--locked` makes CI fail on drift instead of re-resolving.

### D-003 · 2026-11-12 · Layout: the brief's layout plus top-level helper modules
- **Decision:** keep `sources/ store/ universe/ labels/ splits/ evaluate/ registry/ cli.py`. Add `settings.py` (env), `config.py` (YAML schemas), `log.py` (redacting logging), `paths.py` (data layout and guard) and `provenance.py` (git SHA) at the package root. The adapter contract lives in `sources/base.py`.
- **Alternatives:** a `core/` or `utils/` subpackage (vague names, deeper imports); putting config under `store/` (wrong owner).
- **Why:** every subpackage uses these helpers, so none of them should own them. Flat modules are easy to find and review.

### D-004 · 2026-11-12 · Core dependencies at M0; source-specific ones later
- **Decision:** M0 depends on `polars`, `pyarrow`, `duckdb`, `pydantic`, `pyyaml`, `typer` and `rich`. Source-specific packages (Hugging Face Hub, MosaicML streaming, S3 clients, HTTP and retry) arrive in M1, as optional extras where they are heavy.
- **Alternatives:** add everything up front; or defer Polars/PyArrow/DuckDB until M2.
- **Why:** the mandated storage stack is installed and smoke-tested (`tests/test_stack_smoke.py`) on every CI platform from day one, so a missing aarch64 wheel shows up now, not mid-M2. The lock currently resolves Polars 2.1, PyArrow 26 and DuckDB 2.0. All compiled dependencies have manylinux aarch64, x86_64 and macOS arm64 wheels (checked from `uv.lock`).

### D-005 · 2026-11-12 · Credentials: environment only, explicit reader, redaction everywhere
- **Decision:** `settings.Credentials` reads exactly the six variables in the brief from `os.environ` and wraps them in `SecretStr`. Empty or whitespace-only means unset. A local `.env` is supported only through `uv run --env-file .env ...`; the code never opens it. Logging scrubs registered values, their URL-encoded forms and generic secret shapes from the final formatted text. Typer's pretty tracebacks (which print local variables) are off, and `main()` logs unexpected errors through the redactor.
- **Alternatives:** `pydantic-settings` with `env_file` support (reads a file, contrary to "environment variables only", and adds a dependency); a log-record factory instead of a formatter (covers foreign handlers, but mutates every record).
- **Why:** the most literal reading of rule 2, with a small explicit surface that is easy to test. Fake secrets planted in tests prove the redaction for messages, args, tracebacks, URL-encoded values, Bearer headers and JSON logs.

### D-006 · 2026-11-12 · Configs are strict and typo-proof
- **Decision:** frozen pydantic models with `extra="forbid"` and `strict=True`. The YAML loader is a `SafeLoader` that rejects duplicate keys and turns sequences into tuples.
- **Alternatives:** lax pydantic (it coerces `"500"` to 500 and accepts YAML's `yes`/`no`); plain dicts.
- **Why:** a silently ignored or coerced key in a research config is a correctness bug a reviewer can exploit. PyYAML otherwise keeps the last of two duplicate keys without complaint.

### D-007 · 2026-11-12 · Pre-registration lock for the primary endpoint
- **Decision:** `configs/endpoint.yaml` holds the brief's sentence verbatim (tested) plus structured fields. Its canonical SHA-256 fingerprint (parsed content, so comments and formatting do not count) is pinned in `tests/test_preregistration.py`. Changing it needs a pin update and a DECISIONS entry in the same commit. `status: draft` until the human confirms the definitions; the M3 unlock gate will refuse locked-test reads while it is `draft`.
- **Superseded in part by D-016** (2026-11-12, after the M0 review): the pin now covers the whole endpoint bundle, lives in the package and is enforced at runtime.
- **Alternatives:** prose only (unenforceable); a git tag (easy to move); hashing the raw file (comment edits would trip it).
- **Why:** it makes "we changed the endpoint after seeing results" visible in review and impossible to do silently.

### D-008 · 2026-11-12 · **PROPOSED** Endpoint operational definitions
- **Decision (proposed, `status: draft`):**
  1. `forecast_origin`: the last close strictly before the announcement.
  2. `day_1`: the first session whose close comes after the announcement. That is the event day for 08:30 ET CPI and 14:00 ET FOMC releases, and the next session for a release on a non-trading day.
  3. `returns`: daily close-to-close total returns.
  4. `realized_covariance`: the sum of outer products of the 5 daily return vectors, with no demeaning.
  5. `stein_singular_target`: evaluate Stein loss up to its forecast-independent term, i.e. L(Σ̂; S) = tr(Σ̂⁻¹S) + log det Σ̂.
  - *Update (D-016):* the formula and its orientation are now fingerprinted fields (`metric.loss`), not a YAML comment.
- **Alternatives:** day 1 = the session *after* the event day (drops the FOMC-afternoon and CPI-day reaction that the thesis is about); realized covariance from intraday returns (5 days × 390 one-minute returns would make S full rank, but needs minute data, asynchronicity handling and Epps-effect corrections); shrinking S before scoring (biases the comparison).
- **Why:** the sentence is ambiguous on day 1. More seriously, with N = 500 stocks and 5 daily returns, S has rank ≤ 5, so log det(Σ̂⁻¹S) = −∞ and textbook Stein loss is infinite for every forecast. Dropping log det S changes no paired difference between forecasts, and the result remains a consistent loss for a conditionally unbiased proxy (Patton 2011; Laurent, Rombouts & Violante 2013). It does change the absolute level, so the M4 known-answer test checks *differences* (oracle < estimators), not "oracle ≈ 0", whenever the target is a realized proxy. **Needs the human's confirmation before `status: locked`.**

### D-009 · 2026-11-12 · Unit-test isolation
- **Decision:** `tests/conftest.py` installs a socket guard at session start (collection included), points proxy variables at a closed local port, and sets `HF_HUB_OFFLINE=1` for native libraries. It scrubs credentials and points `MJ_DATA_DIR` at a temp dir for each unit test. Integration tests are deselected by default (`-m "not integration"` in addopts) and use `require_env(...)` to skip without credentials. A pytester meta-test proves the guard in a subprocess.
- **Alternatives:** the `pytest-socket` plugin (similar, but no native-library fallback or credential scrubbing); trusting reviewers.
- **Why:** rule 7, enforced by construction.

### D-010 · 2026-11-12 · Repository hygiene enforced by tests
- **Decision:** `tests/test_repo_hygiene.py` checks every committable file (tracked plus untracked, non-ignored): size < 1,000,000 bytes; data-like suffixes only under `data_ref/`; each `data_ref` table has an entry in `data_ref/SOURCES.yaml` (https source URLs, retrieval date, licence); no `.env*` except `.env.example`, whose credential values are empty; no secret-shaped strings or values of credentials from the developer's environment; `.gitignore` covers data and secret paths.
- **Alternatives:** a pre-commit hook only (optional per machine); gitleaks in CI only (runs after the push to a **public** repo, which is too late).
- **Why:** the remote `mistryneel/market-jepa` is **public**, so anything committed is published. The checks run on every `pytest`, before any commit.

### D-011 · 2026-11-12 · Data-directory guard
- **Decision:** `paths.check_data_dir_safe` allows `MJ_DATA_DIR` anywhere outside the repo, and inside it only if git ignores the directory itself. It probes with `.json` and `.csv` names, because extension rules like `*.parquet` would otherwise make any directory look safe.
- **Alternatives:** forbid any data dir inside the repo (too strict for a git-ignored `data/` scratch area).
- **Why:** rule 1 for every data-writing command. `doctor` reports violations today; fetch commands check before writing (M1).

### D-012 · 2026-11-12 · Download-guard semantics
- **Decision:** GB means decimal (1e9 bytes). The guard refuses above `--max-gb` (default 2) without `--yes`; refuses when any pending file's size is unknown, without `--yes`; and refuses when credentials are missing, even with `--yes`. Files already present (same size and checksum) cost nothing, so re-runs are free.
- **Alternatives:** treat an unknown size as zero (unsafe); let `--yes` bypass missing credentials (would fail later, less clearly).
- **Why:** the most conservative reading of rule 4.

### D-013 · 2026-11-12 · UTC everywhere
- **Decision:** all stored and logged timestamps are timezone-aware UTC. Trading dates are `date` in America/New_York. Ruff's `DTZ` rules ban naive datetimes. Manifest models require aware datetimes.
- **Alternatives:** store ET wall-clock times (DST ambiguity; the November fall-back hour repeats).
- **Why:** `knowledge_time` comparisons must be unambiguous.

### D-014 · 2026-11-12 · Branch topology (flagged, no action taken)
- **Observation:** the human created the `feat/harness-phase0` and `research/eval-catalogue` worktrees from an unborn `main`, so each branch's first commit is a root commit. The branches share no history, and merging them will need `git merge --allow-unrelated-histories`. That is safe: the evals agent writes only `docs/evals/`, which this branch never touches.
- **Alternatives:** rebase both onto a shared initial commit on `main` (rewrites history; not ours to do).
- **Why recorded:** so the merge step is not a surprise. Listed in HUMAN_TODO.md.

### D-015 · 2026-11-12 · Every commit is verified in isolation
- **Decision:** besides running ruff, mypy and pytest in the worktree, each commit's tree is exported with `git archive` into a scratch directory and checked there with `uv sync --locked`, ruff, mypy and pytest.
- **Why:** this catches tests that depend on local state. It found one: a CLI test needed a `.git` directory. It now skips in source exports (commit `64e5a51`).

### D-016 · 2026-11-12 · Pre-registration covers the whole endpoint bundle and is enforced at runtime (M0 review: SPEC-1/2/3/5/6/7/8/9, FIT-1)
- **Decision:**
  - **What the pin covers.** The pinned value is a fingerprint of the *endpoint bundle*: the parsed `endpoint.yaml`, the parsed `splits.yaml` and the SHA-256 of every event calendar the endpoint scores (`preregistration.endpoint_bundle`).
  - **Where it lives.** `src/mjepa_harness/preregistration.py`, so code can check it. `mjepa doctor` reports FAIL on a mismatch. The M3 unlock gate calls `require_locked_preregistration`, which refuses unless the bundle matches the pin, `status: locked`, no field is undecided and every calendar exists.
  - **How changes are tracked.** `tests/test_preregistration.py` requires this file to cite the pinned value, so each pin change comes with a dated entry here.
  - **Pinned bundle (2026-11-12, status draft, calendars not yet built):** `sha256:fcaf725112066141350ee3d83e6c7db3401680fd29f73c034408d7bbd10f97c9`. *(Superseded by D-027.)*
- **What the endpoint now pins:**
  - **Metric by formula.** `metric.name: inverse_stein`, `loss: tr(H^-1 S) + logdet(H)`, with H the forecast of E[S | origin] on the 5-day-sum scale. "Stein loss" has two orientations in the literature, and only the inverse one is finite and consistent with a rank-5 realized proxy; the canonical one would need an unpinned pseudo-inverse.
  - **Target.** Simple close-to-close returns on the XNYS calendar.
  - **Universe rules.** Raw unadjusted close on the last session of the prior month, *strictly* above $5; back-adjusted prices would use future split factors. Dollar volume is the sum over the prior month of raw close × raw volume. Security types `[CS]`. Tie-break by `asset_id`.
  - **Event-level rules** (all PROPOSED):
    - asset set = the universe of the month that contains the origin;
    - an asset missing any day-1..5 return is dropped for every model and N_e is recorded;
    - each announcement is one observation; overlapping CPI/FOMC windows fall in the same month block;
    - forecasts must be SPD, and an invalid forecast is an error, not a silent ridge;
    - scheduled = as published before the origin; rescheduled releases at the actual time; cancelled releases dropped.
  - **Decision rule.** Paired by event. Primary comparison: event-conditioned model vs an equal-size supervised model (H2). Baselines: sample covariance, EWMA, Ledoit-Wolf linear, PCA/Marchenko-Pastur, with hyperparameters selected on the tune period only. Statistic: mean paired loss difference, one-sided (`less`), alpha 0.05. Bootstrap n_boot 10,000, seed 20261112. Holm over the baseline comparisons.
  - **Explicit train start.** `splits.periods.train.start: 2005-01-01`, the first year of the event calendars. Before, `null` would have meant "whatever data is on disk".
  - **Purge and embargo** are checked against the endpoint's last label session (`horizon.last`), not the horizon's length.
- **Still undecided, by design (`null`; the schema refuses `status: locked` until set):**
  - `universe.share_class_rule`
  - `universe.exchanges`
  - `universe.min_sessions_in_prior_month`
  - `definitions.refit_policy` (frozen at 2021-12-31 vs re-estimated during the locked period)
  - `decision_rule.bootstrap.scheme`
  - `decision_rule.bootstrap.block_length`
- **Alternatives:**
  - Keep the pin in a test only: the runtime would accept any `status: locked` config.
  - Pin only `endpoint.yaml`: the scored events, which come from the calendars, and the train/tune protocol could change silently.
  - Decide the open fields myself now: these are research-design choices for the human or for M3 with data in hand.
- **Why:** the endpoint's number depends on which events and stocks are scored and how "better" is decided. All of that must be fixed before any locked-period result exists. **PROPOSED values need the human's confirmation.**

### D-017 · 2026-11-12 · Locked-period quarantine sits at the storage/query layer, not only at labels (M0 review: SPEC-4, FIT-4; implemented in M2-M3)
- **Decision:**
  - **What is quarantined.** Every `pit/` row in *every* table whose `event_time` or `knowledge_time` is on or after the locked-test start (2022-01-01) is locked-period data. That covers daily and minute bars, filings, features and names outside the universe, not only labels or the rows an endpoint target uses. All such rows are excluded from the default DuckDB views and as-of helpers. Any exception must be listed in this file. (Corrected 2026-11-12 after review round 2, SPEC-R2-1.)
  - **How it is reached.** Only through an `UnlockToken`. The `--unlock-test` path mints the token after `require_locked_preregistration` passes and an append-only registry record is written. Locked-period forecasting and scoring both run inside that path.
  - **Label dating.** Labels are dated by the *last* session of their window, so a label whose window reaches into 2022 is locked.
  - **Boundaries.** Purge and embargo also apply at the train/tune and tune/locked boundaries.
  - **Test.** A planted test must show that a 2022 daily bar, a 2022 minute bar, a 2022 bar of a name outside the universe and a 2022 feature row are all invisible to ordinary as-of queries and to the tuning API.
- **Alternatives:** gate only the derived label tables (the original design). That fails because the 5-day realized covariance is a deterministic function of the open daily bars, so locked outcomes could be recomputed without leaving a registry record.
- **Why:** the gate and its log must be able to show that locked outcomes were never examined. This must be settled before M1/M2 write `pit/`.

### D-018 · 2026-11-12 · The fetch guards are enforced by the base class, not by convention (M0 review: FIT-6, TEST-1, SEC-2, SEC-8)
- **Decision:** `SourceAdapter.fetch` is a concrete template method. Adapters implement only `plan`, `_download` and `normalize`. `fetch` runs these steps in a fixed order:
  1. print the estimate;
  2. check the `MJ_OFFLINE` kill switch (`mjepa_harness.net.require_network`);
  3. refuse an unsafe data directory;
  4. work out missing credentials from `required_env`;
  5. enforce the `--max-gb`/`--yes` budget.

  Only then does it hand `_download` an `ApprovedPlan`.

  The data-dir guard asks git which work tree actually contains the directory. It resolves symlinks first, including ones whose target does not exist yet, then `..` and case variants, so a sibling checkout or worktree of this repository is caught even when nobody names it. `DataLayout.ensure()` runs the guard before creating anything and checks containment on resolved paths.
- **Alternatives:** a guard function adapters "should" call (forgettable); a decorator (adapters could skip it).
- **Why:** rule 4 and rule 1 must hold for adapters written later by anyone.

### D-019 · 2026-11-12 · Plans, manifests and lineage (M0 review: FIT-3, FIT-5, FIT-8, FIT-10, SEC-7)
- **Decision:**
  - **Sizes.** `PlannedFile` separates an exact listing size (`expected_bytes`) from a heuristic one (`estimated_bytes`). Estimated sizes count towards the budget, so a REST source such as FRED can pass the 2 GB guard without `--yes`. Files of unknown size are counted and shown, and still require `--yes`. `estimated_seconds` is mandatory. `--max-gb` must be finite and positive, so `nan` no longer disables the cap.
  - **Write-once landing zone.** `raw/` is write-once. A changed remote object is stored under a new path and never overwrites bytes an older manifest points to. Entries record `remote_version` (HF commit, ETag, Last-Modified) and `origin_fetch_id`, and a manifest lists the full state of its request.
  - **Lineage.** `NormalizedTable` records sha256, input fetch ids and the structured code version.
  - **Timestamps.** Normalised to UTC on input.
  - **Immutability.** Request and attribute mappings are immutable.
  - **No credentials.** URIs and request values are rejected if they carry credentials: userinfo, key/token/signature parameters or registered secrets. `strip_credentials()` produces the loggable form; FRED's `api_key` parameter is the motivating case.
- **Alternatives:** overwrite-in-place with ETag checks (loses the bytes older manifests describe; Massive replaces flat files without notice); content-addressed storage only (harder for humans to inspect; may still be adopted in M1).
- **Why:** reproducibility, meaning that every run can name the exact bytes it read, and rule 2.

### D-020 · 2026-11-12 · Provenance treats untracked source files as dirty (M0 review: FIT-2)
- **Decision:** `code_version()` reports dirty when any result-affecting path (`src`, `configs`, `data_ref`, `pyproject.toml`, `uv.lock`, `.python-version`) has uncommitted changes *or untracked files*. An unknown state renders as `.dirty-unknown` and never as clean. Outside a git checkout it reports `+nogit`; it never guesses a SHA.
- **Why:** a new, untracked module can change results while `HEAD` looks clean.

### D-021 · 2026-11-12 · DuckDB catalog: per-process in-memory views by default (M0 review: FIT-9; implemented in M2)
- **Decision:** M2's catalog opens an in-memory DuckDB per process and defines views over `pit/` Parquet. Every connection sets `autoinstall_known_extensions=false`, `autoload_known_extensions=false`, `TimeZone='UTC'` and `Calendar='gregorian'`. `catalog/mjepa.duckdb` is at most a read-only published snapshot, rebuilt into a temporary file and atomically renamed into place.
- **Alternatives:** one persistent read-write `.duckdb` file. DuckDB lets only one process hold it read-write, so it would block parallel runs on the DGX.
- **Why:** concurrency, plus no silent extension downloads (network) and no locale-dependent defaults.

### D-022 · 2026-11-12 · Hygiene scan knows this project's credentials; optional pre-commit hook (M0 review: SEC-1, SEC-5, SEC-9, TEST-2, TEST-9)
- **Decision:**
  - **What the scan matches.** It flags secret-looking assignments to sensitive keys: values of 16+ token characters mixing letters and digits, which covers FRED, Massive REST and S3 keys and Bearer headers. It also flags vendor token shapes and the actual credential values found in the environment *and* in local git-ignored env files (`.env`, `*.env`, `.envrc`).
  - **How it scans.** Binary or non-UTF-8 files are decoded with replacement and still scanned. Failures name the file, line and pattern kind, never the value. Placeholders must contain `EXAMPLE`.
  - **What is ignored.** `.gitignore` also covers `*.env`, `*.env.*` and `.envrc`.
  - **Data-like files.** Suffixes are matched case-insensitively and include raw payload formats (`.json`, `.html`, `.txt`, `.idx`, …). Such files may sit outside `data_ref/` only via an explicit allowlist.
  - **What the ignore-coverage test checks.** Only the committed `.gitignore`, in a fresh repo without global or local excludes.
  - **Pre-commit hook.** `scripts/hooks/pre-commit` (optional; enable with `git config core.hooksPath scripts/hooks`) runs these checks on every commit.
- **Why:** the remote is public. The earlier scan matched none of the key formats this project actually uses, and saw `.env` values only if they had been exported into pytest's environment.

### D-023 · 2026-11-12 · CI pins and the toolchain
- **Decision:**
  - **Actions** are pinned by full commit SHA: `actions/checkout` v7.0.1 `3d3c42e5…` and `astral-sh/setup-uv` v10.3.3 `68559e99…`. setup-uv has published no floating major tags since v8, so SHA pinning is required anyway.
  - **Runners** are pinned too: `ubuntu-24.04` and `ubuntu-24.04-arm` (the DGX Spark's Ubuntu userland; `ubuntu-latest` is moving to 26.04 in November 2026) and `macos-26` (arm64).
  - **On Linux** the unit tests run under `sudo unshare --net` with the venv interpreter.
  - **uv:** CI pins 0.11.7, the version that wrote `uv.lock`; lockfile compatibility is guaranteed only within a uv minor.
  - **CPython:** every machine uses uv-managed 3.12.13 (`python-preference = "only-managed"`, `.python-version` = `3.12.13`), never a system Python.
- **Open:** uv 0.13.8 is current. Upgrading means bumping `uv_build`, `required-version`, the CI pin and the lock together; HUMAN_TODO asks whether to upgrade all machines.
- **Why:** reproducible builds on three architectures, and an airtight offline test run.

### D-024 · 2026-11-12 · Network guard layers and integration gating (supersedes D-009's mechanism; M0 review TEST-1/4/5/8)
- **Decision:**
  - **Layers:**
    1. CI on Linux runs the tests in a namespace with no network.
    2. A `sys.addaudithook` guard blocks non-AF_UNIX connect/sendto/sendmsg and all name resolution, at the C level.
    3. Remote PyArrow filesystems are blocked, and `MJ_OFFLINE=1` stops the harness's own fetch path.
    4. Proxy variables point at a closed port, and Hugging Face runs offline.
  - **Integration tests** run only with `--run-integration`; `-m integration` alone skips them.
  - **Meta-tests** use the repo's real pytest configuration.
- **Alternatives:** monkeypatching `socket.socket` methods (the original approach; misses `_socket`, UDP and `gethostbyname`); `pytest-socket` (same limits).
- **Why:** rule 7 must hold for native code and for user-supplied `-m` filters.

### D-025 · 2026-11-12 · Record-level log redaction (extends D-005; M0 review SEC-3/4/6/10)
- **Decision:**
  - **Record level.** A LogRecord factory scrubs every record at creation (message, arguments, exception text, stack info), so every handler is covered, pytest's captured logs included. Calls with mismatched arguments never dump them.
  - **Output level.** Handler output is scrubbed again.
  - **CLI output.** It is redacted and markup-escaped.
  - **Default secrets.** `configure_logging` registers the environment's credentials by default.
  - **Linting.** Ruff `PLE`/`G` rules lint logging calls.
  - **Limitation.** `extra=` fields are attached after the factory runs and are scrubbed only by our formatter, so never put secrets there.
- **Why:** pytest's "Captured log call" section printed raw keys that our handler had redacted.

### D-026 · 2026-11-12 · **PROPOSED** Source strategy for M1, given the licence findings (needs the human's decisions)
The 2026-11-12 research (8 agents plus 8 independent fact-checkers; see DATA_SOURCES.md) found licence terms that change the plan. Proposal:
- **Massive (equities, security master, corporate actions; market-1t rebuild).** The Market Data Terms (§5(g), updated 2026-11-03) and Business ToS (§6.1(j)) forbid training, fine-tuning or distilling ML models on Massive data without express permission. Individual plans also exclude organisational use and publishing.
  - Build the adapter. `plan` works from listings; `fetch` refuses until the human records written permission.
  - No Massive data is downloaded for this project until then.
  - `market1t-rebuild plan` works offline from a per-year size table. `run` additionally requires a quote-size unit check, because market-1t multiplies NBBO sizes by 100 while Massive regenerated its history in shares.
- **FRED/ALFRED.** The FRED Services Terms forbid ML or deep-learning use of FRED content and forbid storing it in a database.
  - Default to primary sources: Treasury Daily Par Yield Curve (CC0) for the 2-year and 10-year yields; NY Fed Markets API for EFFR; Board H.15 as a cross-check.
  - Keep a FRED adapter behind an explicit flag, off until written permission from the St. Louis Fed.
  - VIXCLS is Cboe-copyrighted: request Cboe permission or drop VIX.
- **Market-1T public subset.** Validation-only, on 2020-03 sparse (132 files, 2,502,351,803 B, ungated).
  - Revision pinned to `5797a9f890e133c491265bb8889cd64f27ceb50e`; every file checked against its SHA-256.
  - Read with an in-house MDS reader (numpy + zstandard). `mosaicml-streaming` stays out of the lock: it requires torch and pins numpy<2.2.
  - Its licence ("other/derived-market-data", no text) is unclear, so publish nothing derived from it until fin-ai-lab clarifies.
- **Calendars (Fed Board and BLS; public domain).** Build from the BLS release archives (actual dates) and the Fed historical pages, plus a hand-curated overrides file with a source URL on every row. Fetch politely with a contact User-Agent. Known date changes come from the Oct 2013, Oct–Nov 2025 and Jan–Feb 2026 funding lapses; the October 2025 CPI and jobs reports were cancelled.
- **SEC EDGAR (public).** Use the per-CIK Submissions API from one designated host at ≤ 5 req/s. Derive knowledge time from `acceptanceDateTime` (true UTC, verified) and `filingDate` together, and use EDGAR business days for dissemination.
- **Crypto.**
  - Primary: Kraken's free OHLCVT archive, which keeps many delisted pairs. Kraken's ToS §9 bars automation without consent, so the human downloads it (9.55 GB) and the adapter ingests it from a local path, unless Kraken consents to scripted access.
  - Coinbase as a cross-check only: its terms require consent before derived research is shared.
  - Binance only after legal clearance: its Vision Dataset Terms are CC BY-NC-SA 4.0 and are subject to Binance ToU eligibility, which excludes US persons.
  - A 50-coin USD universe is realistic only from about 2021 (unverified estimate; measure it after download).
- **Calendar library.** `exchange_calendars` for XNYS, with explicit start and end dates (its default window is the last 20 years) and pandas pinned below 3.1 (issue #632).
- **Why:** rule 3 ("respect source terms") and the paper's publishability.

### D-027 · 2026-11-12 · Pre-registration tightened after review round 2 (SPEC-R2-2/3/4/6/7, SPEC-5/6, T-NEW-1)
- **Decision:**
  - **Survivorship is pinned.** `universe.survivorship: include_delisted_pit_security_master` is part of the bundle, and loading fails unless `sources.massive.include_delisted` is true.
  - **New undecided fields.** The endpoint gains four `null` fields: `definitions.min_history_sessions` (assets with less history at the origin are dropped for every model and counted in N_e), `definitions.unscheduled_actions`, `decision_rule.baseline_specs` (per-baseline tune-period grids, each SPD-feasible at N=500; a sample covariance needs a window of at least N+1 sessions and EWMA is near-singular) and `decision_rule.success_criterion`. The schema refuses `status: locked` while any of the now **10** undecided fields is null.
  - **The unlock gate is stricter.** `require_locked_preregistration` also requires a clean commit (`code_version().is_clean`) and configs read from the repository's own `configs/`. A pin and endpoint edited together in the working tree therefore cannot unlock. `doctor` FAILs if a locked endpoint runs on dirty code.
  - **The pin test compares against a literal.** The test holds the pinned value itself, so it no longer trusts the code under test. Negative tests cover doctor FAIL after a protocol edit, and the unlock gate end to end: it unlocks once complete and pinned, and refuses on dirty code, foreign configs, an edited calendar or a missing calendar.
  - **QLIKE is a separate metric.** The brief's QLIKE metric (M4) is univariate QLIKE per asset and per portfolio, distinct from the full-matrix inverse-Stein endpoint loss. M4 adds the known-answer test that E[L(cΣ)] is minimised at c = 1.
  - **Calendar hashing (M1).** The bundle hashes each calendar file whole. That is deliberately strict while in draft. Before locking, M1 points the endpoint at a frozen, dated calendar snapshot, or hashes a canonical projection: the scored rows in UTC, sorted. A routine refresh of later rows then does not break the pin.
- **Pinned bundle (2026-11-12, status draft):** `sha256:00a5d1536f45dd0104cd8cf5c96bde5f61230f94422df4daa3fd1db33673e889`. This replaces D-016's value.
- **Why:** the round-2 review showed the survivorship switch outside the pin, baselines that could not meet the SPD rule, and a gate that trusted an uncommitted pin.

### D-028 · 2026-11-12 · Data-dir guard fails closed; provenance only trusts its own checkout (review round 2: ARCH2-1, SEC-R2-2, ARCH2-6, FIT-2)
- **Decision:**
  - **Repositories are found two ways.** `containing_worktree` asks git, with `GIT_DISCOVERY_ACROSS_FILESYSTEM=1`. If git cannot answer (dubious ownership, filesystem boundary, not installed), it falls back to a filesystem walk for `.git`, instead of concluding "outside every repository".
  - **The guard fails closed.** `check_data_dir_safe` always adds the harness's own checkouts. It probes the directory itself (with a trailing slash) as well as `.json` and `.csv` files under it. Any `git check-ignore` result other than "ignored" or "not ignored" is a refusal.
  - **Provenance.** `code_version()` reports `nogit` unless the imported package is the `src/` tree of the checkout it found. A wheel installed into a venv that sits inside some checkout no longer borrows that checkout's SHA.
- **Why:** the round-2 review showed both a data dir reported as safe because git errored out, and a partly ignored directory passing the probes.
