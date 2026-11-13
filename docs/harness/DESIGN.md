# Harness design

Status: **M0 (scaffolding) complete, after one adversarial review round.** This
document describes the whole Phase 0 harness. Each section says which milestone
implements it; anything marked M1–M5 is design intent, not yet code. Decisions are
numbered `D-…` in [DECISIONS.md](DECISIONS.md).

## 1. What the harness must guarantee

The paper's credibility rests on the harness more than on the model. We assume a
reviewer from a quant firm will try to break it. Their usual attacks are:

| Attack | Defence | Where | Status |
|---|---|---|---|
| Data or keys leaked into a public repo | `.gitignore`, a git-aware data-dir guard, and hygiene tests that know this project's key formats | `.gitignore`, `paths.check_data_dir_safe`, `tests/test_repo_hygiene.py` | M0 ✅ |
| Secrets in logs, tracebacks or terminal output | Credentials read from env only, record-level and output-level redaction, Typer locals off, CLI output escaped | `settings.py`, `log.py`, `cli.py` | M0 ✅ |
| Tests that quietly hit live APIs | No-network namespace in CI, an audit-hook guard, a kill switch, and `--run-integration` gating | `tests/conftest.py`, `.github/workflows/ci.yml`, `net.py` | M0 ✅ |
| Moving the goalposts (endpoint changed after seeing results) | Endpoint-bundle fingerprint pinned in code, checked at runtime and in tests; `draft → locked` requires every field decided | `preregistration.py`, `configs/endpoint.yaml` | M0 ✅ (gate M3) |
| Downloading terabytes by accident | The fetch template enforces estimate → kill switch → data-dir guard → credentials → `--max-gb`/`--yes` | `sources/base.SourceAdapter.fetch` | M0 ✅ (adapters M1) |
| Look-ahead in features | Every row carries `knowledge_time`; as-of queries filter on it; a planted-violation test must fail | `store/` | M2 |
| Survivorship bias | Delisted names kept; a point-in-time security master; a known-answer test showing that dropping delisted names inflates returns | `sources/`, `universe/`, `evaluate/` | M1–M4 |
| Universe look-ahead | Membership for month *m* uses only data knowable before *m*, on raw unadjusted prices | `universe/` | M3 |
| Label leakage across folds | Walk-forward splits; purge and embargo ≥ the last label session, also at period boundaries; test that no training label window overlaps a test window | `splits/` | M3 |
| Peeking at the test set | Locked-period rows are quarantined at the storage/query layer, not only labels; reads need an `UnlockToken` and are logged | `store/`, `splits/`, `registry/` | M2–M5 (D-017) |
| Fitting transforms on the full sample | Scalers, PCA and peer sets take an explicit training window; the API has no "fit on everything" path | `evaluate/`, `labels/` | M3–M4 |
| p-hacking across many comparisons | Decision rule pre-registered (statistic, alpha, bootstrap, Holm family); append-only run registry | `configs/endpoint.yaml`, `evaluate/`, `registry/` | M0 (spec) / M4–M5 |

## 2. Data flow

```
 sources/<name>.py  plan() ──► fetch(): estimate → MJ_OFFLINE → data-dir guard
        │                               → credentials → --max-gb/--yes → _download()
        ▼
 $MJ_DATA_DIR/raw/<source>/...         write-once landing zone (bytes exactly as fetched;
 $MJ_DATA_DIR/manifests/<source>/      a changed remote object gets a new path); one manifest
        │                              per fetch: files, sizes, sha256, remote version, URL,
        │                              fetch time, structured code version
        │ normalize()
        ▼
 $MJ_DATA_DIR/pit/<table>/*.parquet    event_time, knowledge_time, source, ingested_at [, asset_id]
        │                              + lineage (input fetch ids, sha256, code version)
        ▼
 in-memory DuckDB views (per process)  as-of helpers (knowledge_time <= t); rows on or after
        │                              2022-01-01 excluded unless an UnlockToken is held
        ├──► universe/   monthly top-N by prior-month dollar volume, raw close > $5 (PIT only)
        ├──► labels/     forward returns, 5-day realized covariance, event windows
        ▼                (dated by the last session of their window)
 splits/   walk-forward folds, purge/embargo ≥ last label session, locked-test gate
        ▼
 evaluate/ prediction contract → metrics → baselines → paired block bootstrap
        ▼
 registry/ append-only: bundle + config fingerprints, git SHA, data snapshot hashes,
           metrics, every locked-test read
```

