# Public benchmarks and datasets

We checked 29 public benchmarks and datasets for this paper; every one was opened on 2026-11-12. The full entries, with sources, are in [`catalogue.yaml`](catalogue.yaml) under category `benchmark` or `dataset`, and the sources are listed in [`references.md`](references.md).

## Bottom line

- **No public benchmark for multivariate covariance forecasting exists.** 18 searches found none ([`public_risk_benchmark_gap`](catalogue.yaml)). The nearest items are:
  - VOLARE, an archive with no protocol;
  - M6, which ranks returns;
  - Kaggle Optiver, univariate 10-minute volatility with competition-only data.

  Releasing our event-window protocol (dates, identifiers, target construction, code) would fill the gap. Raw CRSP and VIX data cannot be redistributed.
- **US equities.** We have to build the panel ourselves.
  - CRSP is survivorship-free with delisting returns, but licensed to institutions; its new CIZ format changes returns, so freeze the snapshot. Massive (Polygon) files are the alternative.
  - Market-1T is the closest public protocol for JEPA-style market models. Its public sample covers only Jul 2019–Dec 2020, with no licence text, and it has no covariance task.
- **Events.**
  - Use the official FOMC and BLS calendars.
  - The SF Fed USMPD and the Jarociński–Karadi series give FOMC surprises through Oct and Sep 2026.
  - There is no free CPI consensus series.
- **Crypto (H3).** Use Binance Vision for data (academic use under CC BY-NC-SA 4.0, which also binds derived data). Kaggle G-Research is a design template only. Deribit DVOL history starts in 2021.
- **Return ranking.** Qlib, FinTSB and M6 are China A-share or small-universe precedents, useful for metric definitions only.
- **Poor fit.** Order-book data and anonymized competitions (LOB-Bench, LOBCAST, FI-2010, Jane Street, Optiver) do not fit a daily cross-sectional risk paper. They are kept as related work.

## Overview

