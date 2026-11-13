# Human to-do

Things only a human can do: decisions, accounts, keys, purchases, terms and approvals.
The agent never signs up, buys, accepts terms or creates keys. Each item says what it
blocks. Tick items off as you go and note the date. Source details and links are in
[DATA_SOURCES.md](DATA_SOURCES.md); the proposed plan is DECISIONS.md D-026.

_Last updated 2026-11-12 (M0 checkpoint)._

## A. Licence decisions — these gate M1 downloads

1. **Massive (main equities source): get written permission before any training or evaluation use.**
   - **What the terms say.** Massive's Market Data Terms §5(g) (updated 2026-11-03) and Business ToS §6.1(j) forbid training, fine-tuning or distilling ML models on Massive data unless expressly permitted. Individual plans are personal, non-business and non-publishing only, and the data must be deleted when the licence ends.
   - **Ask Massive** (sales@massive.com / legal@massive.com) for an Order Form that expressly permits:
     - ML training and evaluation;
     - publishing derived results in a paper;
     - organisational (lab) use;
     - the history you need (back to 2003 for the train period);
     - keeping the data for replication.
   - **Plan choice.** Daily bars from before about 2016 need **Stocks Advanced** ($199/month, individual and personal use only, which is probably not permissible here) or **Stocks Business** ($2,499/month, or $1,999/month with a commitment, or $19,188/year). Starter and Developer have rolling 5- and 10-year windows, so they do not reach a training period that ends in 2018. Reference and corporate-action history (security master, splits, dividends) comes with every plan from Starter ($29/month), but the ML-training terms apply to it too.
   - **Blocks:** everything Massive in M1 (day aggregates, security master, corporate actions) and the market-1t rebuild.
2. **FRED/ALFRED: choose a path.**
   - **What the terms say.** The FRED Services Terms (in force since mid-2024) forbid using FRED content in connection with ML or deep-learning development, and the API terms forbid storing FRED content in a database.
   - **Option (a), recommended.** Approve primary sources instead:
     - Treasury Daily Par Yield Curve (CC0) for the 2-year and 10-year yields;
     - the NY Fed Markets API for EFFR (accept its terms of use yourself);
     - Board H.15 (public domain) as a cross-check.
   - **Option (b).** Ask the St. Louis Fed for written permission.
   - **VIX** (VIXCLS) is © Cboe. Submit a "Request to Use Cboe Content", or drop VIX from the feature set.
   - **Blocks:** the macro-series adapter.
3. **Market-1T Hugging Face subset: approve validation-only use.**
   - Download 2020-03 sparse: 2.50 GB, 132 files, ungated, no account needed.
   - Its licence tag is "other / derived-market-data" with no text, and the data derives from Massive. Ask fin-ai-lab (the authors) for the licence text, whether ML use is permitted, and the universe metadata (`metadata.parquet`).
   - The code that built the HF layouts (galilai-group/stable-finance) has **no licence**, so it is not vendored.
   - **Blocks:** the Market-1T adapter's one-month test.
4. **Crypto source.**
   - **Kraken** (recommended primary): Kraken's ToS §9 bars scripts and other automation without written consent. So either:
     - download the free OHLCVT archive yourself (5 parts, 9.55 GB; peak disk about 21 GB) and the harness ingests it from a local path; or
     - email marketdata@kraken.com for consent to scripted downloads and published aggregates.

     Kraken does not serve residents of Maine or New York; check that no team member is affected.
   - **Coinbase:** its Market Data Terms require prior written consent before Coinbase-derived numbers appear in the paper (marketdata@coinbase.com).
   - **Binance:** do **not** use it until counsel clears it. The Vision Dataset Terms are CC BY-NC-SA 4.0 and subject to Binance ToU eligibility, which excludes US persons.
   - **Blocks:** the crypto adapter.
5. **Is this project commercial or academic?** Binance (non-commercial licence), Coinbase, CoinGecko and Massive's individual-vs-business terms all depend on the answer.
6. **For counsel, full disclosure about M0:** while researching (2026-11-12), our research agents made small scripted metadata requests, with no data downloaded:
   - file listings on `data.binance.vision`, whose Vision Dataset Terms clause 1.4 says any access accepts the terms;
   - Kraken asset URLs, while ToS §9 bars automation without consent;
   - Massive's public flat-file listing pages;
   - Coinbase public API metadata.

   From M1 on, these sources are accessed only after the decisions above.