## 3. Package layout

| Module | Responsibility | Milestone |
|---|---|---|
| `settings.py` | Environment-only settings: `MJ_DATA_DIR`, `MJ_CONFIG_DIR`, log options, credentials (`SecretStr`) | M0 |
| `config.py` | Strict YAML schemas for the five configs, cross-file checks, fingerprints | M0 |
| `preregistration.py` | Endpoint-bundle fingerprint, the pin, `verify_…`/`require_locked_preregistration` | M0 |
| `log.py` | UTC logging, text or JSON; record-level and output-level secret redaction | M0 |
| `net.py` | `MJ_OFFLINE` kill switch for the harness's own network code | M0 |
| `paths.py` | Data-dir layout; git-aware "not committable" guard | M0 |
| `provenance.py` | Package version, git SHA, conservative dirty flag | M0 |
| `sources/base.py` | Adapter contract, plan/manifest/lineage models, download guard, fetch template | M0 contract, M1 adapters |
| `store/` | Landing-zone writer, manifests, PIT Parquet tables, DuckDB views, as-of helpers, quarantine | M1–M2 |
| `universe/`, `labels/`, `splits/` | Universe builder, labels, walk-forward splits, locked-test gate | M3 |
| `evaluate/` | Prediction contract, metric registry, baselines, statistics, known-answer tests | M4 |
| `registry/` | Append-only run registry | M5 |
| `cli.py` | The `mjepa` command | M0 onward |

The brief's suggested layout is kept. Helper modules shared by every subpackage sit at
the package root (D-003).

## 4. Point-in-time contract (M2 implements; M0 fixes the vocabulary)

Every normalized table has `event_time`, `knowledge_time`, `source` and `ingested_at`,
plus `asset_id` where relevant (`sources.base.PIT_COLUMNS`).

* **Timestamps** are timezone-aware UTC (`Datetime(us, UTC)` in Polars, `TIMESTAMPTZ` in
  DuckDB). Trading dates are calendar dates in `America/New_York` on the XNYS calendar.
  Naive datetimes are banned by lint (ruff `DTZ`), and contract models normalise inputs
  to UTC.
* **`event_time`** is the period the value describes, for example the session date of a
  daily bar or the reference month of a CPI print.
* **`knowledge_time`** is when a market participant could first know the value. The
  research ([DATA_SOURCES.md](DATA_SOURCES.md)) refines each source; the conservative
  defaults are:
  * **daily bar:** that session's close, using the early-close time where one applies.
    Massive's daily *volume* includes extended-hours trades, so volume fields become
    known at the end of extended hours.
  * **filing:** EDGAR `acceptanceDateTime`, which is true UTC (checked against SGML
    headers). If `filingDate` is later than the ET acceptance date, the filing was not
    disseminated until the next EDGAR business day. Acceptance times before 2002 are
    midnight placeholders, so only the date is known.
  * **macro release:** the actual release timestamp from the committed calendars. For
    daily rate series, the publication time of the primary source.
  * **revised series:** the vintage date, where vintages exist.
* **As-of rule:** a decision at time *t* may use only rows with `knowledge_time <= t`.
  For revised series, use the latest vintage known at *t*.
* **Fitted transforms** (scalers, PCA, peer sets) are fit inside each fold's training window.
* **Approximations:** wherever true PIT data is unavailable, DATA_SOURCES.md
  ("Point-in-time approximations") records the approximation. When unsure, take the
  more conservative (later) knowledge time and log it.

M2's acceptance test plants a row with `knowledge_time > t` and requires the as-of query
to exclude it, and a deliberately broken query to be caught.

## 5. Landing zone, manifests and idempotency (contract M0, writer M1; D-019)

1. **`plan()` lists remote objects** with exact sizes where a listing gives them and
   estimates otherwise. It records each object's remote version: HF commit SHA, S3
   ETag, Last-Modified. Objects already present with the same version and checksum are
   `already_present`, so a re-run plans zero bytes.
2. **`_download()` streams to `tmp/`**, resuming with HTTP Range where supported. It
   verifies size and SHA-256, then atomically renames the file into `raw/<source>/`.