| Benchmark or dataset | Priority / status | Asset class and coverage | Frequency | Years | Fit for us |
|---|---|---|---|---|---|
| `pit_event_calendar`: Point-in-time event calendar: actual FOMC and CPI release dates and t… | must / reference | No asset prices: dates and ET release times of US macro announcements (FOMC decisions and CPI releases). | FOMC: eight regularly scheduled meetings a year plus others as needed; CPI: monthly (11 r… | Extract: CPI 2022-01-12 to 2026-11-10, FOMC 2022-01-26 to 2026-10-28; BLS archives back t… | Required for the primary endpoint and H2 (event days, origins, overlap flags) and for H1, whose ordinary-day origins are the trading days with no FOMC/CPI day 0 in t-1..t+5 (G4). |
| `binance_vision`: Binance Vision public market data (crypto) | should / reference | All Binance spot, USD-M and COIN-M symbols; options directory. | Trades, aggTrades; klines from 1s to 1mo. | Spot BTCUSDT 1d 2017-08 to 2026-10; USD-M BTCUSDT 1d 2020-01 to 2026-10. | Good for H3: covers the 2022-mid-2026 test window. |
| `crsp_us_stock`: CRSP US Stock Databases (CIZ format) | should / reference | US-listed stocks, active and inactive. | Daily and monthly. | Over 100 years to the latest release; CIZ only after the Dec-2024 data; 2026 lag unverifi… | High: standard survivorship-free source for the 2022-2026 panel. |
| `market_1t`: Market-1T dataset and evaluation protocol | should / emerging | All US-traded equities; about 700-stock benchmark universe. | 1 Hz. | 2008-2025 per the paper (code evaluates 2008-2023); sample 2019-07-01 to 2020-12-31. | Protocol precedent for H1 only; no public data in our test window. |
| `public_risk_benchmark_gap`: Public multivariate covariance-forecasting benchmark (none found) | should / gap | Not applicable. | Not applicable. | Not applicable. | The gap is the finding: we must define, and could release, our own event-window covariance protocol. |
| `fev_bench`: fev-bench (skill score, win rate and paired bootstrap aggregation) | nice / reference | No equities or crypto. | Heterogeneous. | Not stated. | Reporting template only. |
| `fintsb`: FinTSB financial time-series forecasting benchmark | nice / reference | China A-shares (anonymised). | Daily OHLCV. | 15-year span; 2024 transfer test. | Low: metric and leakage-rule template. |
| `gift_eval`: GIFT-Eval general time-series forecasting benchmark | nice / reference | General time series; Econ/Fin = M4 only. | 10-second to annual. | Heterogeneous by dataset. | Leakage-disclosure template only. |
| `kaggle_gresearch_crypto`: Kaggle G-Research Crypto Forecasting (2021-22) | nice / reference | 14 cryptocurrencies. | 1-minute bars; 15-minute target. | Data from 2018; competition Nov 2021 to May 2022. | Partial for H3 as a design template only. |
| `look_ahead_bench`: Look-Ahead-Bench (LLM look-ahead bias as trading-performance decay) | nice / emerging | AAPL, MSFT, GOOGL, NVDA, TSLA. | Monthly rebalancing. | 2021-04 to 2021-09 and 2024-07 to 2024-12. | Only the pre/post-cutoff design, with paired inference on our losses. |
| `m6_competition`: M6 forecasting competition | nice / reference | 50 S&P 500 stocks and 50 international ETFs. | Daily adjusted closes; four-week rounds. | 2022-2023. | Low: RPS template for the secondary return task. |
| `qlib_alpha158_alpha360`: Qlib benchmarks (Alpha158 and Alpha360 handlers, model zoo) | nice / reference | China A-shares (CSI300 tables); US listed as available. | Daily. | 2008-01-01 to 2020-08-01 (test from 2017). | Low; code-level metric reference. |
| `volare`: VOLARE realized-measure archive | nice / reference | Selected US stocks, FX, futures. | Daily measures from 1-minute, 5-minute or 1-second intraday returns. | Stocks from 2015-01-02; FX from 2009-09-25; futures from 2009-09-28; end not stated. | Low: cross-check for the intraday sensitivity target only. |
| `fi_2010`: FI-2010 limit-order-book dataset | drop / reference | 5 Helsinki-listed stocks. | Event-based, 10 levels. | 1-14 June 2010. | None. |
| `finstressts`: FinStressTS (synthetic financial stress-test benchmark) | drop / reference | Synthetic. | Not stated. | Not applicable (synthetic). | Low. |
| `fintsbridge`: FinTSBridge (financial time-series evaluation suite) | drop / reference | Financial time series (not detailed). | Not stated. | Not stated. | None. |
| `fnspid`: FNSPID (financial news and stock price dataset) | drop / reference | S&P 500 companies. | Daily prices; time-stamped news. | 1999-2023. | Low. |
| `ieee_ranking_challenge`: IEEE Investment Ranking Challenge 2018 | drop / reference | Anonymised stocks. | Six-month periods. | 1996-2017. | None. |
| `kaggle_jane_street_2020`: Kaggle Jane Street Market Prediction (2020-21) | drop / reference | Anonymised. | Intraday opportunities. | About 2 years, calendar undisclosed; competition 2020-21. | Poor. |
| `kaggle_jane_street_2024`: Kaggle Jane Street Real-Time Market Data Forecasting (2024-25) | drop / reference | Anonymised instruments. | Intraday. | Anonymised; competition 2024-25. | Poor. |
| `kaggle_jpx`: Kaggle JPX Tokyo Stock Exchange Prediction | drop / reference | Japanese equities. | Not stated. | Not stated. | None. |
| `kaggle_optiver_close`: Kaggle Optiver Trading at the Close (2023) | drop / reference | NASDAQ-listed stocks. | 10-second snapshots in the closing window. | Anonymised; competition 2023. | None. |
| `kaggle_optiver_rv`: Kaggle Optiver Realized Volatility Prediction (2021) | drop / reference | 112 anonymised stocks. | Snapshots within 10-minute windows. | About 3 years of data (secondary); competition 2021. | Related work only. |
| `lob_bench`: LOB-Bench (generative limit-order-book benchmark) | drop / reference | NASDAQ stocks (GOOG, INTC on the leaderboard). | Message level (nanosecond timestamps). | Leaderboard on January 2023 data. | None. |
| `lobcast`: LOBCAST (benchmark study of LOB-based price-trend models) | drop / reference | 5 Finnish stocks; 6 NASDAQ stocks. | Event-level, 10 levels. | June 2010; July 2021; February 2022. | None; cautionary citation. |
| `monash_archive`: Monash Time Series Forecasting Archive | drop / reference | General; finance-related only Bitcoin, FRED-MD, CIF 2016, NN5. | Mixed. | Not stated. | None. |
| `portbench`: PortBench (LLM portfolio-management benchmark) | drop / reference | Six asset classes. | Not stated. | 2015-2025. | None. |
| `stocknet_acl18`: StockNet / ACL18 tweet-and-price dataset | drop / reference | US stocks. | Daily prices; tweets. | 2014-2015. | None. |
| `tfb`: TFB (Towards Comprehensive and Fair Benchmarking of Time Series Forec… | drop / reference | 10 domains, including stock markets. | Not stated. | Not stated. | None. |

## Access, licence and use

| Benchmark or dataset | Licence | Cost | Size | Access | Used by |
|---|---|---|---|---|---|
| `pit_event_calendar` | BLS material is public domain (cite BLS); Board website content is public domain unless otherwise indicated (cite the Board); USMPD states no dataset… | Free. | Test window: 36 FOMC and 53 CPI events. Extract through 2026-11-12: 40 FOMC rows (including the notation vote) and 58 C… | Free official web pages: federalreserve.gov (FOMC calendars 2021-2027 and statement press releases), bls.gov (per-year release schedules, lapse notices, CPI news-release… | Acosta+ 2025 (USMPD) is the reference FOMC event-time database. Among the seeds, S15 documents its event-time source (exact announcement times from the Bloombe… |
| `binance_vision` | Code MIT; data CC BY-NC-SA 4.0 (Binance Vision Dataset Terms, 26 Aug 2026); contracting entity NEST EXCHANGE LIMITED (ADGM). | Free. | Not quantified; zipped CSVs. | HTTPS download from data.binance.vision (S3 listing) or scripts in github.com/binance/binance-public-data. | None confirmed for Binance Vision itself (the verification record lists no user). S6 Kronos evaluates on Binance spot pairs and pretrains on Binance crypto dat… |
| `crsp_us_stock` | Licensed to institutions; no public terms shown; not redistributable. | Subscription (price not shown). | More than 36,000 active and inactive securities. | Licensed delivery via WRDS, Snowflake, MOVEit or CHASS; subscription request needed. | S5; Ledoit & Wolf 2017; Engle+ 2019; Schwarz+ 2026. |
| `market_1t` | Code MIT; datasets tagged 'derived-market-data' with no licence text. | Sample free; full rebuild needs a paid Massive flat-file plan. | 'Nearly one trillion' 1-second aggregates; sample 376 days, 230,025 ticker-days (28.8 GB sparse, 23.5 GB dense, 27.1 GB… | Hugging Face sample (fin-ai-lab/Market-1T-1Hz-2019H2-2020-sparse, -dense, -daystore; login, no gating stated); full data rebuilt with MIT code (github.com/fin-ai-lab/mar… | S1 (introduces); cited by S17. |
| `public_risk_benchmark_gap` | Not applicable; a release must respect CRSP, Cboe and Binance Vision terms. | Not applicable. | Not applicable. | Not applicable: no qualifying benchmark found. | None found; covariance papers use bespoke panels (S4, S11, S12, S13, Johansson+ 2023). |
| `fev_bench` | fev library Apache-2.0; paper CC BY 4.0; source-dataset licences not stated. | Free. | 100 tasks from 96 datasets in 7 domains; 46 with covariates; 35 multivariate. | github.com/autogluon/fev; HF autogluon/fev_datasets; leaderboard HF space autogluon/fev-bench. | No seed; rules adopted in relative_skill_reporting. |
| `fintsb` | Code GPL-3.0; data licence not stated. | Code free; Eastmoney terms unverified. | 20 datasets of 300 stocks × 250 days. | github.com/TongjiFinLab/FinTSB; raw data from the Eastmoney quant API. | None besides the FinTSB paper in our sources. |
| `gift_eval` | Apache-2.0 (code and data); README says research use only; paper CC BY 4.0. | Free. | 23 datasets, about 144k series, 177M points; test data 1.59 GB. | Hugging Face Salesforce/GiftEval (and GiftEvalPretrain); code github.com/SalesforceAIResearch/gift-eval; leaderboard HF space Salesforce/GIFT-Eval. | fev-bench (datasets); Meyer+ 2025 (leakage audit); no seed. |
| `kaggle_gresearch_crypto` | Kaggle rules (not read). | Free with a Kaggle account (prize pool USD 125,000). | Millions of rows. | Kaggle code competition (time-series API) after accepting the rules. | None in our sources (one course project). |
| `look_ahead_bench` | None shown for lookaheadbench; fork README states MIT without a LICENSE file. | Code free; data via a Financial Datasets API key (these five tickers free without one); P… | 5 tickers, two 6-month windows, single runs. | github.com/benstaf/lookaheadbench (front-end-like) and github.com/benstaf/aihedgefund_lookaheadbench (backtest); no dataset or leaderboard released. | S9 only, in our sources. |
| `m6_competition` | Not stated. | Not stated (prices from free sources such as Yahoo Finance). | 100 assets; 12 rounds. | Papers only (IJF 41(4):1315-1354, 2025; arXiv:2310.13357); no fixed public dataset. | The organisers' paper only, in our sources. |
| `qlib_alpha158_alpha360` | Code MIT; Yahoo-crawled data with no licence stated. | Free. | 20 seeds per model; feature counts not verified. | pip or github.com/microsoft/qlib; get_data.py download currently disabled; Yahoo collector; community A-share data (chenditc/investment_data). | S6 Kronos (data and backtest). |
| `volare` | Not stated for the data; paper CC BY 4.0; Kibot terms not described. | Not stated. | Not stated; US stock count unconfirmed. | volare.unime.it Download section (pre-packaged datasets with READMEs); the site rendered only its title for the verification agent. | No user besides the VOLARE paper in our sources. |
| `fi_2010` | CC BY 4.0. | Free. | 394,337 event samples; 144 features. | Etsin/Fairdata download (urn:nbn:fi:csc-kata20170601153214969115). | LOBCAST; listed by S1. |
| `finstressts` | Not stated. | Not stated. | 30 synthetic environments. | Paper arXiv:2606.03184; code access not recorded. | None in our sources. |
| `fintsbridge` | Not stated. | Not stated. | Three financial datasets. | Not confirmed. | None in our sources. |
| `fnspid` | Conflicting (CC BY 4.0 vs repository statements). | Free. | 29.7M price and 15.7M news records. | Hugging Face Zihan1004/FNSPID. | S8; S16. |
| `ieee_ranking_challenge` | Not stated. | Not stated. | 42 six-month periods. | Not stated. | None in our sources. |
| `kaggle_jane_street_2020` | Kaggle rules (not read). | Free with a Kaggle account. | 2,390,491 rows × 138 columns; 500 days. | Kaggle after accepting the rules. | None in our sources. |
| `kaggle_jane_street_2024` | Kaggle rules (not read). | Free with a Kaggle account. | Not verified (79 features, 9 responders). | Kaggle code competition with an evaluation API. | None (course project and tutorial only). |
| `kaggle_jpx` | Kaggle rules (not read). | Not stated. | Not stated. | Kaggle (title confirmed only). | arXiv:2512.06630 uses its dataset and judges performance by the out-of-sample Sharpe ratio of a long-short portfolio (per the verification record; that paper w… |
| `kaggle_optiver_close` | Kaggle rules (not read). | Free with a Kaggle account. | Not verified. | Kaggle code competition API. | Hettich et al. (ESANN 2024), recorded with the registry entry. |
| `kaggle_optiver_rv` | Competition use only (rules Section 7.A, HeroX mirror). | Free with a Kaggle account. | 3,830 ten-minute time_ids in training (secondary source). | Kaggle code competition after accepting the rules. | Unconfirmed: ARTEMIS (Ray, arXiv:2603.18107; abstract only, per the verification record) reports weaker results on an 'Optiver' dataset with a volatility-focus… |
| `lob_bench` | Code MIT; HF dataset CC BY 4.0 (empty card); LOBSTER data proprietary. | Code free; LOBSTER account needed for real data. | HF dataset about 3.67 GB. | pip install lob_bench; github.com/peernagy/lob_bench; samples on Hugging Face (peernagy/lob_bench). | Leaderboard entries only. |
| `lobcast` | Article CC BY 4.0; repository licence not shown. | Code and FI-2010 free; LOBSTER access for LOB-2021/2022. | 15 models; FI-2010 394,337 events; 6 NASDAQ stocks in LOB-2021/2022. | github.com/matteoprata/LOBCAST; FI-2010 from Fairdata. | Not stated in our sources. |
| `monash_archive` | Research use; per-dataset licences not recorded. | Free. | 30 datasets, 58 variants. | Zenodo via forecastingdata.org. | Meyer+ 2025 (leakage audit). |
| `portbench` | Not stated. | Not stated. | 6,269 QA items plus allocation tasks. | github.com/AgenticFinLab/portbench. | None in our sources. |
| `stocknet_acl18` | MIT. | Free. | 88 stocks. | github.com/yumoxu/stocknet-dataset. | None in our sources. |
| `tfb` | Code MIT; data licences not recorded. | Free. | 8,068 univariate series; 27 multivariate datasets. | github.com/decisionintelligence/TFB; OpenTS-Bench leaderboard. | None in our sources. |

"Not stated" means the field was not on the pages the agents opened. Kaggle details come from secondary write-ups because Kaggle pages render client-side. Licence terms change, so re-check them at submission time.