## B. Credentials (create only after the decisions in A)

Put them in your shell or a git-ignored `.env`, and load with `uv run --env-file .env …`. Never commit them.

- [ ] `SEC_USER_AGENT`: `"Name or Org contact@domain"` with a monitored email (SEC fair access). The same contact goes in the User-Agent for the BLS and Fed calendar scraper.
- [ ] `HF_TOKEN` (optional): a read-only token doubles Hugging Face's anonymous API budget.
- [ ] `FRED_API_KEY`: only if FRED permission is granted (A2).
- [ ] `MASSIVE_API_KEY`, `MASSIVE_S3_ACCESS_KEY_ID`, `MASSIVE_S3_SECRET_ACCESS_KEY`: after A1. Sign any exchange/subscriber agreements in the Massive dashboard first; unsigned agreements cause 403s on flat files.

## C. Endpoint pre-registration (before `status: locked`)

- [ ] Confirm or amend the PROPOSED definitions in `configs/endpoint.yaml` (DECISIONS D-008, D-016). The key ones:
  - inverse-Stein loss on the 5-day sum;
  - day 1 = the first session closing after the announcement;
  - assets missing returns in the window are dropped for every model;
  - one observation per announcement;
  - the decision rule.
- [ ] Decide the six open fields:
  - `universe.share_class_rule`
  - `universe.exchanges`
  - `universe.min_sessions_in_prior_month`
  - `definitions.refit_policy` (frozen at 2021-12-31, or re-estimated during the locked period?)
  - `decision_rule.bootstrap.scheme`
  - `decision_rule.bootstrap.block_length`
- [ ] Should unscheduled Fed actions be flagged as confounders? Two Sunday actions fall inside the locked period: 2023-03-12 and 2023-03-19.
- [ ] Confirm the proposed explicit train start, `2005-01-01`.

## D. Repository and tooling

- [ ] **Licence for the public repo.** It has none, so default copyright applies.
- [ ] **uv version.** Upgrade every machine to uv 0.13.x? If yes, I bump `uv_build`, `required-version`, the CI pin and the lock together. Otherwise keep 0.11.7 everywhere (D-023).
- [ ] **Python.** Stay on 3.12 (the current choice) or move to 3.13, which buys about a year under SPEC 0.
- [ ] **Branch merge.** `research/eval-catalogue` and `feat/harness-phase0` have unrelated root commits, so merging needs `git merge --allow-unrelated-histories` (D-014).
- [ ] **Commit signing.** My commits are signed through your 1Password SSH key, so 1Password must be unlocked when I commit. Alternatively, allow unsigned commits on this branch.
- [ ] **On the DGX Spark**, record `uname -m`, `ldd --version`, `getconf PAGESIZE` and `nvidia-smi` (RUNBOOK §1).
- [ ] Optional: enable the pre-commit hook (`git config core.hooksPath scripts/hooks`).
- [ ] Optional: enable Dependabot (github-actions, uv) and read-only default workflow permissions.

## E. M1 download approvals

| Download | Size | Needs |
|---|---|---|
| Market-1T 2020-03 sparse slice | 132 files, 2,502,351,803 B (above the 2 GB guard), ~2–7 min. The 2020-02 month (1.49 GB) fits under the guard but loses the DST and circuit-breaker checks | A3 approval, then `--yes` |
| Fed and BLS calendar pages | ~800–900 polite requests (≥ 2 s apart, 27–45 min); ~50 MB raw cache outside git; committed CSVs < 200 KB | contact User-Agent (B) |
| SEC EDGAR sample (3 CIKs + a few SGML headers) | ~10–20 requests, < 1 MB. Full backfill later in M1: ~1,500–2,500 CIKs (point-in-time universe), ~3–8k requests, 100–250 MB, 15–30 min | `SEC_USER_AGENT` |
| Board H.15 zip, NY Fed EFFR, Treasury par yields | ~4.3 MB + small; the Treasury endpoint is still to be identified | A2 option (a) |
| Kraken OHLCVT archive | 9.55 GB (33.6 GB unzipped; peak disk ~21 GB for hourly + daily) | A4: a manual download by you, or Kraken's consent |
| Massive day aggregates, full history | ~1–1.5 GB gzip, 5,737 files | A1 (permission + plan) and keys |
| market-1t one-day rebuild test (2020-08-03) | 4.19 GB download, ~6.4 GB on disk (allow 13 GB) | A1 with quotes flat files (Advanced/Business) and keys |