3. **`raw/` is write-once.** A changed remote object, for example a Massive flat file
   replaced without notice, is stored under a new path. It never overwrites bytes an
   older manifest points to.
4. **The manifest is written last,** atomically, and is the commit marker. It lists
   the full state of its request; files kept from earlier fetches carry
   `origin_fetch_id`. A raw file with no manifest entry is untrusted.
5. **Remote URIs and request values are credential-free** (validated).
   `strip_credentials()` produces the recordable form of a URL, such as FRED's, that
   needs a key parameter.
6. **Source-specific facts go in `ManifestEntry.attributes`,** for example
   `quote_size_convention` for Massive quotes (round lots versus shares, after
   2025-11-03).

## 6. Fetching: the template method, the guard and rate limits (D-018)

Adapters implement `plan`, `_download` and `normalize`. `SourceAdapter.fetch` is
concrete and always runs these steps in order:

1. print `format_estimate(plan)`: files, GB, the count of unknown-size files, time;
2. `require_network` (fails when `MJ_OFFLINE=1`);
3. `check_data_dir_safe` (git-aware: symlinks, case variants, sibling checkouts);
4. missing credentials, from `required_env`;
5. `check_download_budget`. It refuses above `--max-gb` (default 2, decimal GB)
   without `--yes`, refuses any plan with files of unknown size without `--yes`, and
   refuses on missing credentials even with `--yes`.

Only then does it call `_download(ApprovedPlan)`.

From M1, each source gets a token-bucket rate limiter and exponential backoff with
jitter that honours `Retry-After`. Limits from the research:
- Hugging Face: 500 API calls per 5 min anonymous (1,000 with a token).
- SEC: ≤ 10 req/s across *all* machines; we use ≤ 5.
- FRED: 120 req/min.
- BLS and Fed pages: ≥ 2 s between requests, with a contact User-Agent.
- Massive and crypto venues: per their documentation.

## 7. Configs and the pre-registered endpoint (D-007, D-016)

* **Five YAML files** in `configs/`, validated by frozen, `extra="forbid"`, strict
  pydantic models. The YAML loader rejects duplicate keys and unsafe tags. Malformed
  values raise `ConfigError`.
* **Cross-file checks:**
  * the endpoint's universe equals `universe.yaml`;
  * its period equals `splits.periods.locked_test`;
  * the label horizon is ≥ the endpoint's last label session;
  * its event types exist in `events.yaml`.
* **The pin covers a bundle:** the parsed `endpoint.yaml`, the parsed `splits.yaml`,
  and the SHA-256 of every event calendar the endpoint scores. It is
  `preregistration.PREREGISTERED_BUNDLE_FINGERPRINT`. `mjepa doctor` FAILs on a mismatch,
  tests require DECISIONS.md to cite the pinned value, and the M3 unlock gate calls
  `require_locked_preregistration`.
* **What the endpoint pins:**
  * the brief's sentence verbatim;
  * the loss by formula: inverse Stein, `tr(H⁻¹S) + logdet H` on the 5-day-sum scale;
  * the target;
  * the universe rules;
  * the event-level rules;
  * the decision rule.
* **Open fields:** ten fields are deliberately `null` (undecided). The schema refuses
  `status: locked` until every field is decided (D-016, D-027).

## 8. Locked test period: quarantine at the storage layer (M2–M5; D-017)

* **What is quarantined.** Every `pit/` row in every table whose `event_time` or
  `knowledge_time` is on or after 2022-01-01 is locked-period data: bars of every
  frequency, filings, features and names outside the universe, not only labels. All of
  it is excluded from the default views and as-of helpers. Otherwise locked targets
  could be recomputed from open daily bars. Exceptions must be listed in DECISIONS.md.
* **How locked data is read.** Only with an `UnlockToken`, minted by the
  `--unlock-test` path. It is issued only after `require_locked_preregistration` passes
  *and* an append-only registry record is written. Locked-period forecasting and
  scoring both run inside that path.
* **Label dating.** Labels are dated by the last session of their window. Purge and
  embargo also apply at the train/tune and tune/locked boundaries.
* **No tuning on locked data.** The tuning API accepts only train and tune folds.
* **Unlock conditions.** The unlock gate also requires a clean commit and the
  repository's own `configs/` (D-027).
