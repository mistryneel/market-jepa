# Evaluation suite for the market world model paper

This folder holds the evaluation catalogue for our paper on a JEPA-style, event-conditioned market world model. Every source was opened on 2026-11-12, and nothing is cited from memory.

| File | What it holds |
|---|---|
| [`catalogue.yaml`](catalogue.yaml) | 125 entries (metrics, protocols, tests, baselines, benchmarks, datasets) in the brief's schema plus the extensions in [section 6](#6-schema-extensions). This is what the harness implements. |
| [`README.md`](README.md) | This report: the recommended suite, the primary-endpoint verdict, reviewer questions, disagreements and gaps. |
| [`benchmarks.md`](benchmarks.md) | Comparison of public benchmarks and datasets. |
| [`references.md`](references.md) | All 228 sources, with URL, type and read depth, grouped by category. |
| [`CANDIDATES.md`](CANDIDATES.md) | Checkpoint 1: the reviewed candidate list and seed-source verification. |
| [`PROGRESS.md`](PROGRESS.md) | Checkpoint 2: counts, top-10 must-haves and open questions. |

## At a glance

- **The primary endpoint survives in spirit but not in form.** As written, the Stein loss of a 5-day realized covariance is infinite for every model (rank ≤ 5 for ~500 stocks). The better-supported alternative is its computable, proxy-robust form, the per-asset Gaussian negative log-likelihood. It ranks models exactly as Stein would wherever Stein is finite. See [section 1](#1-primary-endpoint-confirmed-in-spirit-redefined-in-form).
- **The suite:** 39 must-haves, 42 should-haves and 28 nice-to-haves, plus 16 benchmarks kept only as related work. Every must-have has at least two opened sources or is canonical with its original paper cited.
- **The three biggest risks:**
  1. **Statistical power.** The test window has 89 events on 88 distinct origins, and 19 FOMC–CPI pairs fall within a week of each other.
  2. **H2 ambiguity.** The brief's wording supports several contrasts, and the right test depends on which.
  3. **Leakage.** Pretrained components (Kronos, LLM encoders, our own encoder) may have seen the test years.

## 1. Primary endpoint: confirmed in spirit, redefined in form

**What the brief proposed.** The mean Stein loss of 5-day covariance forecasts over trading days 1–5 after each scheduled FOMC and CPI announcement. Top 500 US stocks by prior-month dollar volume (price > $5), test period 2022 to mid-2026, paired by event, block bootstrap by month.

**Why it cannot be computed as written.** Σ* = (1/5) Σ_d r_d r_d′ has rank at most 5. So log det Σ* = −∞, and Stein = tr(Σ*Σ̂⁻¹) − log det(Σ*Σ̂⁻¹) − n = +∞ for every positive-definite forecast. Five-minute data gives at most 390 returns over 5 days, still fewer than 500 stocks. ([`stein_loss`](catalogue.yaml), [`realized_covariance_target`](catalogue.yaml))

**The better-supported alternative: score the forecast-dependent part.**

L = (1/n)[log det Σ̂ + tr(Σ̂⁻¹Σ*)]   (Gaussian NLL / multivariate QLIKE, forecast inverted)

Why it holds up:
- Stein = n·L − (log det Σ* + n). Paired model differences in L therefore equal Stein differences divided by n, wherever Stein is finite.
- L is affine in Σ*. If the target is conditionally unbiased for the forecast's own horizon and scale, expected-loss rankings match rankings under the true covariance, whatever the rank of Σ*.
- It belongs to the robust loss class of Patton & Sheppard (2009) and Laurent, Rombouts & Violante (2013). Bollerslev, Patton & Quaedvlieg (2018) use it for realized-covariance forecasts. It is the Dawid–Sebastiani score of Gneiting & Raftery (2007), and Johansson et al. (2023) evaluate covariance predictors by the same Gaussian likelihood.
- **One caveat is our own inference.** Laurent et al. prove robustness only for positive-definite proxies; the singular-proxy case follows from linearity.
- Orientation matters. The statistics orientation, which inverts the true matrix (Ledoit & Wolf 2018, 2022), is not ranking-robust and rewards understating risk.

**What else must be pre-specified:**
- **Positive-definiteness.** One repair rule applies to every forecast: an eigenvalue floor at ε·mean eigenvalue, with ε frozen on pre-2022 data. A non-PD forecast counts as a failure, never a silent fallback. At n ≈ 500, naive and EWMA baselines are singular, so the rule matters.
- **Event timing.**
  - CPI is released at 08:30 ET, before the open; FOMC statements come out at 14:00 ET.
  - In interest-rate futures, covariance jumps are identified within about 90 minutes of the release. VaR failures around FOMC cluster on day +1, and day −1 is not a clean baseline.
  - Report day −1, day 0, each of days 1–5, and the cumulative loss.
- **H2's contrast and estimand** (see the defaults table).
- **Power.** The window holds 36 scheduled FOMC decisions and 53 CPI releases, and 19 CPI–FOMC pairs fall within 7 calendar days. The documented announcement-day volatility uplift is only about 4–10%. Compute a minimum detectable effect from pre-2022 per-event NLL differences before unlocking the test set ([`power_mde`](catalogue.yaml)).
- **Co-primary for H1.** Use realized GMV variance, which is defined even when Σ* is singular and is the loss Ledoit and Wolf argue matters for portfolios. It ignores the forecast's scale, so pair it with the calibration ratio, and pool per-event log ratios against a baseline.

### Recommended defaults, pending your decision

The catalogue is written against these defaults. Each is flagged as an open decision in [`PROGRESS.md`](PROGRESS.md).

| Decision | Default adopted | Main alternative |
|---|---|---|
| Primary loss | Per-asset Gaussian NLL, (1/n)[log det Σ̂ + tr(Σ̂⁻¹Σ*)], with Σ* the mean of 5 uncentred daily outer products | Full Stein with a full-rank intraday target (needs ≥ 100 synchronized returns a day; ill-conditioned and noisy) |
| PD repair | Eigenvalue floor at ε·mean eigenvalue, ε frozen on pre-2022 validation | Shrinkage of every forecast toward a diagonal target |
| Forecast origin | Close of announcement day 0, target days 1–5 (surprises may be inputs) | Close of day −1, target days 0–5 (inputs ex ante only); reported as a secondary |
| H2 design | 2×2 (pretrained vs supervised) × (with vs without events). Primary: the pretrained model's event-input gain (nested; Giacomini–White on fixed-length rolling refits). Key secondary: pretrained+events vs supervised+events. | Make the non-nested comparison primary |
| H2 estimand | Post-event paired NLL difference, with the matched non-event difference-in-differences as a required secondary | Make the difference-in-differences primary |
| H1 | Per-asset NLL and realized GMV variance are co-primary on ordinary days. H1 holds only if both are non-inferior to every member of the strong set (DCC-NL, QIS shrinkage, a fundamental factor model, EWMA). This is an intersection–union rule, one-sided 5% each, needing no multiplicity adjustment. Margins come from pre-2022 validation: half the EWMA-to-best NLL gap, and a 5% variance tolerance. | NLL only, or Holm if success on either co-primary should count |
| Ordinary days (H1) | Origins with no FOMC/CPI day 0 in days −1 to +5. Stocks with their own earnings in the target window are dropped from that origin. | Exclude the origin day only |
| Primary test | One-sided paired month-cluster bootstrap at 5%, with DM-HLN and GW as sensitivity analyses | DM-HLN as primary |
| Test window | Locked 1 Jan 2022 – 30 Jun 2026; pre-2022 walk-forward events as a secondary analysis for power | Locked window only |
| Sign and unit | Every paired contrast is a gain, reference minus candidate (positive favours the candidate). The pooled unit is the event origin: 88 origins, since CPI and FOMC share 12 Jun 2024. | — |
| Refits | Fixed-length 10-year rolling windows, refit every six months for every arm, encoder pretraining included. Each fit's data end at least 5 trading days before its first forecast. Fallback: freeze all arms' encoders and claim only a comparison of fitted forecasters. | Expanding windows (then Giacomini–White does not apply) |
| Tuning | All tuning, margins and power inputs use the 2017–2021 validation period with the same walk-forward procedure | — |
| Universe | Top 500 common stocks by prior-month dollar volume, price above $5, one share class per issuer, and a 1,260-day return history (as in De Nard et al. 2021). Delisting returns are kept, with zero returns after delisting. | No history requirement, with per-estimator handling of short histories |
| Failures | A non-PD forecast after repair is a failure. A candidate failure voids that claim; a reference failure drops the origin from that contrast only. | — |

## 2. Recommended evaluation suite

Levels follow each entry's `relevance` field: ● high, ◐ medium, ○ low, blank none. PE marks entries that bear on the primary endpoint. "Sources" counts distinct opened sources in `used_by`; "orig." marks a canonical entry whose original paper is cited.

### 2.1 Must-have

| Entry | What it is | H1 | H2 | H3 | H4 | PE | Status | Sources |
|---|---|:-:|:-:|:-:|:-:|:-:|---|---|
| `stein_loss` | Stein loss (Gaussian KL), scored through its computable form: per-asset Gaussian NLL / multiva… | ● | ● | ◐ | ○ | ✓ | canonical | 11 (orig.) |
| `robust_loss_class` | Loss robustness to a noisy realized proxy (rule for choosing ranking losses) | ● | ● | ◐ | ○ | ✓ | canonical | 9 (orig.) |
| `realized_covariance_target` | Realized covariance target: conventions for Σ* (daily outer products; intraday variants as sen… | ● | ● | ● | ◐ | ✓ | canonical | 12 (orig.) |
| `gmv_realized_variance` | Realized variance of the global-minimum-variance (GMV) portfolio | ● | ◐ | ◐ |  | ✓ | widely used | 11 |
| `risk_calibration_ratio` | Calibration ratio: realized ÷ predicted portfolio variance | ◐ | ● | ◐ | ○ |  | widely used | 6 |
| `model_confidence_set` | Model Confidence Set (Hansen–Lunde–Nason) | ● | ◐ | ◐ |  |  | canonical | 5 (orig.) |
| `ledoit_wolf_linear` | Ledoit–Wolf linear shrinkage (identity, constant-correlation and single-index targets) | ◐ | ◐ | ◐ |  | ✓ | canonical | 9 (orig.) |
| `nonlinear_shrinkage` | Nonlinear shrinkage: analytical NLS (Ledoit–Wolf 2020) and quadratic-inverse shrinkage QIS (Le… | ● | ◐ | ◐ |  | ✓ | canonical | 6 (orig.) |
| `ewma_riskmetrics` | EWMA / RiskMetrics covariance (RiskMetrics λ = 0.94 and a validation-tuned λ) | ● | ● | ◐ | ○ | ✓ | canonical | 5 (orig.) |
| `dcc_family` | DCC-GARCH family: DCC-NL for n ≈ 500; CCC and DCC for small-n checks | ● | ● | ◐ | ○ | ✓ | canonical | 6 (orig.) |
| `factor_risk_models` | Factor-model covariance: statistical (PCA, POET), characteristic-based (IPCA) and fundamental… | ● | ● | ◐ |  | ✓ | canonical | 6 (orig.) |
| `naive_persistence` | Naive persistence: trailing sample covariance and lagged 5-day realized covariance | ◐ | ● | ◐ | ◐ | ✓ | widely used | 7 |
| `event_scaled_baseline` | Event-scaled baseline: strongest event-blind forecast times per-event-type variance multiplier… |  | ● | ○ | ○ | ✓ | our design | 4 |
| `rank_ic` | Cross-sectional information coefficient per date: Pearson IC and Spearman rank IC |  | ○ | ○ | ◐ |  | widely used | 9 |
| `untrained_encoder_floor` | Untrained (random-initialisation) encoder floor read out with the same head | ● | ● | ◐ | ○ |  | emerging | 4 |
| `matched_supervised_comparator` | Equal-capacity supervised comparator with matched inputs, readout and budget (the supervised a… | ◐ | ● | ○ |  |  | widely used | 7 |
| `transfer_protocol` | Equities-to-crypto transfer protocol: zero-shot vs frozen transfer vs fine-tuned vs from scrat… |  | ○ | ● |  |  | widely used | 7 |
| `event_timing_origin` | Event window, forecast origin and day-by-day loss profile | ◐ | ● | ○ | ◐ | ✓ | our design | 11 |
| `earnings_event_handling` | Earnings events: point-in-time announcement timestamps, own-stock earnings windows, results wi… | ● | ● |  | ○ | ✓ | our design | 4 |
| `event_level_inference` | Event-level (calendar-time) inference for clustered events | ◐ | ● | ○ | ◐ | ✓ | canonical | 4 (orig.) |
| `event_vs_nonevent_did` | Event vs matched non-event gain (difference-in-differences) | ○ | ● |  |  |  | our design | 7 |
| `event_placebo` | Event-input permutation and placebo-date test |  | ● |  |  |  | our design | 4 |
| `walk_forward` | Walk-forward evaluation with fixed-length rolling refits (expanding window as a robustness che… | ● | ● | ◐ | ◐ | ✓ | widely used | 13 |
| `purged_cv_embargo` | Purging and embargo of overlapping labels (walk-forward edges, early-stopping blocks, CPCV) | ● | ● | ◐ | ◐ | ✓ | canonical | 10 (orig.) |
| `locked_test_preregistration` | Separate tuning period, locked test window and pre-registration | ● | ● | ● | ◐ | ✓ | widely used | 9 |
| `baseline_tuning_parity` | Same validation data, logged tuning budget and post-processing for every baseline | ● | ● | ◐ | ○ | ✓ | our design | 7 |
| `seed_vs_period` | Uncertainty across time periods vs across training seeds | ● | ● | ◐ | ◐ | ✓ | canonical | 9 (orig.) |
| `block_bootstrap` | Paired month-cluster bootstrap (deciding test) with a stationary-bootstrap sensitivity (Politi… | ● | ● | ◐ | ◐ | ✓ | canonical | 14 (orig.) |
| `diebold_mariano` | Diebold–Mariano test with HAC variance and the Harvey–Leybourne–Newbold correction | ◐ | ● | ◐ | ○ | ✓ | canonical | 11 (orig.) |
| `nested_model_tests` | Giacomini–White test for nested comparisons (Clark–West for squared-error scalar secondaries) | ○ | ● | ○ |  | ✓ | canonical | 5 (orig.) |
| `h1_noninferiority_test` | Non-inferiority (and equivalence) test for H1's 'matches strong risk models' | ● | ○ | ○ |  |  | our design | 9 |
| `multiple_testing` | Holm (FWER) and Benjamini–Hochberg (FDR) corrections with pre-registered families | ◐ | ● | ● | ● |  | canonical | 12 (orig.) |
| `power_mde` | Power and minimum-detectable-effect analysis from pre-2022 per-event NLL differences | ◐ | ● | ◐ | ○ | ✓ | emerging | 8 |
| `pit_universe_survivorship` | Survivorship-free, point-in-time universe with delisting returns | ● | ● | ◐ | ◐ | ✓ | canonical | 16 (orig.) |
| `forward_looking_panel_filter` | No forward-looking completeness filter on the 5-day target panel | ● | ● | ◐ | ◐ | ✓ | our design | 6 |
| `lookahead_revisions` | Look-ahead in features, timestamps and data revisions | ● | ● | ◐ | ● | ✓ | canonical | 16 (orig.) |
| `event_input_availability` | Event-input availability: each event feature carries an available-at time checked against the… | ○ | ● | ○ | ◐ | ✓ | our design | 12 |
| `pit_event_calendar` | Point-in-time event calendar: actual FOMC and CPI release dates and times, with moves and canc… | ● | ● | ◐ | ● | ✓ | reference | 5 |
| `pretraining_overlap_audit` | Pretraining-corpus overlap audit (foundation-model baselines and our encoder) | ● | ● | ● | ◐ | ✓ | emerging | 7 |

### 2.2 Should-have

| Entry | What it is | H1 | H2 | H3 | H4 | PE | Status | Sources |
|---|---|:-:|:-:|:-:|:-:|:-:|---|---|
| `qlike_univariate` | QLIKE on per-stock and fixed-portfolio variances | ◐ | ◐ | ◐ | ○ |  | canonical | 4 |
| `frobenius_distance` | Squared Frobenius distance (and vech-Euclidean variant) | ◐ | ○ | ○ |  |  | widely used | 8 |
| `eigen_spectrum_errors` | Eigenvalue/spectrum errors and correlation-geometry diagnostics (eigenportfolio realized-to-pr… | ◐ | ◐ | ○ | ○ |  | emerging | 5 |
| `relative_skill_reporting` | Report paired differences or skill relative to a stated baseline (not absolute loss levels) | ● | ● | ◐ | ○ | ✓ | widely used | 9 |
| `mv_loss` | Minimum-variance (MV) loss of Engle–Ledoit–Wolf | ◐ | ○ | ○ |  |  | canonical | 6 (orig.) |
| `lw_variance_test` | Test of equal out-of-sample portfolio variance (Ledoit–Wolf) | ◐ | ○ | ○ |  |  | canonical | 4 (orig.) |
| `min_tracking_error_variance` | Realized variance of the minimum-tracking-error portfolio vs a value-weighted benchmark | ◐ | ○ | ○ |  |  | canonical | 4 |
| `bias_statistic` | Bias statistic (SD of standardized returns), rolling bias, MRAD | ◐ | ◐ | ○ |  |  | canonical | 2 |
| `mincer_zarnowitz` | Mincer–Zarnowitz regression of realized on predicted portfolio variance | ◐ | ● | ○ |  |  | canonical | 5 (orig.) |
| `kupiec_pof` | Kupiec proportion-of-failures (unconditional coverage) VaR test with Basel traffic-light zones | ○ | ◐ | ○ |  |  | canonical | 5 (orig.) |
| `christoffersen_dq` | Christoffersen independence and conditional-coverage tests; Engle–Manganelli dynamic quantile… | ○ | ◐ | ○ | ○ |  | canonical | 5 (orig.) |
| `iterated_ewma` | Iterated EWMA (IEWMA) and combined multiple IEWMA (CM-IEWMA) | ◐ | ◐ | ◐ |  |  | emerging | 1 |
| `har_realized` | HAR realized-variance models: diagonal HAR per stock and the scalar vech-HAR | ◐ | ◐ | ◐ | ◐ |  | canonical | 4 (orig.) |
| `garch_univariate` | Univariate GARCH family (GARCH(1,1), GJR/threshold GARCH) and the GARCH-CCC covariance | ◐ | ◐ | ◐ | ◐ |  | canonical | 7 (orig.) |
| `implied_vol_baseline` | Implied-volatility-scaled covariance (VIX9D or VIX for equities; DVOL for crypto) | ○ | ● | ● | ○ | ✓ | our design | 4 |
| `icir` | IC information ratio: ICIR and Rank ICIR (mean over standard deviation of the per-date IC) |  | ○ | ○ | ○ |  | widely used | 5 |
| `newey_west_t` | Newey–West HAC standard errors and t-statistics with a pre-specified lag rule | ◐ | ◐ | ○ | ◐ | ✓ | canonical | 10 (orig.) |
| `net_sharpe` | After-cost (net) Sharpe ratio with a transaction-cost sweep | ○ |  | ○ |  |  | widely used | 16 |
| `turnover` | Portfolio turnover (two-sided, drift-adjusted) | ◐ | ○ | ○ |  |  | widely used | 6 |
| `ssl_objective_ablation` | SSL-objective ablation: JEPA vs masked reconstruction vs a contrastive objective on a fixed ba… | ◐ | ◐ | ○ | ○ |  | widely used | 7 |
| `incremental_value_test` | Incremental value of the latent over raw features, trailing volatility and the strongest basel… | ● | ◐ | ○ | ● |  | emerging | 7 |
| `linear_probe` | Frozen linear (ridge) probe protocol with a covariance-valued probe and control-task selectivi… | ● | ○ | ◐ | ○ |  | canonical | 10 (orig.) |
| `rankme_effective_rank` | Effective rank (RankMe) and collapse diagnostics (per-dimension spread, off-diagonal covarianc… | ◐ | ○ | ○ | ○ |  | canonical | 11 (orig.) |
| `factor_loading_recovery` | Recovery of statistical-factor loadings and of the factor subspace from stock embeddings (S1's… | ● | ○ | ○ |  |  | emerging | 3 |
| `label_efficiency` | Label-efficiency (training-sample) curve for the covariance head and its comparators | ◐ | ◐ | ● |  |  | emerging | 5 |
| `readout_sensitivity` | Readout sensitivity: pooling, token, layer and head capacity (linear vs small MLP) | ● | ◐ | ◐ | ○ |  | emerging | 9 |
| `abnormal_volatility` | Event-study abnormal returns, volatility and correlation | ○ | ● |  | ◐ |  | canonical | 10 (orig.) |
| `mp_surprise_hf` | High-frequency monetary-policy surprises (FOMC only) |  | ● |  | ○ |  | canonical | 14 (orig.) |
| `two_year_yield_change` | Change in the 2-year Treasury yield around FOMC |  | ◐ |  |  |  | canonical | 6 (orig.) |
| `cpi_surprise` | CPI surprise measure |  | ◐ |  | ○ |  | gap | 10 |
| `surprise_stratification` | Stratify by event type and surprise sign/size |  | ◐ |  | ○ |  | emerging | 7 |
| `surprise_leads_vol` | Model 'surprise' as a leading indicator of volatility jumps |  | ○ |  | ● |  | emerging | 5 |
| `trial_ledger` | Ledger of every configuration evaluated | ◐ | ◐ | ◐ | ◐ |  | emerging | 7 |
| `reality_check_spa_stepm` | White's Reality Check, Hansen's SPA and Romano–Wolf StepM | ◐ | ◐ | ○ | ○ |  | canonical | 6 (orig.) |
| `regime_reporting` | Report results by year and by volatility regime | ◐ | ● | ◐ | ◐ | ✓ | widely used | 10 |
| `llm_cutoff_leakage` | Knowledge-cutoff leakage in LLM-derived event inputs | ○ | ● | ○ | ○ | ✓ | widely used | 7 |
| `planted_leak_test` | Planted-leak positive control with a future-perturbation negative control | ◐ | ● | ◐ | ◐ | ✓ | emerging | 6 |
| `leakage_checklist` | Leakage taxonomy and model-info sheet, filled in and machine-checked | ◐ | ◐ | ◐ | ◐ |  | canonical | 4 (orig.) |
| `public_risk_benchmark_gap` | Public multivariate covariance-forecasting benchmark (none found) | ◐ | ◐ | ○ |  | ✓ | gap | 11 |
| `market_1t` | Market-1T dataset and evaluation protocol | ◐ | ○ |  |  |  | emerging | 2 |
| `binance_vision` | Binance Vision public market data (crypto) |  |  | ● |  |  | reference | 2 |
| `crsp_us_stock` | CRSP US Stock Databases (CIZ format) | ● | ● | ○ | ◐ | ✓ | reference | 6 |

### 2.3 Nice-to-have

| Entry | What it is | H1 | H2 | H3 | H4 | PE | Status | Sources |
|---|---|:-:|:-:|:-:|:-:|:-:|---|---|
| `mse_variance` | MSE on variance forecasts (per stock and fixed portfolios) | ○ | ○ | ○ |  |  | canonical | 3 |
| `bures_wasserstein` | Bures–Wasserstein distance | ○ | ○ | ○ |  |  | emerging | 4 |
| `loglik_regret` | Log-likelihood regret against the period's realized covariance | ○ |  | ○ |  |  | emerging | 1 |
| `eigenfactor_bias_test` | Eigenfactor (eigen-portfolio) bias test | ◐ | ○ | ○ |  |  | canonical | 3 |
| `erc_check` | Equal-risk-contribution (ERC) portfolio check | ○ | ○ | ○ |  |  | canonical | 4 (orig.) |
| `es_backtests` | Expected-shortfall backtests (Acerbi–Székely Z1/Z2, Du–Escanciano, McNeil–Frey) | ○ | ○ | ○ |  |  | canonical | 6 (orig.) |
| `comparative_backtest` | Comparative backtesting with strictly consistent scores and a three-zone decision | ◐ | ◐ | ○ |  |  | canonical | 4 |
| `rie_cleaning` | Rotation-invariant cleaning: RMT eigenvalue clipping, average oracle, and learned GMV-trained… | ◐ | ○ | ○ |  |  | widely used | 4 |
| `long_short_decile` | Long–short decile spread (top minus bottom decile of the forecast) |  | ○ | ○ |  |  | widely used | 6 |
| `max_drawdown` | Maximum drawdown of a strategy's cumulative value | ○ |  | ○ |  |  | widely used | 8 |
| `factor_neutral_ic` | Factor-neutralised rank IC (partial rank correlation after removing sector and style exposures) |  | ○ |  | ○ |  | our design | 3 |
| `deflated_sharpe` | Deflated Sharpe ratio (with the probabilistic Sharpe ratio) |  |  | ○ |  |  | canonical | 4 (orig.) |
| `r2_oos` | Out-of-sample R² of return forecasts against a stated benchmark forecast |  | ○ | ○ |  |  | canonical | 5 (orig.) |
| `knn_probe` | k-NN retrieval probe with temporal exclusion | ◐ | ○ | ○ | ○ |  | canonical | 3 (orig.) |
| `lidar` | LiDAR: effective rank of the whitened between-class scatter over views | ○ |  | ○ |  |  | emerging | 4 |
| `latent_organization_probes` | Latent-organisation probes (same day, same firm, same industry; sector separation and co-movem… | ○ |  | ○ |  |  | emerging | 3 |
| `cka` | Linear CKA representation similarity, debiased estimator primary | ○ |  | ◐ |  |  | canonical | 4 (orig.) |
| `covariance_jump_rank_test` | Rank test for announcement covariance jumps |  | ○ |  | ○ |  | emerging | 2 |
| `cpcv` | Combinatorial purged cross-validation (CPCV) | ○ | ○ | ○ | ○ |  | canonical | 2 (orig.) |
| `pbo_cscv` | Probability of backtest overfitting via combinatorially symmetric cross-validation (CSCV) | ○ | ◐ | ○ | ○ |  | canonical | 3 (orig.) |
| `volare` | VOLARE realized-measure archive | ○ | ○ |  | ○ | ✓ | reference | 1 |
| `m6_competition` | M6 forecasting competition |  |  |  |  |  | reference | 2 |
| `qlib_alpha158_alpha360` | Qlib benchmarks (Alpha158 and Alpha360 handlers, model zoo) |  |  |  |  |  | reference | 2 |
| `fintsb` | FinTSB financial time-series forecasting benchmark |  |  |  |  |  | reference | 1 |
| `gift_eval` | GIFT-Eval general time-series forecasting benchmark | ◐ | ○ | ◐ |  |  | reference | 3 |
| `fev_bench` | fev-bench (skill score, win rate and paired bootstrap aggregation) | ○ | ○ | ○ |  | ✓ | reference | 1 |
| `look_ahead_bench` | Look-Ahead-Bench (LLM look-ahead bias as trading-performance decay) |  | ◐ |  |  |  | emerging | 1 |
| `kaggle_gresearch_crypto` | Kaggle G-Research Crypto Forecasting (2021-22) |  |  | ○ |  |  | reference | 1 |

### 2.4 By hypothesis

Must-have entries rated high for each hypothesis, followed by the should-haves rated high.

- **Primary endpoint**: `stein_loss`, `robust_loss_class`, `realized_covariance_target`, `gmv_realized_variance`, `ledoit_wolf_linear`, `nonlinear_shrinkage`, `ewma_riskmetrics`, `dcc_family`, `factor_risk_models`, `naive_persistence`, `event_scaled_baseline`, `event_timing_origin`, `earnings_event_handling`, `event_level_inference`, `walk_forward`, `purged_cv_embargo`, `locked_test_preregistration`, `baseline_tuning_parity`, `seed_vs_period`, `block_bootstrap`, `diebold_mariano`, `nested_model_tests`, `power_mde`, `pit_universe_survivorship`, `forward_looking_panel_filter`, `lookahead_revisions`, `event_input_availability`, `pit_event_calendar`, `pretraining_overlap_audit`.
- **H1** (a pretrained latent plus a small covariance head matches strong risk models on ordinary days): must `stein_loss`, `robust_loss_class`, `realized_covariance_target`, `gmv_realized_variance`, `model_confidence_set`, `nonlinear_shrinkage`, `ewma_riskmetrics`, `dcc_family`, `factor_risk_models`, `untrained_encoder_floor`, `earnings_event_handling`, `walk_forward`, `purged_cv_embargo`, `locked_test_preregistration`, `baseline_tuning_parity`, `seed_vs_period`, `block_bootstrap`, `h1_noninferiority_test`, `pit_universe_survivorship`, `forward_looking_panel_filter`, `lookahead_revisions`, `pit_event_calendar`, `pretraining_overlap_audit`; should `relative_skill_reporting`, `incremental_value_test`, `linear_probe`, `factor_loading_recovery`, `readout_sensitivity`, `crsp_us_stock`.
- **H2** (adding event inputs lowers post-event loss versus an equally sized supervised model): must `stein_loss`, `robust_loss_class`, `realized_covariance_target`, `risk_calibration_ratio`, `ewma_riskmetrics`, `dcc_family`, `factor_risk_models`, `naive_persistence`, `event_scaled_baseline`, `untrained_encoder_floor`, `matched_supervised_comparator`, `event_timing_origin`, `earnings_event_handling`, `event_level_inference`, `event_vs_nonevent_did`, `event_placebo`, `walk_forward`, `purged_cv_embargo`, `locked_test_preregistration`, `baseline_tuning_parity`, `seed_vs_period`, `block_bootstrap`, `diebold_mariano`, `nested_model_tests`, `multiple_testing`, `power_mde`, `pit_universe_survivorship`, `forward_looking_panel_filter`, `lookahead_revisions`, `event_input_availability`, `pit_event_calendar`, `pretraining_overlap_audit`; should `relative_skill_reporting`, `mincer_zarnowitz`, `implied_vol_baseline`, `abnormal_volatility`, `mp_surprise_hf`, `regime_reporting`, `llm_cutoff_leakage`, `planted_leak_test`, `crsp_us_stock`.
- **H3** (pretraining on US equities transfers to crypto): must `realized_covariance_target`, `transfer_protocol`, `locked_test_preregistration`, `multiple_testing`, `pretraining_overlap_audit`; should `implied_vol_baseline`, `label_efficiency`, `binance_vision`.
- **H4** (the model's surprise leads volatility jumps): must `multiple_testing`, `lookahead_revisions`, `pit_event_calendar`; should `incremental_value_test`, `surprise_leads_vol`.

## 3. What a skeptical reviewer will ask

| Question | Why they will ask | Where the answer lives |
|---|---|---|
| "Stein loss on a 5-day covariance of 500 stocks is infinite. What did you compute?" | Rank ≤ 5 makes the brief's endpoint infinite. | `stein_loss`, `realized_covariance_target`, `robust_loss_class` |
| "Is your loss fooled by the noisy realized proxy?" | Only robust losses rank forecasts correctly against noisy proxies. | `robust_loss_class`, `qlike_univariate`, `frobenius_distance` |
| "Did you beat strong risk models, tuned as well as yours?" | Persistence and shrinkage are hard to beat at 5 days; seed papers handicapped their baselines. | `ledoit_wolf_linear`, `nonlinear_shrinkage`, `dcc_family`, `factor_risk_models`, `ewma_riskmetrics`, `naive_persistence`, `baseline_tuning_parity` |
| "Is the gain from pretraining, or just head capacity?" | Random encoders with fitted readouts matched many SSL methods in seed papers. | `untrained_encoder_floor`, `matched_supervised_comparator`, `ssl_objective_ablation` |
| "Is the gain specific to events?" | Generic gains look like event gains unless contrasted with non-event days. | `event_vs_nonevent_did`, `event_placebo`, `event_scaled_baseline`, `implied_vol_baseline` |
| "Are your tests valid for nested models, overlapping windows and clustered events?" | DM is undersized for nested models; all stocks share each event date. | `nested_model_tests`, `event_level_inference`, `block_bootstrap`, `diebold_mariano` |
| "How much power do 88 event origins give you?" | Short windows cannot certify moderate effects. | `power_mde`, `regime_reporting` |
| "Do portfolio outcomes agree with the matrix loss?" | Matrix losses and GMV rankings disagreed in three seed papers. | `gmv_realized_variance`, `mv_loss`, `lw_variance_test`, `min_tracking_error_variance` |
| "Is post-event risk calibrated, not just ranked?" | Risk models that meet coverage overall failed around FOMC. | `risk_calibration_ratio`, `bias_statistic`, `kupiec_pof`, `christoffersen_dq`, `mincer_zarnowitz` |
| "Does 'matches strong risk models' mean anything statistically?" | Failing to reject a difference is not evidence of a match. | `h1_noninferiority_test`, `model_confidence_set` |
| "Any survivorship, look-ahead, revision or timestamp leakage?" | A planted look-ahead oracle passed the deflated Sharpe ratio in a seed paper. | `pit_universe_survivorship`, `forward_looking_panel_filter`, `lookahead_revisions`, `event_input_availability`, `pit_event_calendar`, `planted_leak_test` |
| "Were your foundation-model baselines, or your own encoder, trained on the test years?" | Kronos was pretrained to June 2024. | `pretraining_overlap_audit`, `transfer_protocol` |
| "Could an LLM event encoder have memorized outcomes?" | Post-cutoff performance decays in LLM trading studies. | `llm_cutoff_leakage`, `look_ahead_bench` |
| "Is the spread across seeds or across periods?" | Split and period variance dominate seed variance. | `seed_vs_period` |
| "How many configurations did you try?" | Search inflates apparent skill. | `trial_ledger`, `reality_check_spa_stepm`, `pbo_cscv`, `multiple_testing` |
| "Is the representation any good, or collapsed?" | Rank metrics are not quality scores. | `linear_probe`, `rankme_effective_rank`, `latent_organization_probes`, `factor_loading_recovery` |
| "Does the 'surprise' lead volatility beyond persistence?" | Seed papers found it synchronous or weak. | `surprise_leads_vol`, `incremental_value_test` |
| "Is the return signal real after costs and factor exposure?" | Harness choices moved Sharpe more than models did. | `rank_ic`, `newey_west_t`, `net_sharpe`, `factor_neutral_ic`, `deflated_sharpe` |
| "Are the results just 2022?" | Period effects dominate metric variance. | `regime_reporting`, `walk_forward` |

## 4. Where the literature disagrees

- **Matrix losses vs portfolio losses.**
  - Ledoit and Wolf favour the minimum-variance loss, but show that the MV-optimal nonlinear shrinkage coincides with the Frobenius-optimal one.
  - Bongiorno et al. (2026) dispute that equivalence in practice and train directly on 5-day GMV variance.
  - Reis et al. (2026) use only Frobenius/Euclidean matrix losses plus long-only GMV variance; their Frobenius winner was not the lowest-variance model.
  - In CD-DFM (Alouadi & Lehalle 2026), Ledoit–Wolf has by far the worst Stein loss but GMV calibration as good as the proposed model's.
  - **Our position:** NLL as the primary endpoint, GMV co-primary for H1.
- **Stein's orientation.** Statistics papers invert the true matrix; econometrics papers invert the forecast. Only the latter is ranking-robust.
- **Pooling events.** Li, Todorov & Zhang (2024) argue that pooled event studies rest on a fragile homogeneity assumption; other papers pool by category. We report FOMC and CPI separately and pooled.
- **Do scheduled events move second moments?**
  - Covariance jumps appear in interest-rate futures (Li, Todorov & Zhang).
  - VaR failures appear around FOMC (Bui et al., abstract only).
  - An event-blind JEPA latent barely moved (Mahns et al.).
  - The daily volatility uplift is about 4% (Savor & Wilson) to 10% (Bernanke & Kuttner).
- **Effective rank as a health signal.** One study reads it as "no collapse". Others show it rising while usefulness falls, or lowest for the best forecasters. RankMe's authors restrict it to within-method comparisons.
- **Purged CV vs a single split.** Several papers purge or embargo, and one uses a single split. Bergmeir et al. (2018) show K-fold CV is valid for purely autoregressive models with uncorrelated errors.
- **One-day vs intraday policy surprises.** Hanson & Stein use 1–2-day changes in the 2-year yield; Nakamura & Steinsson show one-day windows add background noise.
- **Does JEPA-style pretraining help?**
  - STOCK-JEPA reports gains (3 runs, no tests).
  - The sign flips by backbone in Feng et al.
  - Many SSL methods fall below a random encoder in Market-1T.
  - There is little incremental value in Mahns et al., no trading edge in jepa-trader, and no gain over raw features in causal-jepa.
- **Does a foundation model's exposure to future data inflate accuracy?** Meyer et al. document inflated scores. A September 2026 preprint (abstract only) finds that later vintages reduced US forecast accuracy.
- **IC vs Sharpe** as the headline return metric, and **R² benchmarks** (zero vs historical mean).
- **Conventions:** centring and divisor of the realized covariance, variance vs volatility calibration ratios, squared vs unsquared Bures distance.

## 5. Gaps where no standard exists

- **No public benchmark for multivariate covariance forecasting.** 18 searches found none. The nearest items are VOLARE (an archive), M6 (return ranking) and Kaggle Optiver (univariate volatility). Releasing our event-window protocol (dates, identifiers, target construction, code) would fill this gap; CRSP and VIX data cannot be redistributed.
- **No free CPI consensus-surprise series.** The academic standard uses proprietary survey medians. We stratify CPI events by the size of the realized index move until a source is licensed.
- **No theory for singular proxies.** Robust-loss theory covers positive-definite proxies only. Applying it to a rank-5 target is our inference from linearity.
- **No academic definition of factor-neutralized IC.** We define one ([`factor_neutral_ic`](catalogue.yaml)).
- **No peer-reviewed planted-leak protocol in finance.** Our design borrows from LLM contamination tests and a 2026 preprint.
- **No standard design for event-specific gains** (event vs matched non-event difference-in-differences), and no standard non-inferiority margins for risk models.
- **No standard JEPA-specific representation diagnostic for markets.** LiDAR needs a definition of "views" of a market sample.
- **No LLM-leakage test designed for covariance targets.** Existing tests score returns or text.

## 6. Schema extensions

The brief invited extensions. Each is documented here and in the header of `catalogue.yaml`.

| Extension | Values | Why |
|---|---|---|
| `section` | A–G | Ties each entry to the brief's scope section. |
| `priority` | must, should, nice, drop | The recommended suite, so the harness can filter. |
| `status` values | adds `our_design`, `reference`, `gap` | `our_design`: a protocol we propose, with cited precedents but no literature standard. `reference`: a dataset or benchmark rather than a method. `gap`: no standard exists. |
| `status_note` | text | Why the status holds, and any change from the candidate list. |
| `category` values | adds `baseline`, `dataset` | Reference models and data sources are first-class entries the harness must build. |
| `computable_form` | LaTeX | The form to implement when the textbook formula cannot be computed (Stein). |
| `conventions` | text | Orientation, normalisation, centring, annualisation, lag and sidedness choices an implementer needs. |
| `related` | entry ids | Cross-references. |
| `used_by[].ref`, `source_type`, `read_depth`, `version_read`, `accessed` | — | Ties each source to `references.md` and records how deeply it was read and which version. |
| `used_by_papers`, `fit_for_us` | text | Benchmark-only additions for `benchmarks.md`. |

`verified: true` means every source in the entry's `used_by` was opened on 2026-11-12. Read depth is recorded per source, and derivations of our own are labelled as such in `conventions` or `status_note`.

## 7. How this was built and verified

- **Seven passes with research agents.**
  1. Eight read the 17 seed links.
  2. Nine opened the canonical originals and benchmark pages the brief names.
  3. Three followed further references and counted events from official calendars.
  4. Five reviewed the candidate list adversarially.
  5. Nine drafted the catalogue entries.
  6. Eight reviewed the drafted catalogue: formulas with numeric checks, source fidelity, new-source verification, implementability and completeness.
  7. Seven merged those findings into the final entries under one written set of global decisions: sign convention, pooled unit, bootstrap clusters, H1 rule, multiplicity, refits, tuning period, universe and failures.
- **Read depth and versions.** About a quarter of sources were read at abstract or metadata level, mostly because publishers returned HTTP 403. Read depth is recorded per source. Where an author copy or working paper was read instead of the published version, the source list says so.
- **Kaggle pages** render client-side, so competition details come from secondary write-ups.
- **Prompt injection, ignored.** Some OpenAlex API responses asked automated clients to register with the user's email address. The agent that saw them did not act on them, and no personal data was sent.
- **Not done here.** No metric was implemented in the repo (the brief forbids code). The numeric checks of formulas ran in a scratch environment outside the repository.
