# Progress: checkpoint 2

**Status:** the full catalogue is written, and work has stopped for your review. Branch `research/eval-catalogue`.

## Definition of done

- [x] **At least 40 verified entries:** 125 of 125 entries are verified: every cited source was opened on 2026-11-12, at least at record level. Read depth per source is in [`references.md`](references.md).
- [x] **Must-have sourcing:** Every must-have has at least two opened sources or is canonical with its original paper cited.
- [x] **Primary endpoint:** confirmed in spirit and challenged in form, with a better-supported alternative ([README section 1](README.md#1-primary-endpoint-confirmed-in-spirit-redefined-in-form)).
- [x] **`catalogue.yaml` parses:** checked with Ruby's built-in YAML parser as a one-off command; no code was added to the repo.

## Counts

228 distinct sources are cited.

### By category

| Category | Entries |
|---|---|
| protocol | 23 |
| benchmark | 20 |
| stat_test | 18 |
| risk_metric | 14 |
| baseline | 14 |
| dataset | 9 |
| return_metric | 8 |
| leakage_test | 7 |
| representation_metric | 6 |
| event_metric | 6 |
| **Total** | **125** |

### By status

| Status | Entries |
|---|---|
| canonical | 47 |
| reference | 26 |
| emerging | 20 |
| widely used | 19 |
| our design | 11 |
| gap | 2 |
| **Total** | **125** |

### By section

| Section | Entries |
|---|---|
| A | 36 |
| G | 28 |
| E | 16 |
| C | 14 |
| D | 12 |
| B | 10 |
| F | 9 |
| **Total** | **125** |

### By priority

| Priority | Entries |
|---|---|
| should | 42 |
| must | 39 |
| nice | 28 |
| drop | 16 |
| **Total** | **125** |

## Top-10 must-haves

1. **`stein_loss`:** the primary endpoint in computable form, the per-asset Gaussian NLL. The brief's Stein loss is infinite for a 5-day, 500-stock target.
2. **`realized_covariance_target`:** the endpoint is undefined until the target's return type, centring, divisor, overnight returns and delistings are fixed.
3. **`event_timing_origin`:** the forecast origin and day-by-day profile. CPI lands before the open and FOMC at 14:00 ET, and failures cluster on day +1.
4. **`block_bootstrap`:** the primary inference, a paired month-cluster bootstrap of per-event NLL differences.
5. **`nested_model_tests`:** Giacomini–White on fixed-length rolling refits for the nested H2 contrast. DM is undersized there, and Clark–West does not apply to this loss.
6. **`event_vs_nonevent_did`:** separates event-specific gains from generic ones, which is the heart of H2.
7. **`power_mde`:** 89 events on 88 origins, 19 CPI–FOMC pairs within a week, and a modest documented uplift. Size the effect before unlocking the test set.
8. **`gmv_realized_variance`:** the decision-relevant co-primary for H1, defined even when the target is singular.
9. **`baseline_tuning_parity`:** strong baselines (shrinkage, DCC-NL, factor models, EWMA) get the same tuning budget and post-processing as our model.
10. **`pit_universe_survivorship`:** a point-in-time universe that keeps delisted names and their delisting returns.

Runners-up: `untrained_encoder_floor`, `h1_noninferiority_test`, `pretraining_overlap_audit`, `event_input_availability`, `risk_calibration_ratio`.

## Open questions

The catalogue uses the defaults in [README section 1](README.md#recommended-defaults-pending-your-decision). Each needs your decision:

1. **H2's contrast and estimand.** Default: a 2×2 design, with the pretrained model's event-input gain as primary (nested; GW on rolling refits) and pretrained+events vs supervised+events as the key secondary. Is the endpoint the raw post-event difference or the difference from matched non-event days?
2. **Forecast origin.** Default: close of announcement day 0, target days 1–5, surprises allowed as inputs. Alternative: close of day −1, target days 0–5.
3. **PD repair.** Default: an eigenvalue floor at ε·mean eigenvalue, with ε frozen on pre-2022 data. Approve, or prefer shrinkage toward a diagonal target?
4. **The deciding test.** Default: a one-sided paired month-cluster bootstrap at 5%. Is "better than strong baselines" decided by all pairwise tests, by SPA, or by MCS?
5. **H1.**
   - Default: both co-primaries must be non-inferior to every strong baseline (intersection–union).
   - The margins are half the EWMA-to-best NLL gap on validation and a 5% GMV-variance tolerance.
   - Ordinary days exclude FOMC/CPI days −1 to +5 and own-earnings stocks.
   - Approve, or count success on either co-primary (with Holm)?
6. **H3.** Crypto universe (point-in-time top-N Binance pairs including delisted ones), target and period (DVOL only from 2021). Is crypto excluded from all pretraining?
7. **H4.** Outcome (announcement-time jumps or daily RV above the training 90th percentile) and test.
8. **Earnings data.** Which source gives before-open and after-close timestamps?
9. **Test window and refits.**
   - Keep 2022 to mid-2026 only, or add pre-2022 events for power?
   - Is re-running encoder pretraining every six months (10-year rolling windows) affordable? If not, the fallback freezes all encoders and narrows the H2 claim to fitted forecasters.
10. **LLMs.** Will any event input pass through an LLM or text encoder?
11. **Foundation-model baselines.** Which are in scope, and may they be scored only on events after their pretraining cutoffs?
12. **Data.**
    - CRSP (CIZ) or Massive files?
    - Accept the 1,260-day history requirement, which excludes recent listings?
    - Is intraday data available?
    - Should we license CPI consensus data?
13. **Public release.** Make an event-window covariance benchmark an explicit contribution, given the redistribution limits?
14. **Schema extensions.** Approve them ([README section 6](README.md#6-schema-extensions)).

## Next, after your review

- Apply your decisions to the affected entries.
- Hand `catalogue.yaml` to the harness branch.
- Optionally run a full-text pass on sources still read at abstract level that back must-haves, such as Engle & Colacito 2006 and Kupiec 1995.