* **Planted test.** A 2022 daily bar, a 2022 minute bar, a bar of a name outside the
  universe and a feature row must all be invisible to ordinary queries and to the
  tuning API.

## 9. Secrets and logging (D-005, D-025)

* Credentials come from environment variables only (`settings.CREDENTIAL_ENV_VARS`).
  A local `.env` is loaded by the user with `uv run --env-file .env`; the code never
  reads it.
* **Record level.** A LogRecord factory scrubs every record when it is created:
  message, arguments, exception text and stack info. It works for any handler,
  pytest's captured logs included. A call with mismatched arguments never dumps them.
  `extra=` fields are attached after the factory runs, so never put secrets there.
* **Output level.** The CLI's handler scrubs the final text again. Both layers remove:
  * registered credential values and their URL-encoded forms;
  * `api_key=`-style assignments, with underscore prefixes such as `FRED_API_KEY=`;
  * `Authorization: Bearer` values;
  * `hf_…` tokens and AWS key ids.
* **CLI output.** Error messages and table cells are redacted and markup-escaped.
  Typer's pretty tracebacks, which print local variables, are off. `main()` logs
  unexpected errors through the redactor.
* **Third-party loggers.** Loggers that print full URLs are raised to WARNING. Ruff `G`
  and `PLE` rules lint logging calls.

## 10. Testing strategy (D-009, D-024)

* **Unit tests never touch the network.** Layers, strongest first:
  1. **CI on Linux** runs them in a network namespace with no network.
  2. **Audit hook.** A `sys.addaudithook` guard blocks non-AF_UNIX `socket.connect`,
     `sendto`/`sendmsg` and all name resolution. It also covers the C `_socket`
     module, `ssl`, `asyncio` and `urllib`.
  3. **Native fallbacks.** Remote PyArrow filesystems are blocked. `MJ_OFFLINE=1`
     stops the harness's own fetch path. Proxy variables point at a closed port, and
     Hugging Face runs offline.
* **Integration tests** carry `@pytest.mark.integration` and run only with
  `--run-integration`; a `-m` filter alone cannot select them. They call
  `require_env(...)` and skip when credentials are missing.
* **Unit tests run isolated:** credentials scrubbed, `MJ_DATA_DIR` in a temp dir,
  hermetic git (no global or system config, so no signing prompts and no global
  excludes).
* **Fixtures are synthetic**, generated in code. No data files are committed.
* **Meta-tests** run throwaway suites with the repo's real pytest config, to prove the
  guard and the integration gating.
* **Guard tests** cover hygiene, pre-registration, the download guard, the fetch
  template, data-dir safety and provenance.
* **Known-answer and planted-violation tests** arrive with M2–M4. They include
  E[L(cΣ)] being minimised at c = 1 for the inverse-Stein loss. Paired differences are
  checked rather than "oracle ≈ 0" when the target is a realized proxy. The brief's
  QLIKE is the univariate per-asset and per-portfolio loss, a separate metric from the
  endpoint's full-matrix loss.
* **CI** runs ruff, mypy `--strict` and pytest on x86_64 Linux, aarch64 Linux (Ubuntu
  24.04, like the DGX Spark) and arm64 macOS. Actions are pinned by SHA, and uv and
  CPython are pinned.

## 11. Known limitations and caveats

* **Network guard, local runs.** Outside CI, native code that ignores proxy variables
  (`pyarrow.fs.FileSystem.from_uri("s3://…")`) and child processes are not blocked.
  Only the CI network namespace is airtight.
* **Redaction is defence in depth.** Code must still never format credentials into
  messages or URLs it logs.
* **Numerics differ across machines.** NumPy wheels use Apple Accelerate on macOS ≥ 14
  and OpenBLAS on Linux. Covariance results are therefore not bitwise identical between
  the Macs and the DGX, so M4 known-answer tests use tolerances.
* **Time zones.** Time-zone data can differ between machines (system tz database vs
  `tzdata` vs DuckDB's ICU). M2 adds a test that session-close UTC offsets agree across
  Python, Polars and DuckDB, and the registry records tz versions.
* **DuckDB connections** must set `autoinstall_known_extensions=false`,
  `autoload_known_extensions=false`, `TimeZone='UTC'` and `Calendar='gregorian'`
  (D-021).
* **Calendars.** Config paths for calendars point at files that M1 creates. Until then
  the pre-registration bundle records them as missing.
