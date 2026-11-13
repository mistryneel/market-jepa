# Data sources

Status (2026-11-12): eight research agents surveyed these sources from documentation and metadata only, and eight independent fact-checkers then tried to refute each topic. Corrected claims are used here; claims a fact-checker could not verify are marked (unverified). Nothing has been downloaded, and the adapters arrive in milestone M1. Terms, prices and layouts change often: verify on implementation.

Conventions: GB = 10^9 bytes, GiB = 2^30 bytes. ET = America/New_York via `zoneinfo`, never a fixed offset. "The guard" means every download prints an estimate and refuses more than 2 GB without `--yes`. The repository is public: no data, vendor files or credentials go into git, and credentials come only from `MASSIVE_API_KEY`, `MASSIVE_S3_ACCESS_KEY_ID`, `MASSIVE_S3_SECRET_ACCESS_KEY`, `FRED_API_KEY`, `SEC_USER_AGENT` and `HF_TOKEN`. Periods: train to 2018-12-31, tune 2019-2021, locked test 2022-01-01 to 2026-06-30. Nothing here is legal advice.

## Summary

| Source | Role | Coverage | Cost | Access | Licence / terms headline | M1 status |
|---|---|---|---|---|---|---|
| Market-1T public subset (Hugging Face) | Adapter validation; optional tune-period 1 Hz bars | 2019-07-01 to 2020-12-31; 376 sessions; 190-916 names a day ([index][hf-daystore-202001]) | $0 | None; `HF_TOKEN` optional ([API][hf-sparse-api]) | `other` / `derived-market-data` with no licence text; derived from Massive ([card][hf-sparse-card]) | Ready to build, validation only; the 2.50 GB slice needs `--yes` |
| Market-1T full rebuild (`market-1t`) | Optional 1 Hz data for train and test | Massive quotes and trades from 2003-09-10 ([quotes][m-quotes]); paper scope 2008-2025 | $199 or $2,499 a month for a plan with quote files ([pricing][m-pricing], [business][m-business]); 16.23 TB of flat files for 2008-2025 ([listing][m-quotes-root]) | Paid plan, S3 keys | Code MIT; data under Massive terms, which ban ML training without permission ([MDT][m-mdt]) | Blocked: plan + written ML-training permission. The offline `plan` estimator can be built |
| Massive | Daily bars, point-in-time security master, corporate actions | Bars from 2003-09-10 ([day aggs][m-dayaggs]); splits from 1978-10-25 ([splits][m-splits]); dividends from 2000-01-15 ([dividends][m-dividends]) | Advanced $199/mo; Business $2,499/mo, $1,999 committed, $19,188/yr; reference data from Starter $29/mo | Account, plan, REST key, separate S3 key pair ([S3 KB][m-s3kb]) | ML training needs express permission (MDT §5(g), Business ToS §6.1(j)); individual plans are personal use only ([Individuals ToS][m-indiv]) | Blocked: written permission (Order Form). Build against synthetic fixtures |
| FRED / ALFRED | Vintage-aware DGS2, DGS10, DFF, VIXCLS | Vintages from 2005-06-28 (H.15 series) and 2010-11-22 (VIX) ([ALFRED][alfred-dgs10]) | $0 | Free key, `FRED_API_KEY` ([keys][fred-key]) | ML use and local database caching prohibited ([FRED legal][fred-legal]) | Blocked: written permission from the St. Louis Fed; adapter off by default |
| Treasury, NY Fed, Board H.15 | Primary-source 2y/10y yields and EFFR | Current values, no vintages | $0 | None ([NY Fed API][nyfed-api]) | CC0 ([data.gov][ust-datagov]); NY Fed licence with notice ([terms][nyfed-terms]); Board public domain ([disclaimer][frb-disclaimer]) | Ready to build; Treasury endpoint still to identify |
| VIX (Cboe, via FRED VIXCLS) | Volatility feature | From 1990-01-02, back-tested before 2003-09-22 ([methodology][cboe-method]) | Unknown | Cboe permission or licence | Cboe copyright; storage and derived works need consent ([Cboe terms][cboe-terms]) | Blocked: Cboe permission, or drop or replace |
| Event calendars (Fed Board, BLS) | FOMC, CPI and jobs-report release times | 174 FOMC decisions and 262 + 262 BLS releases, 2005 to 2026-11-12 | $0 | None; contact User-Agent ([BLS policy][bls-pss]) | Public domain, cite the source ([Board][frb-disclaimer], [BLS][bls-link]) | Ready to build |
| SEC EDGAR | Earnings 8-K (Item 2.02) and 10-Q/10-K filing times | From 1994; real acceptance times from about May 2002 | $0 | `SEC_USER_AGENT`; ≤10 requests/s ([policy][sec-privacy]) | Public information, free to reuse; trademarks restricted ([policy][sec-privacy]) | Ready to build |
| Kraken | Primary crypto bars for H3 | 2013-09-11 to 2026-09-30; 1,758 complete pairs ([archive][kr-part04]) | $0 | None ([support][kr-ohlcvt]) | Own benefit only; no redistribution; no automation without consent ([ToS][kr-terms]) | Ready to build; the human downloads the 9.55 GB archive |
| Coinbase Exchange | Crypto cross-check and fallback | 847 products, 331 delisted ([products][cb-products]) | $0 | None ([candles][cb-candles]) | No derived research outside the organisation without written consent ([terms][cb-terms]) | Probes only; publication needs consent |
| Binance Vision | Broadest crypto archive (conditional) | From 2017-08 ([listing][bn-s3-btc1h]) | $0 | None | CC BY-NC-SA 4.0, subject to Binance Terms of Use, which exclude US persons ([terms][bn-terms]) | Blocked: counsel sign-off |

## Licence and terms blockers

Clause numbers refer to the versions current on 2026-11-12.

### Massive (also governs Market-1T and the market-1t rebuild)

- **ML training is banned on both licence tracks.** Market Data Terms (MDT, updated 2026-11-03) §5(g): you may not "Use Information to train, fine-tune or distill an artificial-intelligence or machine-learning model" unless it is expressly permitted and all third-party provider requirements are met ([MDT][m-mdt]). Businesses ToS (updated 2026-10-06) §6.1(j) bars it unless an Order Form expressly permits it, and §6.1 is subject to every third-party agreement ([Business ToS][m-biz]). Both bar letting AI tools use the data for their own purposes. Buying Stocks Business does not by itself allow training.
- **Individual plans are personal only.** Individuals ToS (updated 2026-11-03) §2 grants access only for personal, non-commercial, non-business purposes, and its preamble sends use on behalf of an organisation to the Businesses Terms ([Individuals ToS][m-indiv]). Stocks Advanced requires non-professional status ([pricing][m-pricing]), and MDT §3 lets Massive back-bill the professional-rate difference from the start of the subscription ([MDT][m-mdt]). Work for an employer, university or lab points to Business or a negotiated licence.
- **No publishing.** MDT §5(c) bars sharing, publishing or redistributing Information; your own analyses may be kept only if they contain no Information and cannot recreate it. Individuals ToS §1 counts derived data that can substitute for the source as Information, and MDT §5(d) requires a separate licence for indexes and benchmarks. Massive's knowledge base (guidance, not contract) treats published charts or tables as very likely redistribution and a private model whose outputs you keep as usually not ([KB][m-redistrib]). Whether model weights count as Information is unresolved.
- **Business licence.** Internal use (§2.1); derivative models and analyses may be built and their outputs distributed if they contain no Information (§2.2(c)); no indexes, benchmarks or investment strategies without a licence (§6.1(f)); all Information deleted at termination, §2.2(c) works kept (§11.3); fees non-cancellable ([Business ToS][m-biz]).
- **Deletion and change.** MDT §8: delete downloaded Information within 30 days after the licence ends (unused backups within 90 days); a lapsed paid period counts as a move to the free plan. MDT §7: Massive may change or withdraw data without notice ([MDT][m-mdt]). The 2025-08-28 terms had no ML clause but banned publishing Derived Works ([Wayback][m-mdt-2025]).
- **Needed before Massive data enters training or evaluation:** a written Order Form or research licence that expressly permits training, fine-tuning and evaluation, publication of aggregate results without raw prices, keeping weights and derived artefacts after the subscription, and use by every team member, with confirmation that the SIP and exchange pass-through terms allow it.

### Market-1T on Hugging Face

- The three repos declare only `license: other` and `license_name: derived-market-data`: no licence text, link, LICENSE file or gating ([card][hf-sparse-card]). tfwm's README defers to the cards ([README][tfwm-readme]), and the paper calls the data licensed for release without naming a licence ([paper][arxiv-v2]). The data derive from Massive flat files; whether Massive's §5(g) carries over is open.
- Allowed now: download and internal adapter validation (internal research use looks intended, unconfirmed). Needs written clarification from fin-ai-lab and/or Massive: publishing dependent results, redistributing any derived artefact, and training.
- Code: tfwm and market-1t are MIT and mosaicml/streaming is Apache-2.0. galilai-group/stable-finance, which built the HF layouts, has no licence: read it, do not copy it ([repo][sf-repo]). tfwm's `industry_map.parquet` derives from Compustat SIC codes, so Compustat/WRDS terms may apply ([README][tfwm-readme]).

### FRED and ALFRED

- **No ML use, by anyone.** Section II (Prohibited Use) of the FRED Services Terms covers all use, including non-commercial, educational and personal, and forbids using FRED Services or Content in connection with developing or training software or machine-learning systems, naming LLMs, deep learning and generative AI ([FRED legal][fred-legal]).
- **API prohibitions with no consent carve-out:** (k) ML development or training; (l) storing, caching or archiving FRED content, or loading it into any database, archive or cache; (m) wholesale downloading. The general list, which does allow prior written consent, adds (g) excessive automated collection, (j) commercial use and (p) storing content in any database ([FRED legal][fred-legal]). The ML and caching clauses appeared between the Wayback captures of 2024-05-03 and 2024-05-07 ([Wayback][fred-legal-2024]).
- **Discrepancy:** the standalone API terms page has neither clause, but it incorporates the St. Louis Fed legal terms and links to the API section of the full terms, which state they cover the API ([API terms][fred-apiterms]). Treat the full terms as binding. Amendments must be a written statement executed by the Bank, so any permission should take that form; the summary's listing of research as a personal use is an ambiguity for counsel.
- Third-party series such as VIXCLS need the owner's permission beyond personal use, which the Bank cannot grant ([API terms][fred-apiterms]). A calendar derived from ALFRED vintage dates is itself FRED Content. If FRED is used, outputs must carry the API terms' non-endorsement notice.

### VIX (Cboe)

- FRED marks VIXCLS as copyrighted, citation required, with a Cboe copyright line ([VIXCLS][fred-vix]). Cboe's site terms (updated 2022-11-16) allow one personal, non-commercial copy; storage in a retrieval system, redistribution, derivative works and use to verify other data need written consent, fair use aside ([Cboe terms][cboe-terms]). Routes: a Request to Use Cboe Content ([form][cboe-use]) or a DataShop or Global Indices licence, cost unknown; otherwise drop or replace VIX.

### Coinbase

- Using the Exchange Market Data API binds you to the Market Data Terms ([docs][cb-welcome]), last updated 2023-02-06 (latest capture checked 2026-07-10; the live page blocks automated fetches). The licence covers personal or research use within your entity; without prior written consent you may not disseminate the data or Derived Works, which expressly include charts, analytics and research, outside your organisation, nor build indexes or benchmarks ([terms][cb-terms]). Publishing paper results needs consent from marketdata@coinbase.com.

### Kraken

- ToS updated 2026-11-06 (US residents contract with Payward Interactive, Inc.). Section 8 allows Kraken's content only for your own benefit, other uses via marketdata@kraken.com; Section 9 bars giving it to third parties and bars scraping, bots, scripts and other automation without written consent, with no carve-out for the public API ([ToS][kr-terms]). Derived research is not expressly restricted, and the OHLCVT page has no data licence. Kraken does not serve residents of Maine or New York ([restrictions][kr-geo]).
- Allowed now: a manual download by the human for our own research. Confirmation advised: scripted downloads and published aggregates. Never redistribute raw bars.

### Binance Vision

- Vision Dataset Terms v1.0 (updated 2026-08-26, on GitHub from 2026-09-30) ([terms][bn-terms]): 1.2 subject to the Binance Terms of Use; 1.3 provider NEST EXCHANGE LIMITED (ADGM); 1.4 any access or attempted access accepts both; 1.5 the Vision terms prevail in a conflict; 2.3 open to any individual or legal entity; 2.4 covers derived charts, models and indicators; 3.1 CC BY-NC-SA 4.0; 3.4 commercial use needs an enterprise licence; 4.1 academic research, open education, personal backtesting and open-source evaluation only; 4.3 no hosting or selling; 4.5 credit Binance Vision and keep redistributed derivatives under CC BY-NC-SA 4.0; 7.1-7.3 rate limits and IP bans; 8.2 no implied endorsement of papers.
- Binance's prohibited-countries list (updated 2024-02-27) includes the United States, Canada and the Netherlands and treats US-connected entities as US users ([list][bn-prohibited]); `api.binance.com` returns HTTP 451 from the US, citing eligibility ([ping][bn-ping]). Counsel must clear US-person use and the ShareAlike duties first, and should know that research agents sent listing requests that clause 1.4 may count as access.

### Public-domain and permissive sources

- Federal Reserve Board and BLS: public domain (BLS excepts previously copyrighted images); cite the source ([Board][frb-disclaimer], [BLS][bls-link]). SEC: public information that may be copied with citation; no seal or logos; SEC and EDGAR marks are registered trademarks ([policy][sec-privacy]); EDGAR filing content is free to reuse ([FAQ][sec-faq]). Treasury yield curve rates: CC0 1.0 ([data.gov][ust-datagov]). NY Fed (terms of 2023-06-09): personal or business use including automated access, storage and derivative works, with its prescribed notice and disclaimer on EFFR outputs ([terms][nyfed-terms]). SF Fed USMPD: credit required, not for private gain, contains LSEG data, so a private cross-check only ([USMPD][usmpd], [policies][frbsf-policies]).
- Attribution line for committed calendar CSVs: "Event calendars derived from public-domain pages of the Board of Governors of the Federal Reserve System and the U.S. Bureau of Labor Statistics."

### What is allowed now and what needs a human

| Source | Allowed now | Needs written permission or counsel |
|---|---|---|
| Massive, incl. the market-1t rebuild | Nothing until the human buys a plan and accepts the terms | Training, fine-tuning, evaluation; publishing derived results; organisational use of an individual plan; keeping artefacts after the licence ends |
| Market-1T (HF) | Download; internal adapter validation | Publication; redistribution of derived data; training |
| FRED / ALFRED | Personal, non-commercial viewing and downloading | Any ML use; any storage in the harness |
| VIX (Cboe) | One personal, non-commercial copy | Storage, derived features, verification of other data, publication |
| Kraken | Manual download; own research | Scripted download and published aggregates (confirmation advised) |
| Coinbase | Research within the organisation | Any derived number, chart or table in the paper |
| Binance | Nothing | Everything: US eligibility and CC BY-NC-SA duties |
| Board, BLS, SEC, Treasury, NY Fed | Copy, store and redistribute with citation or the required notice | Nothing |

## Market-1T public subset (Hugging Face)

**Coverage**
- `fin-ai-lab/Market-1T-1Hz-2019H2-2020-{sparse,dense,daystore}`, 2019-07-01 to 2020-12-31, all in the tune period ([tree][hf-daystore-tree]). 376 of 381 NYSE sessions: the five early-close days (2019-07-03, 2019-11-29, 2019-12-24, 2020-11-27, 2020-12-24) are missing from every layout.
- Universe: 190 (2020-01) to 916 (2020-04) names a day, four months below 500 ([index][hf-daystore-202001]). REITs and foreign listings are in, ETFs out, symbols as traded (FB, CTL, UTX, BRK.B) ([meta.json][hf-meta-20201231]). The paper's rule (no ETFs or REITs, prior-month VWAP above $5, ADV of at least $20M, about 700 names) cannot be reproduced: `metadata.parquet` is unpublished ([paper][arxiv-v2], [ingest.py][sf-ingest]).
- A sparse record is one ticker-day: `date`, `ticker`, `ts_interval` (int32 Unix seconds, interval end) and float32 `features` (n×9: `bid_price, vwap_all, high, low, ask_price, bid_size, ask_size, volume, n`). There is no open, close or last trade, though the paper lists 11 features. Sparse keeps only seconds with a quote or trade (07:00-20:00 ET per the card); dense is a 23,400-row grid stamped 09:30:01-16:00:00 ET; the day store adds forward-looking targets ([card][hf-sparse-card], [spec.py][sf-spec]). Sparse has 230,025 ticker-days.

**Access and cost**: $0; public, ungated, no account ([API][hf-sparse-api]); `HF_TOKEN` optional. Pinned sizes: sparse 1,670 files / 28,838,752,778 B, dense 2,941 / 23,532,307,967 B, day store 3,028 / 27,124,643,291 B ([tree][hf-sparse-tree]).

**Terms**: see [Licence and terms blockers](#licence-and-terms-blockers).

**Rate limits**: per 5-minute window, anonymous 500 API and 3,000 resolver requests per IP, free account 1,000 / 5,000, PRO 2,500 / 12,000, then 429 ([HF docs][hf-rate]). huggingface_hub 2.4.0 needs about 3 API calls for a month with a SHA revision ([source][hf-snapshot]); 0.36.0, which tfwm pins, about one per file ([source][hf-036-xet]). The Xet hosts (`us.aws.cdn.hf.co`, `cas-server.xethub.hf.co`) have undocumented limits and must be reachable through any firewall ([Xet][hf-xet]).

**Point-in-time semantics**
- A row stamped `t` covers (t−1, t] of SIP time in UTC: `event_time` = (t−1, t], `knowledge_time` = t. A 1-minute bar over (m−60, m] gets m; a dense-grid daily bar gets 16:00:00 ET. The float64 interval calculation can shift events within about 128 ns of a boundary, which is negligible ([methodology][m1t-methodology]).
- `date` is the ET session date; never derive it from UTC, because the window crosses UTC midnight. 2020-03-08 is a DST switch: the session moves from 14:30-21:00 to 13:30-20:00 UTC ([IANA][iana]).
- Quotes hold the NBBO at the interval end. `high`, `low` and `vwap_all` are forward-filled into rows without trades, so aggregate over `n > 0` only; odd-lot-only seconds still carry stale highs and lows ([conditions][m1t-conditions]). Corrections are not applied and prints are bucketed by SIP receipt, so `event_time` is dissemination time ([trades doc][m-trades-md]).
- The dense and day-store grids end at 16:00:00 ([spec.py][sf-spec]). Whether closing-auction prints fall after that, into sparse rows only, is (unverified), so any daily close is a proxy to check against official closes. Day-store targets are labels, never features.

**Implementation notes for M1**
- Pin revisions: sparse `5797a9f890e133c491265bb8889cd64f27ceb50e`, dense `e20121edadb80fd05bf11dda0f00b394c5eb7210`, day store `b8f7520b1d89bdd1e971ec87f64e687f26e0d813`; data last changed on 2026-09-27 ([commits][hf-sparse-commits]).
- Call `snapshot_download(repo_id, repo_type="dataset", revision=<sha>, allow_patterns=["1Hz_mosaic_mnth_sparse/2020/03/*"], local_dir=..., max_workers=8)` with huggingface_hub ≥2.4 and hf-xet; `HF_HUB_ENABLE_HF_TRANSFER` is deprecated ([env vars][hf-env]). Each month folder holds `index.json` and `shard.NNNNN.mds.zstd` files (MDS v2, 64 MiB raw, no hashes) ([index][hf-2003-index]).
- Hash every file yourself: normal downloads skip sha256, interrupted files restart from zero, and the `local_dir` fast path trusts any file whose metadata commit matches ([file_download.py][hf-filedl]). Check LFS files against the tree's `lfs.oid` (2020-03 `shard.00000` is `f08290180f30942e2debd8a22e158a62829579dbe542816c23257531b3091d16`) and non-LFS files (`index.json`, `meta.json`, the git-stored `2019/12/shard.00042.mds.zstd`) against the git blob SHA-1 ([tree][hf-sparse-tree]). A throttled download can return without error while files are missing ([tfwm][tfwm-dl]).
- Records are shuffled within a month, so process whole months with our own MDS reader (see [Tooling notes](#tooling-notes-relevant-to-sources)). float32 counts are exact only up to 16,777,216: cast before summing.
- 2020-03 invariants: 22 sessions, 14,309 records, 650-651 tickers a day, 131 shards of 10-118 samples, the DST shift. The research expects circuit-breaker halts on 03-09, 03-12, 03-16 and 03-18, from general knowledge (unverified).

**Known gaps and risks**: an unclear licence; a universe usable only as an external mask; quote-size units (market-1t multiplies by 100 while Massive's docs describe shares, so check that AAPL NBBO sizes are hundreds to low thousands) ([quotes doc][m-quotes]); a 07:00 start that conflicts with stable-finance's 04:00 extended open; unadjusted prices not yet checked on bytes (check AAPL and TSLA over 2020-08-28 to 08-31) ([snapshot.py][m1t-snapshot]); and a dense card that says sizes are zero-filled while the code forward-fills them ([schema.py][sf-schema]).

**Next-download estimate**: M1 slice `1Hz_mosaic_mnth_sparse/2020/03/*`: 132 files, 2,502,351,803 B (2.33 GiB), about 7.5, 4 or 2 min at 50, 100 or 200 Mbit/s, decompressing to 8,687,607,177 B (about 217 million rows) ([index][hf-2003-index]). Above the guard, so `--yes`. The 2020-02 sparse month (1.487 GB) fits under the guard but loses the DST and circuit-breaker checks. Full: 79.50 GB for three layouts, about 1.8 h at 100 Mbit/s; decompressed, sparse is 109.58 GB and day-store features 193.8 GB.

## Market-1T full rebuild (market-1t pipeline)

**Coverage**
- `fin-ai-lab/market-1t` (MIT; `38da67c065c12e0373a5d56a52a2685d6eccf660`, one commit, 2026-10-08) turns Massive `quotes_v1` and `trades_v1` flat files into Parquet (100 ticker-hash partitions) and sparse 1 Hz snapshots of every ticker over the whole flat-file day, about 12,882 tickers on a 2026 day ([README][m1t-readme]).
- Quote files start on 2003-09-10 ([quotes doc][m-quotes]). The paper says 2008-2025 ([arXiv][arxiv-abs]), but the code shows the lab's archive spans 2008-01 to 2024-12 ([densify.py][sf-densify]). It does not rebuild the HF layouts (unlicensed stable-finance) or the universe (`metadata.parquet` has no public builder) ([write_mds.py][sf-writemds]).

**Access and cost**: quote flat files need Stocks Advanced ($199/month; individual, non-professional) or Business ($2,499/month); Developer ($79) has trades only and Starter ($29) neither ([quotes doc][m-quotes], [pricing][m-pricing], [business][m-business]). It uses the S3 keys, not the REST key, read from `MASSIVE_ACCESS_KEY_ID` and `MASSIVE_SECRET_ACCESS_KEY` ([download.py][m1t-download]); the wrapper should map our `MASSIVE_S3_*` variables onto those in the child environment only. The DGX Spark has at most 4 TB of NVMe ([NVIDIA][dgx]), so stage month by month.

**Terms**: Massive's (see blockers).

**Rate limits**: none published for `files.massive.com`. market-1t runs 4 files with 8 connections each and retries a file 3 times (after 10, 20 and 40 s) on top of botocore's retries; ranged GETs sometimes get 403 ([download.py][m1t-download]). Massive's listing pages returned 503 to the researcher after about 25 quick requests (not to the fact-checker's 21 spaced ones); the root pages give per-year counts and bytes in two reads ([trades listing][m-trades]).

**Point-in-time semantics**
- `ts_interval` is the right-closed interval end in UTC nanoseconds; set `knowledge_time` to at least that plus a small pad ([methodology][m1t-methodology]).
- **Quote sizes.** Massive moved quote sizes from round lots to shares on 2025-11-03 and promised to regenerate history ([blog][m-roundlots]). All 2007-2025 `quotes_v1` files were rewritten on 2026-04-07..10 with content changes (2020-08-03 went from 2,772,282,190 to 3,088,555,751 B; 2020-08 files grew 11.3%, 2008-06 files 16.5%), which supports but does not prove conversion ([Wayback][m-wayback-2020-08]). market-1t always multiplies by 100 ([snapshot.py][m1t-snapshot]), so its sizes are certainly 100 times too large from 2025-11-03 (the last ~8 test months) and very likely for all dates on current files.
- **Vintages.** Quote files exist in at least three versions: 2024-08-16, rewrites of the Nov-2025 files on 2026-01-15 and 2026-04-09, and April 2026 ([Wayback][m-wayback-2025-11]). Trade files re-uploaded on 2026-03-30..04-14 kept their sizes (2020-08 checked), and Tape B data before 2026-09-21 report tape 1 ([changelog][m-changelog]). Record size and checksum as well as ETag and Last-Modified. The HF release very likely used older round-lot files, so a rebuild will not match it byte for byte.
- **Regulatory breaks.** Tiered round lots apply from 2025-11-03 (100 shares up to $250, 40 up to $1,000, 10 up to $10,000, 1 above) and are reassigned each May and November, so today's `round_lot` is not point-in-time ([Federal Register][fr-mdi]). UTP odd-lot quotes start on 2026-04-27 ([blog][m-roundlots]); the tick and access-fee changes moved to 2026-11-02, after the test ([Federal Register][fr-612]).
- market-1t drops rows until a ticker has both quoted and traded that day, so quote-only pre-market data (such as the NBBO at the 08:30 CPI release) are missing, and its Form T window ignores 13:00 early closes ([methodology][m1t-methodology]). stable-finance labels resampled bars by their first second, a look-ahead ([transforms.py][sf-transforms]), and puts the closing auction at row 23,400, outside the grid ([anchors.py][sf-anchors]). tfwm's holiday CSV is SIFMA's bond calendar for 2021-2025 ([CSV][tfwm-holidays]).

**Implementation notes for M1**
- Run market-1t in its own locked uv environment, e.g. `uvx --from git+https://github.com/fin-ai-lab/market-1t@38da67c065c12e0373a5d56a52a2685d6eccf660 market-1t`. It pins Python <3.13, numpy 1.26.4, polars 1.6.0 (<1.26, because the hash changed) and pyarrow 17.0.0, the only versions it was byte-validated with ([pyproject][m1t-pyproject]).
- `market1t-rebuild plan` must work offline: only `download` has `--dry-run`, and that needs credentials ([download.py][m1t-download]). Enumerate XNYS sessions for explicit bounds (market-1t defaults `--end` to today) and use the table below.
- `market1t-rebuild run`: explicit `--dates` and `--yes`; download (dry run first), convert and snapshot as separate stages; set `--memory-budget-gb` (about 3.3 GB per convert worker, 0.5-2.5 GB per snapshot worker) ([README][m1t-readme]).
- Resume traps: completeness is checked by size only; `convert` never redoes existing Parquet; `snapshot` rebuilds only with `--overwrite` ([jobs.py][m1t-jobs]). Use a fresh root per vintage, and never `run` dates whose flat files were deleted without `--skip-download`.
- Mandatory unit check per quote file: among names at or below $250, the share of nonzero sizes divisible by 100 is near 1 for shares and near 0 for lots. Divide by 100 for shares and record it.
- Partition parity on ARM is inferred from Polars source, not tested: run market-1t's tests on the DGX Spark and a Mac ([CI][m1t-ci], [hasher][polars-hash]). Read output with `scan_parquet` and a ticker filter; a zero bid or ask is missing. The ticker is the only key, so join to a FIGI-based ID map ([ticker events][m-events]).

**Known gaps and risks**: the ×100 bug, vintage drift, no public universe builder, unlicensed stable-finance code, an archive ending in 2024-12, storage, and the licence.

**Next-download estimate**
- M1 one-day test on 2020-08-03, a day in the HF sample with 699 names: quotes 3,088,555,751 B plus trades 1,105,672,164 B, 4.19 GB (the fact-checker's figure; the researcher had estimated 6-10 GB). About 6.4 GB on disk; allow 13 GB ([Wayback][m-wayback-2020-08]). About 5.6 min at 100 Mbit/s plus processing (the authors report about 90 s for a 2026 day on 64 cores). Above the guard, and blocked on plan, keys and permission.
- Full 2008-2025, exact on 2026-11-12 ([quotes][m-quotes-root], [trades][m-trades]): 16.23 TB of flat files (quotes 12.90 TB, trades 3.33 TB, 4,529 days), about 6.1 TB of Parquet and 2.3 TB of snapshots by the README's 2026 ratios (untested on old files); 2026H1 adds 1.53 TB over 123 days. Train 5.05 TB, tune 3.56 TB, test 9.15 TB; peak month 2026-03 at 0.33 TB. TB per year: 2008 0.392, 2009 0.381, 2010 0.367, 2011 0.454, 2012 0.319, 2013 0.281, 2014 0.333, 2015 0.508, 2016 0.714, 2017 0.491, 2018 0.809, 2019 0.789, 2020 1.293, 2021 1.477, 2022 2.079, 2023 1.669, 2024 1.704, 2025 2.174. Download time is 36.1 h at 1 Gbps; compute about 34 h on 64 cores, of which conversion takes at least 9 h because it is read-bound.

## Massive (flat files, security master, corporate actions)

**Coverage**
- Flat files `us_stocks_sip/{day_aggs_v1, minute_aggs_v1, trades_v1, quotes_v1}/YYYY/MM/YYYY-MM-DD.csv.gz`: one gzipped CSV per trading day from 2003-09-10, unadjusted, tickers as traded ([overview][m-overview]). Aggregate columns are `ticker,volume,open,close,high,low,window_start,transactions`, with `window_start` in Unix nanoseconds and no VWAP ([day aggs][m-dayaggs]); minute bars cover 04:00-20:00 ET, with no row for a minute without an eligible trade ([KB][m-missing]). OTC data start on 2021-12-31 ([history KB][m-history]); whether the day files include OTC names is (unverified).
- Security master: `/v3/reference/tickers` with `date=` and `active=false` returns `cik`, `composite_figi`, `share_class_figi`, `delisted_utc`, `primary_exchange` and `type`, with no list date and never a CUSIP ([All Tickers][m-alltickers]). Ticker Events is experimental and records only `ticker_change` ([events][m-events]).
- Corporate actions: `/stocks/v1/splits` (from 1978-10-25) and `/stocks/v1/dividends` (cash only, from 2000-01-15) ([splits][m-splits], [dividends][m-dividends]). Nothing covers spin-offs, mergers or rights offerings ([KB][m-tickerchanges]).
- History: Starter 5 years and Developer 10 years, rolling back from each request; Advanced and Business all history ([history KB][m-history]). Reference and corporate-action data have all history from Starter and 2 years on Basic ([All Tickers][m-alltickers]).

**Access and cost**: individual plans, all under a personal licence ([pricing][m-pricing]): Basic $0 (no flat files), Starter $29/month or $288/year, Developer $79/month or $768/year, Advanced $199/month or $1,920/year (non-professional only). Business costs $2,499/month, $1,999/month with a commitment or $19,188/year, and its intraday data are Fair Market Value rather than SIP ([business][m-business]); 18 months cost about $31,182-38,376 at list, because annual terms are not pro-rated. The human signs up, accepts the terms, signs exchange agreements (otherwise S3 returns 403) and creates a REST key and a separate S3 key pair ([S3 KB][m-s3kb]).

**Terms**: see blockers; develop against synthetic data until an Order Form exists.

**Rate limits**: REST limits are per asset class: Basic 5 requests/min, paid tiers uncapped, reference endpoints a separate bucket of undocumented size; 429 on breach; extra keys add no capacity ([KB][m-ratelimit]). S3 is not metered, but a third party hit 429s when syncing in parallel ([log][m-thirdparty-log]): start with 1-2 streams and back off on 429, 503 and SlowDown. The SDK's sub-second retries cannot clear a 5/min bucket.

**Point-in-time semantics**
- Take the session date from the S3 key. `window_start` is most likely 00:00 ET (REST `t` × 10^6) ([KB][m-restvsfile]), but the docs' sample row decodes to 16:00 EDT and `day_aggs_v1/2019/08/2019-08-12.csv.gz` was found stamped a day late ([fix][zipline-fix]). Flag mismatches and never use it as a knowledge time.
- Daily OHLC uses regular-session, non-Form-T trades (including a close just after 16:00), while volume and transactions cover 04:00-20:00 ET ([Form T KB][m-formt]). Proposed: OHLC known at 16:15 ET and volume at 20:00 ET, with LastModified kept as `published_at`. After an after-close earnings release, day-D volume already contains the reaction.
- Files are complete by about 11:00 ET the next day (often around 00:30) and can be replaced; a 2026-01-02 file was rewritten on 2026-03-30 ([readiness KB][m-ready]). Daily bars absorb late trades ([KB][m-aggbars]), and volume is decimal from 2026-02-23 ([changelog][m-changelog]). Whether tiered round lots change odd-lot flags, and so OHLC, above $250 is (unverified).
- Corporate actions are not point-in-time: `historical_adjustment_factor` is cumulative to today and has been revised, records carry no added-at timestamp, future splits are listed early, and `adjustment_type` gets reclassified (NVDA's 2021 4-for-1 is a `stock_dividend`) ([splits KB][m-splits-kb]). Snapshot daily and compute our own factors. Splits apply from 04:00 ET on `execution_date` ([splits][m-splits]); dividends are known at `declaration_date` 20:00 ET, otherwise on the ex-date pre-market.
- `date=D` answers use current knowledge and were rewritten in the 2025-07-03 migration ([changelog][m-changelog]). `delisted_utc` trails the last trade (Twitter: last bar 2022-10-27, `delisted_utc` 2022-10-31T04:00:00Z), contrary to the API reference ([KB][m-tickerchanges], [Ticker Overview][m-overview-ticker]). Ticker Overview shares and market cap follow report periods, not filing dates, so they cannot be features.
- Tickers are reused: META was an ETF in January 2022, FB now is one, and PARA changed hands in 2026 (Massive's KB names Banzai; SEC's ticker file maps it to Parabolic Technologies) ([KB][m-tickerchanges], [SEC][sec-tickers]). FIGIs are never reused ([OpenFIGI][openfigi]), so key on composite FIGI, then share-class FIGI, then (CIK, ticker episode).

**Implementation notes for M1**
- S3: `https://files.massive.com`, bucket `flatfiles`, `s3v4` signing, region `us-east-1`, path-style, `list_objects_v2` per `YYYY/MM/` prefix ([quickstart][m-quickstart]). A 403 is ambiguous (plan, history window, unpublished, agreements); a 404 means no trading or the wrong dataset ([S3 KB][m-s3kb]). Manifest every object (key, size, ETag, LastModified, sha256), keep old versions, and do not run `aws s3 sync` blindly.
- CSV: read columns by name; `volume` as Float64 or Decimal; `window_start` as Int64 nanoseconds; case-sensitive tickers (BRK.A, ABRpD); a missing row means no trades.
- REST: `https://api.massive.com` with `Authorization: Bearer`; follow `next_url` as given ([REST quickstart][m-rest-qs]). `api.polygon.io` still answers, with no announced sunset ([rebrand][m-rebrand]). Response shapes differ by endpoint for unknown tickers ([KB][m-dashes]), and a range that partly overlaps the plan window returns 200 with rows dropped, so assert the first date ([history KB][m-history]).
- Snapshot `/v3/reference/tickers?market=stocks&date=...&active=true&limit=1000` weekly, plus one undated `active=false` sweep. On `/stocks/v1/*` the `order` parameter is ignored, so pass `sort=...asc` and `limit=5000`; skip the deprecated v3 splits and dividends endpoints. Use XNYS for history, because `/v1/marketstatus/upcoming` is forward-only ([holidays][m-holidays]).
- The SDK is optional: `massive==2.9.1` is pure Python but pins `certifi<2027.0.0` and lacks Arrow support ([PyPI][m-pypi-291]).

**Known gaps and risks**: the licence; no spin-off or merger data, so total returns jump and acquired names just stop; unknown coverage of delisted names; a daily close that is the last eligible trade rather than a documented auction price ([Form T KB][m-formt]); Fair Market Value intraday data on Business; changing terms.

**Next-download estimate**: nothing before a plan and permission exist; then one recent day file (0.21-0.27 MB per a third-party log). Day aggregates for 2003-09-10 to 2026-06-30: 5,737 files (3,854 train, 757 tune, 1,126 test sessions), about 1-1.5 GB gzipped, minutes if bandwidth-bound, under the guard. Minute aggregates: 22,848,818-26,083,580 B per recent day ([readiness KB][m-ready]) and about 70-120 GB in total (an unverified extrapolation). Security master: about 10-15.5k requests for weekly snapshots; dividends about 200.

## Macro series: FRED/ALFRED and primary-source alternatives (Treasury par yield curve, NY Fed EFFR, Board H.15)

**Coverage**
- FRED: DGS2 from 1976-06-01, DGS10 from 1962-01-02, DFF (7-day) from 1954-07-01, VIXCLS from 1990-01-02. ALFRED vintages on 2026-11-12: DGS2 5,150, DGS10 5,149 and DFF 5,164, from 2005-06-28 and weekly until 2006-02-21; VIXCLS 3,972 from 2010-11-22 ([DGS10][alfred-dgs10], [VIXCLS][alfred-vix]). 65% of rows predate their series' first vintage.
- Treasury par yields come from FRBNY indicative bid quotes at or near 3:30 PM ET and are usually posted by 6:00 PM ET; the monotone convex method applies from 2021-12-06 ([methodology][ust-method]), old-method yields remain official, and the methods differ by -0.1 to 0.5 bp on average ([info sheet][ust-infosheet]).
- NY Fed EFFR: published for the prior business day at about 9:00 a.m. ET, revised the same day at about 2:30 p.m. only for a move above 1 bp; a volume-weighted median since 2016-03-01 ([NY Fed][nyfed-rates]).
- Board H.15: posted Monday to Friday at 4:15 pm (ET, inferred from the GMT Last-Modified), not on holidays, with data through the previous business day; the XML zip keeps only the latest version ([H.15][h15]). Data Download Program bookmarks stop working on 2027-03-31 ([DDP FAQ][ddp-faq]).
- VIX: disseminated every 15 s, 09:31-16:15 ET, with shorter hours on half-days; launched on 2003-09-22, so earlier values are back-tested ([Cboe][cboe-method]).

**Access and cost**: $0, except Cboe (unknown). A FRED key needs a free account, one key per application, and registering accepts the API terms ([keys][fred-key]). The NY Fed API needs no key ([OpenAPI][nyfed-api]).

**Terms**: FRED is blocked (ML and caching), VIX needs Cboe; Treasury is CC0, the Board public domain, and NY Fed data need its notice (see blockers). FRED's public-domain labels on DGS2, DGS10 and DFF apply only where no prohibited use is involved ([FRED legal][fred-legal]).

**Rate limits**: FRED allows 120 requests per minute, then returns 429 and may block temporarily; whether per key or per IP is not stated ([errors][fred-errors]). A request returns at most 100,000 observations and 2,000 vintage dates in JSON or XML ([observations][fred-obs]); third parties report that the 2,000 cap also applies to real-time windows, with an HTTP 400 (unverified) ([EconGraph][econgraph]). Budget at most 1 request/s. The other sources document no limits.

**Point-in-time semantics**
- FRED and ALFRED give dates, never times, and FRED runs on US Central time. Store `knowledge_time` in UTC and never treat a date as known from 00:00. Vintage dates are release dates that FRED assigns, not load times ([ALFRED deck][alfred-deck]).
- DGS2, DGS10, DFF: `realtime_start` is the H.15 publication date, normally the next Board business day; FRED loaded the 2026-11-12 release about a minute after posting ([DGS10][fred-dgs10]).
- VIXCLS: `realtime_start` is set back to the trading date, although FRED loads the close the next morning at about 08:37 CT, and later on slow days (2026-09-23..25) ([VIXCLS][fred-vix], [calendar][fred-cal-200]). A date-only as-of join leaks the post-FOMC VIX close into a 14:00 ET event.
- Rows older than a series' first vintage carry it as a placeholder, which is not a knowledge time, and ALFRED's "initial release" output is wrong for them ([help][alfred-help]). About 76% of DGS10's and 75% of VIX's pre-2019 rows are placeholders.
- Proposed first-release rules: DGS2 and DGS10 at 16:30 ET on the H.15 date (18:30 ET on day t if taken from Treasury); EFFR at 14:30 ET on its NY Fed publication day (16:30 ET on the H.15 date if taken via H.15); VIX at 16:30 ET on day t. With ALFRED, take the later of rule and vintage, and record `kt_source`.
- The NY Fed API returns only the current EFFR, with a `revisionIndicator`, so first prints of revised days are lost; hence the 14:30 rule ([OpenAPI][nyfed-api]). The Board closes on Fridays before Saturday holidays while the NY Fed publishes (e.g. 2026-07-03) ([K.8][k8]), and 95 business days since 2006-02-22 have no DGS10 vintage: build the H.15 calendar from observed releases. That DFF weekend rows always carry the previous business day's EFFR is (unverified) beyond the 2026-11-11 example ([DFF][fred-dff]).
- Breaks: EFFR method 2016-03-01, Treasury method 2021-12-06, VIX back-tested before 2003-09-22. VIX closes 15 minutes after the NYSE, so VIX(t) against day-t returns at a 16:00 decision is a look-ahead.

**Implementation notes for M1**
- Put FRED behind a flag that defaults to off. Default adapters: NY Fed `GET https://markets.newyorkfed.org/api/rates/unsecured/effr/search.json?startDate=YYYY-MM-DD&endDate=YYYY-MM-DD` ([OpenAPI][nyfed-api]); the Board's `https://www.federalreserve.gov/releases/h15/data/FRB_h15_xml.zip` for reconciliation ([H.15][h15]); Treasury par yields, endpoint still to be identified. No Data Download Program URLs.
- If FRED is permitted: call `fred/series/vintagedates` once per series ([vintagedates][fred-vintagedates]); fetch `fred/series/observations` with `output_type=1` in windows of at most 1,000 vintages, halving a window on the vintage-cap 400; always send both real-time bounds, since the docs disagree on defaults ([real-time][fred-realtime]); merge rows clipped at window edges, a behaviour reported only by third parties (unverified) ([fredapi PR][fredapi-52]). `.` means missing. fredapi and pystlouisfed do not window, and the v2 API has no vintages ([v2][fred-v2]).
- Never use FRED's "FOMC Press Release" release as a meeting calendar: it has a date for every calendar day ([calendar][fred-cal-101]).
- Fixture from 2026-11-12: DGS10 for 2026-11-10 is 4.98 and DGS2 4.73, matching the H.15 10-year and 2-year ([DGS10][fred-dgs10]).

**Known gaps and risks**: no vintages from primary sources (revisions rare but unmeasured); an unknown Treasury endpoint; unverified release times before 2016 (add buffer); an unverified VIX close time before methodology v6.0; and the VIX licence.

**Next-download estimate**: M1: the H.15 zip at 4,288,427 B ([H.15][h15]) plus small NY Fed and Treasury pulls; $0, under the guard. FRED if permitted: about 30 requests (about 30 s), up to 36 MB of JSON, about 66k rows and an estimated 1-2 MB of Parquet, then about 8 requests a day ([observations][fred-obs]).

## Event calendars (FOMC, BLS CPI and Employment Situation)

**Coverage**
- FOMC: 174 scheduled decisions from 2005-02-02 to 2026-10-28, eight a year except seven in 2020 (03-17/18 cancelled); the next is 2026-12-09 ([calendar][fomc-cal], [history][fomc-hist-idx]). The 2027 schedule revised on 2026-11-12 (12:45 p.m. EST) has seven decisions: Oct 26-27 becomes a strategy meeting and Dec 7-8 moves to Nov 16-17 ([release][fed-20261112]).
- Statement times: 2:15 p.m. ET until 2013-01-30 (57 decisions), 12:30 p.m. at the eight 2011-2012 press-conference meetings, 2:00 p.m. from 2013-03-20 (109) ([2011][fed-20110324], [2013][fed-20130313]). Pages print the time only from 2016-01-27 ([2016][fed-20160127]); 2:15 rests on the 2011 and 2008-11-20 releases ([2008][fed-20081120]) and convention. The 2012 press-conference pages print 12:20 (01-25) and 12:35 (04-25, 06-20, 09-13), but news put 2012-09-13 at 12:30 ([page][fed-presconf-2012]).
- 26 unscheduled actions are drafted, e.g. 2008-10-08 07:00 EDT and 2020-03-15 17:00 EDT (a Sunday), plus Board or joint actions on 2010-02-18 (16:30 EST), 2023-03-12 (18:15 EDT) and 2023-03-19 (17:00 EDT), the last two on Sundays inside the test ([2020-03-15][fed-20200315], [2023-03-12][fed-20230312]). Missing: the 2020-04-09 08:30 EDT Board action ([release][fed-20200409]). None occurred in 2021-2024 or in 2026 so far ([2026 list][fed-press-2026]).
- BLS: 262 CPI and 262 Employment Situation releases through 2026-11-10 and 2026-11-06, all at 8:30 a.m. ET ([CPI][bls-cpi-archive], [jobs][bls-empsit-archive]). Only funding lapses moved dates (10 rescheduled, 2 cancelled):
  - 2013: September jobs Oct 4 → Oct 22, September CPI Oct 16 → Oct 30, October jobs Nov 1 → Nov 8, October CPI Nov 15 → Nov 20 ([BLS][bls-2013]).
  - 2025: September CPI Oct 15 → Oct 24, recorded only in a notice last modified 2025-10-10 ([notice][bls-notice]); September jobs Oct 3 → Nov 20; October jobs and CPI cancelled; November jobs Dec 5 → Dec 16; November CPI Dec 10 → Dec 18 ([BLS][bls-2025]).
  - 2026: January jobs Feb 6 → Feb 11, January CPI Feb 11 → Feb 13 ([BLS][bls-2025]); the lapse dates come from news reports.
  - On 2024-05-15 some April CPI files went up about 30 minutes early ([BLS][bls-early]).
- Counts from actual dates: train CPI 168, jobs 168, FOMC 112; tune 36, 36, 23; test 53, 53, 36 ([calendar][fomc-cal]). CPI and an FOMC decision shared a day 14 times (e.g. 2013-10-30, 2024-06-12); a CPI or jobs release followed 64 of the 174 decisions within 1-7 days, 78 if same-day CPI counts ([CPI][bls-cpi-archive]).

**Access and cost**: $0, no accounts. Send a User-Agent with a monitored project contact address.

**Terms**: public domain. Commit the CSVs with a `source_url` on every row and the attribution line above.

**Rate limits**: BLS blocks bots that hit it several times a second and may block bots without contact details ([policy][bls-pss]); `robots.txt` allows every path needed ([robots][bls-robots]). The Fed publishes no crawl rule ([policies][fed-policies]). Fetch serially, at most once every 2 s, with conditional GETs, and stop on 403 or 429; keep archive.org to about 20 requests a minute and honour `Retry-After` ([IA][ia-blog], [wayback][wayback-client]). BLS ignores Range and its release pages are 1.07-1.37 MB, so stream and stop after about 60 KB ([page][bls-cpi-20251024]).

**Point-in-time semantics**
- `knowledge_time` is the public release time (the Fed's release time, or the BLS embargo lift at 08:30 ET); `event_time` is the reference month or decision date. Store the ET time with its offset and in UTC: 2025-10-24T08:30-04:00 is 12:30Z, and the 2026-10-28 14:00 EDT statement is 18:00Z, as in the Fed RSS ([RSS][fed-rss]). Use `zoneinfo`, not the BLS ICS file's US-Eastern zone, which encodes only post-2007 rules ([ICS][bls-ics]); the 2023-03-12 18:15 EDT action fell on the day DST began.
- Sessions: BLS releases precede the open, but nine fell on Good Fridays (CPI 2017-04-14, 2020-04-10; jobs 2007-04-06, 2010-04-02, 2012-04-06, 2015-04-03, 2021-04-02, 2023-04-07, 2026-04-03), when bond markets could trade ([SIFMA][sifma-gf]). FOMC statements are intraday, so windows start at t+1 or split the day. Sunday actions map to Monday, and 2010-02-18 16:30 to the next day.
- Keep the schedule as known at time τ apart from realized events: year pages are revised after the fact ([archive][bls-sched-arch]), reschedules have their own knowledge times (the 2025-10-10 notice), and FOMC schedules change (2012-05-16, 2026-11-12) ([2012][fed-20120516b]).
- Never use schedule pages, ICS files, feed timestamps or URL slugs as evidence of release time: Atom entries for the Jul-Nov 2026 jobs reports are stamped around 07:50 ET ([feed][bls-feed]), and the June 2007 statement sits at a slug dated 06-18 ([page][fed-20070618]).
- Cancelled releases are status rows, never events. October 2025 payroll data first appeared on 2025-12-16, and the October household survey and all-items CPI were never produced ([BLS][bls-2025]). For 2024-05-15 keep 08:30 with an early-availability flag.

**Implementation notes for M1**
- Sources: Fed `fomccalendars.htm` (2021 on), `fomchistorical{YYYY}.htm` (2005-2020) and `monetary{YYYYMMDD}{a|b|c}.htm`; BLS `/bls/news-release/{cpi|empsit}.htm`, `/news.release/archives/*_{MMDDYYYY}.htm` from February 2008, `/news.release/history/*.txt` before, and the two lapse pages.
- Traps: strip HTML comments first, because the jobs archive hides a 2026-12-04 entry and a 2027 placeholder in them ([jobs][bls-empsit-archive]); two 2019 jobs links are absolute URLs; FOMC headings vary ([2017][fomc-hist-2017]); press-conference URLs vary (`fomcpressconf20260128.htm` works, `fomcpresconf20260128.htm` is a 404), so take links from the calendar page; use dates shown on pages, not slugs.
- Build: an on-demand fetcher writes a raw cache outside git, a deterministic offline parser builds rows, and a reviewed overrides CSV of about 40 rows with source URLs covers unscheduled actions, the 2005-2015 time rules, original lapse dates and cancellations. Record `time_source` and `time_precision` per row; commit only the CSVs and a source manifest.
- Tests: no future rows; archive dates equal year-page dates; Wayback plans differ only on lapse rows; every embargo line says 08:30; eight FOMC decisions a year except 2020 and 2027 (seven); 2016+ headers say 2:00 p.m.; UTC conversion round-trips.
- FOMC minutes (2:00 p.m., three weeks after each meeting), projections and press conferences are further intraday confounders, not yet in the calendar.

**Known gaps and risks**: rule-based times for 2005-2015 and "immediate release" actions; disagreeing 2012 minutes; an undecided scope for Board actions; planned BLS dates before 2008-10 not checked against snapshots; and future lapses.

**Next-download estimate**: about 800-900 requests, 27-45 min at one every 2-3 s. The raw cache is about 50 MB, mostly about 31 MB of BLS header reads and about 10 MB of Fed release pages. Committed CSVs are under 200 KB (BLS 526 rows, about 123 KB; FOMC 175 rows, about 45 KB; unscheduled about 8 KB), and monthly refreshes need under 10 requests. $0, under the guard.

## SEC EDGAR

**Coverage**
- `https://data.sec.gov/submissions/CIK##########.json`: `filings.recent` (at least a year or 1,000 filings) plus page files, with 16 columns including `accessionNumber`, `filingDate`, `reportDate`, `acceptanceDateTime`, `form` and `items` ([API][sec-api], [Apple][sec-aapl]). History starts in 1994 ([access][sec-access]), but electronic filing was phased in only by 1996-05-06 ([33-7427][sec-phasein]).
- Real acceptance times start around May 2002. Earlier ones are mostly midnight-ET placeholders (T04:00:00Z or T05:00:00Z), though not all (a 1994 Apple filing is real) ([1994][sec-idx-1994]), so test for exactly 00:00:00 ET, not a date cutoff.
- Earnings items: none dedicated before 2003-03-28; Item 12 from then ([33-8176][rel-8176]), furnished as Item 9 until EDGAR supported it ([2003-41][sec-2003-41]) with Release 8.6, whose Filer Manual came out on 2003-07-28 ([digest][sec-digest-2003]); Item 2.02 from 2004-08-23 ([33-8400][rel-8400]). Other forms also use `items` (for ABS-15G, 2.02 is a due-diligence finding), so filter on the 8-K family first ([FAQ][sec-faq]).
- Item 2.02 is due within four business days ([8-K][form8k]). 94 of Apple's 99 earnings 8-Ks were accepted between 16:00 and 16:45 ET; others came hours later or were intraday preannouncements ([Apple][sec-aapl], [page 001][sec-aapl-001]).
- Bulk: `submissions.zip` is 1,574,117,096 B and `companyfacts.zip` 1,423,778,421 B ([bulk][sec-bulk]). The optional Financial Statement Data Sets are 71 zips for 2009q1-2026q3, about 5.4 GB, reprocessed in December 2024 ([FSDS][sec-fsds]).

**Access and cost**: $0, with no account or key. Send `SEC_USER_AGENT` in the form `Name contact@domain` and `Accept-Encoding: gzip, deflate`, and let the client set `Host` ([access][sec-access]).

**Terms**: public and reusable (see blockers). The FSDS are open government data ([data.gov][datagov-fsds]); the licence status of EDGAR filing assets in SEC's catalogue is (unverified).

**Rate limits**: at most 10 requests per second in total across all machines; offenders are limited until they stay under the threshold for 10 minutes, and unclassified bots are not allowed ([policy][sec-privacy]). Use one fetching process for the DGX, the Macs and any shared NAT, a token bucket of at most 5 per second, and a cool-off of at least 10 minutes after a 403 or 429.

**Point-in-time semantics**
- `acceptanceDateTime` in the JSON is true UTC with historical DST rules, checked on eight filings from 2001-2026 ([SGML][sec-hdr-aapl-26], [2003][sec-idx-2003]). Index-page, SGML and XBRL RSS acceptance times are naive ET wall-clock times despite the FAQ's "EST" label ([FAQ][sec-faq]). Never take the UTC date as the ET date: 2025-07-09T01:18:13Z is 21:18 ET on 2025-07-08.
- Held filings: a transmission starting after 5:30 p.m. ET is filed the next business day (Forms 3, 4, 5, 144, Schedules 13D/13G and 14N and Rule 462(b) are allowed until 10 p.m.) ([eCFR][ecfr-232-13]), and most filings, including 8-K, 10-Q and 10-K, are only disseminated then ([status][sec-status]). A held 8-K accepted at 21:18 ET on 2025-07-08 appeared at 06:01 ET the next day, while an Apple 8-K accepted at 18:55 kept its date ([SGML][sec-hdr-aapl-20]). Detect holds by a `filingDate` later than the ET acceptance date.
- Rule: placeholders get `filingDate` 22:00 ET at date precision; held filings get `filingDate` 06:00 ET plus a buffer; the rest get acceptance plus 5 minutes, since the lag is typically 1-3 minutes and no availability timestamp exists ([FAQ][sec-faq]). Never go earlier than acceptance. The rule is unvalidated before 2003, when EDGAR's hours changed ([digest][sec-digest-2003]).
- EDGAR days are not NYSE days: EDGAR closes on federal holidays, including Columbus Day and Veterans Day, and opens on Good Friday ([calendar][sec-cal]). It closed on 2025-12-24 and 12-26 while the NYSE traded (the NYSE side comes from a news report) ([notice][sec-closed-dec2025], [news][nyse-dec2025-news]); both closed on 2025-01-09 ([notice][sec-closed-jan2025]). Trust `filingDate` and map to sessions with XNYS.
- An Item 2.02 acceptance bounds first public availability; it is not the press-release time. `reportDate` is the date of the earliest event in the 8-K ([8-K][form8k]). Flag `late_8k` when acceptance is after `reportDate`, and fall back to the 10-Q or 10-K when no 2.02 exists (Instruction 4).
- JSON company fields are current snapshots, so use the per-filing SGML header ([SGML][sec-hdr-25]); `formerNames` dates are encoded inconsistently, so take the UTC date part ([Exxon][sec-xom-old]). Ticker to CIK is not point-in-time: XOM moved to CIK 2115436 on 2026-07-01, DIS, GOOG and GOOGL show the same pattern, WBD is gone and PARA is reused ([tickers][sec-tickers]); accessions shared by the old and new CIK link the chain ([Exxon][sec-xom-old]).

**Implementation notes for M1**
- Page files are numbered newest-first and shift as filings age: fetch the main file and all pages in one session and deduplicate on `accessionNumber` ([Exxon][sec-xom-old]). Parse acceptance as UTC and pass unknown columns through (`isXBRLNumeric` appeared in 2026-04).
- Keep 8-K and 8-K/A, 10-Q, 10-K and their variants (10-K405, 10-KT, 10-QT, 10-KSB, 10-QSB), plus 8-K12B and 8-K12G3 as successor markers. Foreign issuers file 6-K, 20-F and 40-F without items.
- Archives honour Range when `Accept-Encoding: gzip` is sent, and HEAD returns sizes, so peeking at large files costs kilobytes ([master.idx][sec-masteridx]). data.sec.gov sends no ETag or Last-Modified, so cache by TTL.
- Never join on `company_tickers.json`: it is current-only, and CDN edges served two versions seconds apart. `submissions.zip` has a single ETag, which suits freezing the test vintage; whether it contains the page files is (unverified).
- Map tickers to CIKs from a point-in-time master (Massive `date=`, which starts in 2003-09 and whose `cik` semantics are unverified, or CRSP/WRDS) plus reviewed CIK chains. Cover pages have carried trading symbols since 2019-05-02 ([FAST Act][sec-fast]).
- Self-test on each ingest: the SGML acceptance time, localised to ET, must equal the JSON value. Fixtures: 0000320193-26-000018 = 2026-07-30T20:30:28Z; 0001140361-25-025275 = 2025-07-09T01:18:13Z; 0001104659-03-004649 = 2003-03-21T00:36:01Z; 0000912057-01-544436 is a placeholder.

**Known gaps and risks**: date-only acceptance before 2002; thin coverage in 1994-1996; Item 2.02 lags and gaps; no ticker history in SEC data; schema drift; FSDS rewrites and the look-ahead field `prevrpt` ([FSDS doc][sec-fsds-pdf]); acceptances on non-business days, so no hard operating-hour asserts; and a proposed optional semiannual Form 10-S (secondary sources, unverified) that could change 10-Q cadence after the test ([Deloitte][sec-10s]).

**Next-download estimate**: M1 sample: CIKs 320193 (with page 001), 34088 and 2115436 plus a few SGML headers, about 10-20 GETs and under 1 MB (Apple's main file is 28,326 B gzipped; JPM's is 474,884 B) ([JPM][sec-jpm]). Full: about 1,500-2,500 CIKs for a 500-name point-in-time universe over 1994-2026, about 3-8k requests, 15-30 min at 5 per second or less, 100-250 MB gzipped and 150-300k index rows; nightly refreshes need about 500 requests. All under the guard; `submissions.zip` (1.57 GB) is a one-request alternative.

## Crypto (Kraken primary, Coinbase, Binance)

**Coverage**
- **Kraken OHLCVT Full r1** (generated 2026-10-01): 2013-09-11 to 2026-09-30, one `{ALTNAME}_{MINUTES}.csv` per pair and interval (1, 5, 15, 60, 240, 720 and 1,440 min) without a header: timestamp (Unix s, bar start), open, high, low, close, volume (base) and trades; bars without trades are omitted ([support][kr-ohlcvt], [archive][kr-part04]). The MANIFEST says 1,760 pairs; the zip holds 1,758 complete pairs plus a 1-minute-only BTCUSD. 351 pairs are no longer listed (e.g. FTMUSD, MATICUSD, MKRUSD, LUNA2USD, USTUSD), while LUNAUSD still is ([AssetPairs][kr-assetpairs]). BSV (traded until 2019-04-29), DAO and ICN are missing ([BSV][kr-bsv]). The archive covers the test and its five-day horizon (to 2026-07-08).
- Breadth, estimated from file sizes (unverified): about 13 currently listed USD coins at 2019-01-01, 31 at 2021-01-01 and 61 at 2022-01-01, so 50 coins only from about 2021. Kraken's EUR, GBP and AUD FX pairs seem to start around 2019-2020 (inferred), so earlier EUR volume needs external FX.
- **Coinbase Exchange**: 847 products (331 delisted; 497 USD-quoted, 93 of them delisted) without listing dates; renames create new IDs (MATIC-USD → POL-USD) ([products][cb-products]). Candles come at six granularities from 60 to 86,400 s, at most 300 per request, as `[time, low, high, open, close, volume]`, possibly incomplete and absent for intervals without ticks ([candles][cb-candles]); whether delisted products keep candles is undocumented.
- **Binance Vision**: monthly and daily zips per symbol, each with a SHA256 `.CHECKSUM`; BTCUSDT hourly files run from 2017-08 (111 months, about 42.8 KB each) ([listing][bn-s3-btc1h]); 12 columns including quote volume and trade count ([README][bn-readme]); delisted symbols kept; the count of 3,767 symbols is (unverified).

**Access and cost**: $0, no accounts. Kraken's parts sit on its CDN and accept byte ranges; quarterly zips are 523,665,624 B (2026Q1), 537,866,903 B (Q2) and 576,348,633 B (Q3), and old vintages are not kept (2025Q4 returns 404) ([support][kr-ohlcvt], [2025Q4][kr-2025q4]). From the US, `api.binance.com` returns 451 while `data.binance.vision` is reachable ([ping][bn-ping]). Massive crypto aggregates (from 2013-11-01; Currencies Starter $49/month or $470/year) are a licensed alternative under the same ML ban ([crypto aggs][m-crypto-day]).

**Terms**: see blockers.

**Rate limits**: Coinbase allows 10 public requests/s per IP (bursts to 15), then 429, and candles share that limit ([limits][cb-rate]). Kraken stays within limits at one call per second per IP, with extra per-pair limits on OHLC and Trades ([limits][kr-rate]); its REST OHLC returns only the latest 720 bars, the last uncommitted ([OHLC][kr-ohlc]). Binance Vision publishes no number, and its terms require obeying posted limits ([terms][bn-terms]).

**Point-in-time semantics**
- Bars are stamped at their start in UTC; for Kraken's REST API that is an assumption to test ([OHLC][kr-ohlc]). Binance uses milliseconds before 2025-01-01 and microseconds after, with close time = open + interval − 1 unit ([README][bn-readme]). Store `event_time` = open and `event_end` = open + interval, and set `knowledge_time` = close + 1-5 s (as-if-live), with a strict mode that takes the later of close and vintage publication. Drop bars still in progress.
- Daily bars end at 00:00 UTC (19:00 or 20:00 ET), so build NYSE-aligned windows from hourly bars (16:00 ET is 21:00 UTC in winter, 20:00 UTC in summer). FOMC at 14:00 ET falls on the hour; CPI at 08:30 ET falls mid-hour, so use 15-minute bars or end the pre-window at the previous full hour. The horizon is the UTC span of the next five US trading days, and a 50×50 covariance needs hourly or finer bars.
- A missing bar means no trades (undocumented for Binance): never fabricate volume, and treat outages as missing.
- Universe: rank monthly on trailing 30-day USD notional from closed bars, including pairs delisted later, never on current listings. Use dated identity maps (MATIC → POL, RNDR → RENDER, FTM → S, MKR → SKY, XBT = BTC, XDG = DOGE). Binance's LUNAUSDT switched to Terra 2.0 on 2022-05-31 at 06:00 UTC (secondary source) ([report][luna-fm]). USDT is not USD (UST depegged in 2022-05, USDC in 2023-03); Kraken and Coinbase volumes are in base units; Binance's zero-fee BTC pairs (2022-07-08 to 2023-03-22) inflate volume ([Kaiko][kaiko-zerofee]).

**Implementation notes for M1**
- Kraken: concatenate the parts and check both the part hashes ([SHA256SUMS][kr-sums]) and the reassembled-zip hash on the support page (`bc273e90…b1c7`). part02 was re-uploaded on 2026-10-16, after part04 (central directory and CRCs, 2026-10-06), and the hash file changed again on 2026-11-11, so CRC-check every member and refuse to ingest on any mismatch; there are no per-file checksums (the README cites an absent `SHA256SUMS.txt`). Skip `README.md`, `MANIFEST.json`, `BTCUSD_Daily_OHLC.csv`, `BTCUSD_1.csv` and 42 stray `*_30.csv` files ([archive][kr-part04]). Accept a local path so the human can download manually.
- Kraken pairs: map explicitly from AssetPairs, with Wayback captures (2015-05, then monthly 2021-04 to 2026-11) for delisted pairs ([CDX][kr-wayback-cdx]); do not parse by longest suffix, because AUSD, TUSD (Threshold), SUSD (Sonic) and short tickers collide with stablecoin names.
- Exclusions: explicit, dated lists of stablecoins, fiat, wrapped tokens, liquid-staking tokens, leveraged tokens, commodity tokens and tokenized equities, not prefix rules (WLD, WIF and WAVES are ordinary assets).
- Coinbase probes: the earliest candle of each major, and a delisted product (UST-USD daily for 2022-05). Use windows of exactly 300 × granularity, remap the columns, sort and deduplicate, at 3-5 requests/s ([candles][cb-candles]).
- Binance, only if cleared: parse the S3 XML properly (newer entries carry checksum tags); prefer daily files where monthly ones differ, as an open issue reports for rows in 2020-2022 ([issue #475][bn-issue475]); expect rewrites missing from its "exhaustive" update list (BTCUSDT monthly files rewritten on 2023-12-12, 2025-10-08 and 2026-11-10) ([listing][bn-s3-btc1mo]).
- Keep raw files immutable with manifests (URL, sha256, ETag, Last-Modified, retrieval time, terms version), and normalise to Parquet with `asset_id`, venue, symbol, quote, `event_time`, `event_end`, `knowledge_time`, OHLC, base and quote volume, trades and `vintage_id`.

**Known gaps and risks**: thin breadth before 2021; older Kraken delistings missing; Kraken's automation clause and state exclusions; Coinbase consent and delisted candles; Binance's legal status; no in-venue FX before about 2019; and "largest coins" by venue volume rather than market cap (Coin Metrics Community data, CC BY-NC 4.0 at 10 requests per 6 s, can cross-check) ([Coin Metrics][coinmetrics]).

**Next-download estimate**: M1 Kraken archive: five parts, 9,546,553,626 B (33,610,251,765 B unpacked), 12.7 min at 100 Mbit/s; peak disk about 21 GB for hourly and daily files, or 52.7 GB for everything, unless parts are deleted after hashing ([support][kr-ohlcvt]). Above the guard; a manual download by the human is preferred. Smaller: the 2026Q3 zip (576,348,633 B; contents not inspected), also manual; a range-read of the 50 largest USD pairs (about 72 MB) needs Kraken's consent. Coinbase: a few requests for the probe; 50 products hourly and daily take about 7.5-9k requests, 25-50 min and 150-180 MB of JSON. Binance, if cleared: 50 symbols take about 15-22k requests and up to about 239 MB.

## Point-in-time approximations

| Source | Issue | Proposed approximation | Conservative? |
|---|---|---|---|
| FRED DGS2, DGS10, DFF | Vintages are dates; FRED loads about a minute after the 16:15 ET posting ([DGS10][fred-dgs10]) | 16:30 ET on the H.15 publication date | Yes |
| FRED, all series | Pre-archive rows carry the first vintage as a placeholder ([help][alfred-help]) | Publication rules; extra buffer before 2016 | Yes, if buffered |
| FRED VIXCLS | `realtime_start` set back to the trading date; loaded next morning ([VIXCLS][fred-vix]) | Day t 16:30 ET (16:15 close + 15 min), never midnight | Yes; "next FRED business day 09:45 ET" is too early on late loads |
| VIX half-days | Dissemination ends early ([methodology][cboe-method]) | `event_time` from the actual close; keep the 16:30 rule | Yes |
| ALFRED revisions, gaps | Revision times unknown; load gaps (DFF 2017-06-01 to 06-09) ([DFF][alfred-dff]) | End of the `realtime_start` day (Chicago); later of rule and vintage | Yes |
| Treasury par yields | No posting timestamp; usually by 18:00 ET ([methodology][ust-method]) | Day t 18:30 ET; live data never before fetch time | Mostly |
| NY Fed EFFR | Only the current, possibly revised value ([OpenAPI][nyfed-api]) | 14:30 ET on the publication day; weekend rows inherit it | Yes |
| Board H.15 calendar | Irregular closures ([K.8][k8]) | Observed releases, not a holiday rule | Yes |
| Market-1T rows | About 128 ns boundary error ([methodology][m1t-methodology]) | `knowledge_time` = interval end, optional pad | Negligible look-ahead |
| Market-1T forward fills | Prices carried into rows without trades | Aggregate over `n > 0` only | Yes |
| Market-1T early closes | Five sessions missing ([tfwm CSV][tfwm-holidays]) | Trading days with missing data, not holidays | Yes |
| Market-1T universe | Unpublished, possibly not point-in-time ([ingest.py][sf-ingest]) | External mask; own universe from prior data | Yes |
| 1 Hz daily close | Auction may fall after the grid (unverified) ([anchors.py][sf-anchors]) | 16:00:00 mid or last-minute VWAP, checked against official closes | Yes |
| Massive trades | SIP receipt time; corrections not applied ([trades doc][m-trades-md]) | `event_time` = dissemination time; robust or mid-quote estimators | Yes |
| Massive quote sizes | Lots vs shares; semi-annual lot changes ([Federal Register][fr-mdi]) | Detect unit per file; lot regime per ticker and half-year | Yes |
| Massive day bars | Unclear `window_start`; one defective file ([fix][zipline-fix]) | Session date from the S3 key | Yes |
| Massive day bars | OHLC from the session, volume to 20:00 ET ([Form T KB][m-formt]) | OHLC at 16:15 ET; volume and transactions at 20:00 ET | Yes |
| Massive flat files | Silent replacements; late trades absorbed ([readiness KB][m-ready]) | Versioned manifests; frozen test vintage; `published_at` | Partly |
| Massive corporate actions | No added-at times; cumulative factors ([splits KB][m-splits-kb]) | Daily snapshots; own factors; ratio from 04:00 ET on `execution_date`; dividends at declaration 20:00 ET | Yes for adjustments |
| Massive reference data | `date=D` rebuilt; `delisted_utc` after the last trade ([KB][m-tickerchanges]) | Raw snapshots; last bar as stop date; no Ticker Overview shares | Partly |
| Ticker reuse, renames | META, FB, PARA; CTL → LUMN, UTX → RTX; XOM's new CIK ([tickers][sec-tickers]) | `asset_id` on composite FIGI with dated maps; reviewed CIK chains | Yes |
| EDGAR before 2002-05 | Midnight-ET placeholders ([1994][sec-idx-1994]) | `filingDate` 22:00 ET, date precision | Yes |
| EDGAR after 17:30 ET | Held to the next business day ([eCFR][ecfr-232-13]) | `filingDate` 06:00 ET + buffer if `filingDate` is after the ET acceptance date | Yes from 2003 |
| EDGAR dissemination | No availability timestamp ([FAQ][sec-faq]) | Acceptance + 5 min | Mostly |
| EDGAR Item 2.02 | Bounds, but is not, the release time ([8-K][form8k]) | Leakage-safe bound; `late_8k` flag | Yes |
| EDGAR company fields | JSON fields are current ([Apple][sec-aapl]) | Per-filing SGML header | Yes |
| FOMC 2005-2015 | No printed time ([2011][fed-20110324]) | 2:15 and 12:30 conventions; wider windows | Partly |
| Fed "immediate release" | No printed time ([transcript][fed-transcript-0121]) | Transcript or news times; next-session mapping | Yes for day mapping |
| BLS 2024-05-15 | Files about 30 minutes early ([BLS][bls-early]) | 08:30 plus an early-availability flag | No (flagged) |
| Schedules known at τ | Pages and FOMC schedules revised later ([archive][bls-sched-arch]) | Separate schedule-as-known table; notice dates as proxies | Partly |
| NYSE ad hoc closures | Calendars embed them retroactively ([XNYS][xcal-xnys]) | Calendar as known at t for features; announcement times to source | Yes once sourced |
| Crypto bars | No publication time in archives ([support][kr-ohlcvt]) | Bar close + 1-5 s; strict mode adds vintage time | As-if-live: no; strict: yes |
| Crypto archives | Silent re-uploads ([SHA256SUMS][kr-sums]) | Pinned hashes; immutable raw copies | Partly |
| Binance LUNAUSDT | Symbol reused in May 2022 ([report][luna-fm]) | Split at 2022-05-31 06:00 UTC | Yes |

## Next downloads for M1

| Item | Files | Size | Time | Cost | Needs | Under the 2 GB guard? |
|---|---|---|---|---|---|---|
| Market-1T 2020-03 sparse slice ([index][hf-2003-index]) | 132 | 2,502,351,803 B | 7.5 / 4 / 2 min at 50 / 100 / 200 Mbit/s | $0 | Nothing (`HF_TOKEN` optional); pinned SHA | No: `--yes` |
| Event calendars, Fed and BLS pages ([CPI][bls-cpi-archive], [calendar][fomc-cal]) | About 800-900 requests | About 50 MB raw cache; under 200 KB committed | 27-45 min | $0 | Contact address for the User-Agent | Yes |
| EDGAR sample via the submissions API ([Apple][sec-aapl]) | About 10-20 GETs | Under 1 MB | Under a minute | $0 | `SEC_USER_AGENT` | Yes |
| EDGAR full backfill, later in M1 | About 3-8k GETs | 100-250 MB gzipped | 15-30 min | $0 | `SEC_USER_AGENT`; ticker-to-CIK map | Yes |
| Board H.15 XML zip ([H.15][h15]) | 1 | 4,288,427 B | Seconds | $0 | Nothing | Yes |
| NY Fed EFFR ([OpenAPI][nyfed-api]) | A few range queries | Not measured, small | Seconds | $0 | Notice on outputs | Yes |
| Treasury par yields ([data.gov][ust-datagov]) | Endpoint not identified | Not measured | Not measured | $0 | Identify the endpoint | Expected yes |
| FRED/ALFRED, four series ([observations][fred-obs]) | About 30 requests | Up to 36 MB JSON; 1-2 MB Parquet | About 30 s | $0 | `FRED_API_KEY` plus written permission (and Cboe's for VIX) | Yes, but blocked |
| Kraken OHLCVT Full r1 ([support][kr-ohlcvt]) | 5 parts | 9,546,553,626 B; peak disk about 21 GB (hourly + daily) or 52.7 GB (all) | 12.7 min at 100 Mbit/s | $0 | Manual download by the human | No: `--yes` |
| Kraken smaller sample: 2026Q3 zip ([support][kr-ohlcvt]) | 1 | 576,348,633 B | About 46 s at 100 Mbit/s | $0 | Manual download | Yes |
| Coinbase delisted-candle probe ([candles][cb-candles]) | A few requests | Under 1 MB | Seconds | $0 | No publication without consent | Yes |
| Massive day aggregates, full history ([day aggs][m-dayaggs]) | 5,737 | About 1-1.5 GB gzipped | Minutes if bandwidth-bound | Advanced $199/mo (personal) or Business $2,499/mo ([pricing][m-pricing]) | Plan, S3 keys, written ML-training permission | Yes, but blocked |
| Massive security master and corporate actions ([All Tickers][m-alltickers]) | About 10-15.5k (weekly master) plus tens (splits) and about 200 (dividends) | Not measured | Depends on the undocumented reference bucket | Full reference history from Starter $29/mo | Plan, REST key, permission | Yes, but blocked |
| market-1t one-day rebuild, 2020-08-03 ([Wayback][m-wayback-2020-08]) | 2 flat files | 4.19 GB (researcher's estimate: 6-10 GB); about 6.4 GB on disk | About 5.6 min at 100 Mbit/s plus processing | Advanced $199/mo or Business $2,499/mo | Plan with quote files, S3 keys, written permission | No: `--yes`, and blocked |
| Binance Vision | None until cleared | | | | Counsel sign-off | |

## Open questions

1. Is the project personal, academic or organisational/commercial? This decides whether a Massive individual plan is usable at all and whether Binance's non-commercial licence fits.
2. Will Massive sign an Order Form covering training, fine-tuning and evaluation, publication of derived results, keeping weights after the subscription and use by the whole team, with SIP and exchange terms satisfied? Do model weights count as Information?
3. What are the terms behind `derived-market-data`, and does Massive's §5(g) apply to Market-1T? Will fin-ai-lab publish the universe builder and explain the REITs, the 190-name month and the dropped half-days?
4. Will the St. Louis Fed grant written, Bank-executed permission for FRED/ALFRED with local caching and published statistics, or do we stay with primary sources? Will Cboe license VIX history, and at what cost?
5. Will Kraken confirm scripted downloads and published aggregates, and does anyone on the team live in Maine or New York? Will Coinbase consent to publication? May a US person use Binance Vision at all?
6. What is the Treasury par-yield download endpoint, and does it keep revisions?
7. First Market-1T bytes: the quote-size unit; a 07:00 or 04:00 ET start; auction prints after 16:00:00; unadjusted prices across the 2020-08-31 AAPL and TSLA splits.
8. First Massive files: is the shares regeneration of quote files complete; what is `window_start`, and does the 2019-08-12 defect persist; are OTC names in the day files; were historical aggregates rewritten for decimal volume?
9. Massive reference data: coverage of splits, dividends and FIGIs for names delisted in 2003-2018; Ticker Events by FIGI when no current holder exists; whether `cik` is as of the queried date; reference rate limits on paid plans.
10. Does Polars 1.6.0 reproduce market-1t's partitions on the DGX Spark and on Apple silicon?
11. If FRED is permitted: how the 2,000-vintage cap counts a window, how often these series are revised, and whether VIXCLS backdating has held since 2010.
12. Calendars: times of the "immediate release" actions; the 2012 statement minutes; primary support for 2:15 in 2005-2010; which Board actions count as events; 08:00 or 08:30 for 2024-05-15; the timing of the 2026 lapse.
13. EDGAR: does `submissions.zip` contain the page files; how were after-5:30 filings handled before 2003; which time zone does FSDS `accepted` use; are pre-2004 8-K items populated for all filers?
14. NYSE: announcement times of the ad hoc closures (2007-01-02, 2012-10-29/30, 2018-12-05, 2025-01-09); any ad hoc closure in 2026 H1; an official confirmation that 2025-12-26 was a full session; XNYS under pandas 3.1.
15. Crypto: Coinbase candles for delisted products; Kraken's completeness for 2019-2022 delistings; whether Kraken daily bars align to UTC and equal their 24 hourly bars; the unidentified tickers FIDD, SOFID, USDUC, USDSM, APXUSD, U and XU3O8; and the evaluation window (from about 2021 with 50 coins, a smaller N earlier, or Binance if cleared).
16. Event scope and window rules (Board actions as events or as confounder flags; FOMC day split or t+1), and Market-1T's role beyond adapter validation.

## Tooling notes relevant to sources

- **mosaicml-streaming: keep it out of the harness.** 0.13.0 (2025-07-15), the latest release, hard-depends on torch, torchvision, transformers<5, numpy<2.2.0 (since 0.11.0), cloud SDKs and python-zstd, and its `hf` extra pins huggingface_hub<0.34 ([PyPI][pypi-streaming]). python-zstd 1.5.7.2 has no cp312 manylinux aarch64 wheel, so it builds from source on the DGX Spark; 1.5.7.3, which tfwm pins, is yanked as not thread-safe ([zstd][pypi-zstd], [1.5.7.3][pypi-zstd-1573]). uv resolves all extras and groups into one lock and `tool.uv.conflicts` cannot exempt base dependencies, so adding it anywhere would bind the whole harness to its pins (or break `uv lock` if the base needs numpy ≥2.2); only a separate, non-workspace project isolates it ([uv][uv-resolution]). Without a remote it also keeps zipped and raw shards, about 11.19 GB for the 2020-03 slice ([stream.py][mds-stream]).
- **Use an in-house MDS reader** with numpy and zstandard 0.25.0 (cp312 wheels for macOS arm64 and manylinux2014 aarch64) ([zstandard][pypi-zstandard]). After zstd decompression a shard is: uint32 sample count; uint32 absolute offsets (count + 1); the JSON shard config; the samples. Each sample holds one uint32 length per variable-size column, in sorted column order, then the payloads: `str` is UTF-8, `int32` is 4 bytes little-endian with no prefix, and `ndarray:<dtype>` is one byte `(ndim << 2) | code` (code 0-3 = u8-u64 for the shape), the shape, then C-order little-endian values ([encodings.py][mds-enc]). Slice each payload by its length before `frombuffer`, pass `max_output_size`, and keep the Apache-2.0 attribution if code is ported. Not yet tested on real bytes.
- **huggingface_hub 2.4.0 with hf-xet 1.8.0** (abi3 wheels for manylinux_2_28 aarch64 and macOS arm64) waits out 429s automatically; `hf_transfer` is not needed ([huggingface_hub][pypi-hfhub], [hf-xet][pypi-hfxet]).
- **exchange_calendars 4.13.2 for XNYS** (Apache-2.0, pure Python) ([PyPI][xcal-pypi]) encodes 09:30-16:00 America/New_York, 13:00 early closes, the ad hoc closures of 2001-09-11..14, 2004-06-11, 2007-01-02, 2012-10-29/30, 2018-12-05 and 2025-01-09, and NYSE's published 2026-2028 dates ([XNYS][xcal-xnys], [NYSE][nyse-hours]). Caveats:
  - Its default window, computed at import, runs from today minus 20 years to today plus 1 year, so today it silently starts on 2006-11-13 and its output depends on the wall clock ([source][xcal-default]). Always pass bounds, e.g. `get_calendar("XNYS", start="2004-01-02", end="2027-12-31")`, and persist the session table with a content hash and library version.
  - pandas 3.1.0 breaks some of its calendars (issue #632; the fix, PR #633, is unreleased). XNYS is probably unaffected (inference), but pin pandas below 3.1 until the fix ships ([issue][xcal-632]); pandas 3.1 also makes `Index.values` read-only and drops `freq` from datetime arrays ([pandas 3.1][pandas-31]).
  - Golden tests: closed on 2007-01-02, 2012-10-29, 2012-10-30, 2018-12-05, 2025-01-09, 2022-06-20, 2026-04-03 and 2026-06-19; 13:00 closes on 2013-07-03, 2019-07-03, 2025-11-28 and 2025-12-24; 2025-12-26 a full session (secondary sources only).
  - Session labels are naive dates while opens and closes are UTC, so take closes from the calendar, never a hard-coded 21:00 UTC. pandas_market_calendars 5.6.0 (MIT) depends on exchange_calendars and adds intraday irregularities that XNYS lacks (a 15:56 close on 2005-06-01, a 09:32 open on 2006-12-27); use it only as a test-time cross-check ([pandas_market_calendars][pmc-nyse]).
- **Separate calendars and environments**: XNYS for sessions, observed H.15 releases for Board days, EDGAR's `filingDate` for EDGAR days, and never tfwm's holiday CSVs. Run market-1t in its own locked environment (Python <3.13, polars<1.26, numpy<2) ([pyproject][m1t-pyproject]).
- **S3 client**: s3fs pulls aiobotocore 3.10.0, which pins botocore to 1.43.115-117 and holds boto3 back ([aiobotocore][aiobotocore]); use boto3 directly or obstore 0.12.1 (aarch64 and arm64 wheels) for Massive flat files ([obstore][obstore]).
- **Time zones**: `zoneinfo` reads the OS database first, so record tz versions in run manifests ([zoneinfo][zoneinfo]); in DuckDB set `TimeZone = 'UTC'` and `Calendar = 'gregorian'` on every connection, because both default to the locale ([DuckDB][duckdb-config]).

[aiobotocore]: https://pypi.org/pypi/aiobotocore/3.10.0/json
[alfred-deck]: https://alfred.stlouisfed.org/docs/alfred_capturing_data.pdf
[alfred-dff]: https://alfred.stlouisfed.org/series/downloaddata?seid=DFF
[alfred-dgs10]: https://alfred.stlouisfed.org/series/downloaddata?seid=DGS10
[alfred-help]: https://alfred.stlouisfed.org/help/downloaddata
[alfred-vix]: https://alfred.stlouisfed.org/series/downloaddata?seid=VIXCLS
[arxiv-abs]: https://arxiv.org/abs/2610.09048
[arxiv-v2]: https://arxiv.org/html/2610.09048v2
[bls-2013]: https://www.bls.gov/bls/updated_release_schedule.htm
[bls-2025]: https://www.bls.gov/bls/2025-lapse-revised-release-dates.htm
[bls-cpi-20251024]: https://www.bls.gov/news.release/archives/cpi_10242025.htm
[bls-cpi-archive]: https://www.bls.gov/bls/news-release/cpi.htm
[bls-early]: https://www.bls.gov/bls/early-data-release-05152024.htm
[bls-empsit-archive]: https://www.bls.gov/bls/news-release/empsit.htm
[bls-feed]: https://www.bls.gov/feed/empsit.rss
[bls-ics]: https://www.bls.gov/schedule/news_release/bls.ics
[bls-link]: https://www.bls.gov/bls/linksite.htm
[bls-notice]: https://www.bls.gov/bls/092025-cpi-reschedule-notice.htm
[bls-pss]: https://www.bls.gov/bls/pss.htm
[bls-robots]: https://www.bls.gov/robots.txt
[bls-sched-arch]: https://www.bls.gov/bls/archived_sched.htm
[bn-issue475]: https://github.com/binance/binance-public-data/issues/475
[bn-ping]: https://api.binance.com/api/v3/ping
[bn-prohibited]: https://www.binance.com/en/legal/list-of-prohibited-countries
[bn-readme]: https://github.com/binance/binance-public-data/blob/master/README.md
[bn-s3-btc1h]: https://s3-ap-northeast-1.amazonaws.com/data.binance.vision?delimiter=/&prefix=data/spot/monthly/klines/BTCUSDT/1h/
[bn-s3-btc1mo]: https://s3-ap-northeast-1.amazonaws.com/data.binance.vision?delimiter=/&prefix=data/spot/monthly/klines/BTCUSDT/1mo/
[bn-terms]: https://github.com/binance/binance-public-data/blob/master/TERMS_AND_CONDITIONS.md
[cb-candles]: https://docs.cdp.coinbase.com/api-reference/exchange-api/rest-api/products/get-product-candles.md
[cb-products]: https://api.exchange.coinbase.com/products
[cb-rate]: https://docs.cdp.coinbase.com/exchange/rest-api/rate-limits
[cb-terms]: https://web.archive.org/web/20260710181643/https://www.coinbase.com/legal/market_data?japan_bespoke_content=false&logged_in=false&country=US&currency=USD&mobile=false
[cb-welcome]: https://docs.cdp.coinbase.com/exchange/introduction/welcome.md
[cboe-method]: https://cdn.cboe.com/api/global/us_indices/governance/Volatility_Index_Methodology_Cboe_Volatility_Index.pdf
[cboe-terms]: https://www.cboe.com/terms
[cboe-use]: https://www.cboe.com/use-of-content
[coinmetrics]: https://docs.coinmetrics.io/packages/coin-metrics-community-data
[datagov-fsds]: https://catalog.data.gov/dataset/financial-statement-data-sets
[ddp-faq]: https://www.federalreserve.gov/data/ddp-retirement-frequently-asked-questions.htm
[dgx]: https://www.nvidia.com/en-us/products/workstations/dgx-spark/
[duckdb-config]: https://duckdb.org/docs/2.0/configuration/overview.html
[ecfr-232-13]: https://www.ecfr.gov/current/title-17/chapter-II/part-232/subpart-A/section-232.13
[econgraph]: https://github.com/EconGraph/econ-graph/pull/490
[fed-20070618]: https://www.federalreserve.gov/newsevents/pressreleases/monetary20070618a.htm
[fed-20081120]: https://www.federalreserve.gov/newsevents/pressreleases/monetary20081120a.htm
[fed-20110324]: https://www.federalreserve.gov/newsevents/pressreleases/monetary20110324a.htm
[fed-20120516b]: https://www.federalreserve.gov/newsevents/pressreleases/monetary20120516b.htm
[fed-20130313]: https://www.federalreserve.gov/newsevents/pressreleases/monetary20130313a.htm
[fed-20160127]: https://www.federalreserve.gov/newsevents/pressreleases/monetary20160127a.htm
[fed-20200315]: https://www.federalreserve.gov/newsevents/pressreleases/monetary20200315a.htm
[fed-20200409]: https://www.federalreserve.gov/newsevents/pressreleases/monetary20200409a.htm
[fed-20230312]: https://www.federalreserve.gov/newsevents/pressreleases/monetary20230312a.htm
[fed-20261112]: https://www.federalreserve.gov/newsevents/pressreleases/monetary20261112a.htm
[fed-policies]: https://www.federalreserve.gov/website-linking-policies.htm
[fed-presconf-2012]: https://www.federalreserve.gov/monetarypolicy/fomcpresconf20120913.htm
[fed-press-2026]: https://www.federalreserve.gov/newsevents/pressreleases/2026-press-fomc.htm
[fed-rss]: https://www.federalreserve.gov/feeds/press_monetary.xml
[fed-transcript-0121]: https://www.federalreserve.gov/monetarypolicy/files/FOMC20080121confcall.pdf
[fomc-cal]: https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm
[fomc-hist-2017]: https://www.federalreserve.gov/monetarypolicy/fomchistorical2017.htm
[fomc-hist-idx]: https://www.federalreserve.gov/monetarypolicy/fomc_historical_year.htm
[form8k]: https://www.sec.gov/files/form8-k.pdf
[fr-612]: https://www.govinfo.gov/content/pkg/FR-2025-11-17/html/2025-19926.htm
[fr-mdi]: https://www.govinfo.gov/content/pkg/FR-2024-10-08/html/2024-21867.htm
[frb-disclaimer]: https://www.federalreserve.gov/disclaimer.htm
[frbsf-policies]: https://www.frbsf.org/site-policies/
[fred-apiterms]: https://fred.stlouisfed.org/docs/api/terms_of_use.html
[fred-cal-101]: https://fred.stlouisfed.org/releases/calendar?rid=101&y=2026
[fred-cal-200]: https://fred.stlouisfed.org/releases/calendar?rid=200&y=2026&vs=2026-01-01&ve=2026-12-31&pageID=5
[fred-dff]: https://fred.stlouisfed.org/series/DFF
[fred-dgs10]: https://fred.stlouisfed.org/series/DGS10
[fred-errors]: https://fred.stlouisfed.org/docs/api/fred/errors.html
[fred-key]: https://fred.stlouisfed.org/docs/api/api_key.html
[fred-legal]: https://fred.stlouisfed.org/legal/
[fred-legal-2024]: https://web.archive.org/web/20240507170418/https://fred.stlouisfed.org/legal/
[fred-obs]: https://fred.stlouisfed.org/docs/api/fred/series_observations.html
[fred-realtime]: https://fred.stlouisfed.org/docs/api/fred/realtime_period.html
[fred-v2]: https://fred.stlouisfed.org/docs/api/fred/v2/release_observations.html
[fred-vintagedates]: https://fred.stlouisfed.org/docs/api/fred/series_vintagedates.html
[fred-vix]: https://fred.stlouisfed.org/series/VIXCLS
[fredapi-52]: https://github.com/mortada/fredapi/pull/52
[h15]: https://www.federalreserve.gov/releases/h15/
[hf-036-xet]: https://github.com/huggingface/huggingface_hub/blob/v0.36.0/src/huggingface_hub/utils/_xet.py
[hf-2003-index]: https://huggingface.co/datasets/fin-ai-lab/Market-1T-1Hz-2019H2-2020-sparse/resolve/5797a9f890e133c491265bb8889cd64f27ceb50e/1Hz_mosaic_mnth_sparse/2020/03/index.json
[hf-daystore-202001]: https://huggingface.co/datasets/fin-ai-lab/Market-1T-1Hz-2019H2-2020-daystore/resolve/b8f7520b1d89bdd1e971ec87f64e687f26e0d813/1Hz_daystore/2020/01/index.json
[hf-daystore-tree]: https://huggingface.co/api/datasets/fin-ai-lab/Market-1T-1Hz-2019H2-2020-daystore/tree/b8f7520b1d89bdd1e971ec87f64e687f26e0d813?recursive=true
[hf-env]: https://huggingface.co/docs/huggingface_hub/package_reference/environment_variables
[hf-filedl]: https://github.com/huggingface/huggingface_hub/blob/v2.4.0/src/huggingface_hub/file_download.py
[hf-meta-20201231]: https://huggingface.co/datasets/fin-ai-lab/Market-1T-1Hz-2019H2-2020-daystore/resolve/b8f7520b1d89bdd1e971ec87f64e687f26e0d813/1Hz_daystore/2020/12/2020-12-31/meta.json
[hf-rate]: https://huggingface.co/docs/hub/rate-limits
[hf-snapshot]: https://github.com/huggingface/huggingface_hub/blob/v2.4.0/src/huggingface_hub/_snapshot_download.py
[hf-sparse-api]: https://huggingface.co/api/datasets/fin-ai-lab/Market-1T-1Hz-2019H2-2020-sparse
[hf-sparse-card]: https://huggingface.co/datasets/fin-ai-lab/Market-1T-1Hz-2019H2-2020-sparse/resolve/5797a9f890e133c491265bb8889cd64f27ceb50e/README.md
[hf-sparse-commits]: https://huggingface.co/api/datasets/fin-ai-lab/Market-1T-1Hz-2019H2-2020-sparse/commits/main
[hf-sparse-tree]: https://huggingface.co/api/datasets/fin-ai-lab/Market-1T-1Hz-2019H2-2020-sparse/tree/5797a9f890e133c491265bb8889cd64f27ceb50e?recursive=true
[hf-xet]: https://huggingface.co/docs/hub/xet/index
[ia-blog]: https://blog.archive.org/2026/09/15/an-update-on-wayback-machine-access/
[iana]: https://www.iana.org/time-zones
[k8]: https://www.federalreserve.gov/aboutthefed/k8.htm
[kaiko-zerofee]: https://research.kaiko.com/insights/the-impact-of-binances-zero-fee-volume
[kr-2025q4]: https://assets.kraken.com/marketing/institutions/Kraken_OHLCVT_2025Q4.zip
[kr-assetpairs]: https://api.kraken.com/0/public/AssetPairs
[kr-bsv]: https://support.kraken.com/hc/en-us/articles/360029029592-Delisting-of-Bitcoin-SV-BSV-April-2019
[kr-geo]: https://support.kraken.com/articles/360001368823-Geographic-Restrictions-Can-I-use-Kraken-if-I-m-from-
[kr-ohlc]: https://docs.kraken.com/api/docs/rest-api/get-ohlc-data
[kr-ohlcvt]: https://support.kraken.com/hc/en-us/articles/360047124832-Downloadable-historical-OHLCVT-Open-High-Low-Close-Volume-Trades-data
[kr-part04]: https://assets.kraken.com/marketing/institutions/Kraken_OHLCVT_Full.zip.part04
[kr-rate]: https://support.kraken.com/articles/206548367-what-are-the-api-rate-limits-
[kr-sums]: https://assets.kraken.com/marketing/institutions/OHLCVT_Full_PARTS_SHA256SUMS.txt
[kr-terms]: https://www.kraken.com/legal/global-terms
[kr-wayback-cdx]: https://web.archive.org/cdx/search/cdx?url=api.kraken.com/0/public/AssetPairs&output=json
[luna-fm]: https://www.financemagnates.com/cryptocurrency/news/terras-ambitious-luna-20-plunges-70-in-24-hours/
[m-aggbars]: https://massive.com/knowledge-base/article/how-does-massive-create-aggregate-bars
[m-alltickers]: https://massive.com/docs/rest/stocks/tickers/all-tickers.md
[m-biz]: https://massive.com/legal/businesses-terms-of-service
[m-business]: https://massive.com/business-stocks
[m-changelog]: https://massive.com/changelog
[m-crypto-day]: https://massive.com/docs/flat-files/crypto/day-aggregates.md
[m-dashes]: https://massive.com/knowledge-base/article/why-are-ticker-symbols-with-dashes-not-showing-in-massives-system
[m-dayaggs]: https://massive.com/docs/flat-files/stocks/day-aggregates.md
[m-dividends]: https://massive.com/docs/rest/stocks/corporate-actions/dividends.md
[m-events]: https://massive.com/docs/rest/stocks/corporate-actions/ticker-events.md
[m-formt]: https://massive.com/knowledge-base/article/does-a-form-t-trade-update-a-pre-market-minute-bars-high-low-open-and-close
[m-history]: https://massive.com/knowledge-base/article/how-much-historical-stock-data-does-massive-have
[m-holidays]: https://massive.com/docs/rest/stocks/market-operations/market-holidays.md
[m-indiv]: https://massive.com/legal/individuals-terms-of-service
[m-mdt]: https://massive.com/legal/market-data-terms-of-service
[m-mdt-2025]: https://web.archive.org/web/20251117140522/https://massive.com/legal/market-data-terms-of-service
[m-missing]: https://massive.com/knowledge-base/article/why-are-there-missing-aggregates-in-massives-data
[m-overview]: https://massive.com/docs/flat-files/stocks/overview.md
[m-overview-ticker]: https://massive.com/docs/rest/stocks/tickers/ticker-overview.md
[m-pricing]: https://massive.com/pricing
[m-pypi-291]: https://pypi.org/pypi/massive/2.9.1/json
[m-quickstart]: https://massive.com/docs/flat-files/quickstart.md
[m-quotes]: https://massive.com/docs/flat-files/stocks/quotes.md
[m-quotes-root]: https://massive.com/docs/flat-files/stocks/quotes
[m-ratelimit]: https://massive.com/knowledge-base/article/what-is-the-request-limit-for-massives-restful-apis
[m-ready]: https://massive.com/knowledge-base/article/what-time-are-massives-flat-files-ready-each-day
[m-rebrand]: https://massive.com/blog/polygon-is-now-massive
[m-redistrib]: https://massive.com/knowledge-base/article/how-can-i-redistribute-massives-market-data
[m-rest-qs]: https://massive.com/docs/rest/quickstart.md
[m-restvsfile]: https://massive.com/knowledge-base/article/why-doesnt-a-bar-from-the-rest-api-match-the-flat-files
[m-roundlots]: https://massive.com/blog/change-stocks-quotes-round-lots-to-shares
[m-s3kb]: https://massive.com/knowledge-base/article/how-to-get-started-with-s3
[m-splits]: https://massive.com/docs/rest/stocks/corporate-actions/splits.md
[m-splits-kb]: https://massive.com/knowledge-base/article/does-massive-support-normal-and-reverse-splits
[m-thirdparty-log]: https://github.com/nishpa800/Share-with-Claude-Desktop/blob/main/recon/historical-download-status.md
[m-tickerchanges]: https://massive.com/knowledge-base/article/how-does-massive-handle-ticker-changes-and-acquisitions
[m-trades]: https://massive.com/docs/flat-files/stocks/trades
[m-trades-md]: https://massive.com/docs/flat-files/stocks/trades.md
[m-wayback-2020-08]: https://web.archive.org/web/20260123174336/https://massive.com/docs/flat-files/stocks/quotes/2020/08
[m-wayback-2025-11]: https://web.archive.org/web/20260117063124/https://massive.com/docs/flat-files/stocks/quotes/2025/11
[m1t-ci]: https://github.com/fin-ai-lab/market-1t/blob/38da67c065c12e0373a5d56a52a2685d6eccf660/.github/workflows/ci.yml
[m1t-conditions]: https://github.com/fin-ai-lab/market-1t/blob/main/src/market_1t/trade_conditions.json
[m1t-download]: https://github.com/fin-ai-lab/market-1t/blob/38da67c065c12e0373a5d56a52a2685d6eccf660/src/market_1t/download.py
[m1t-jobs]: https://github.com/fin-ai-lab/market-1t/blob/38da67c065c12e0373a5d56a52a2685d6eccf660/src/market_1t/jobs.py#L98-L120
[m1t-methodology]: https://github.com/fin-ai-lab/market-1t/blob/38da67c065c12e0373a5d56a52a2685d6eccf660/docs/methodology.md
[m1t-pyproject]: https://github.com/fin-ai-lab/market-1t/blob/38da67c065c12e0373a5d56a52a2685d6eccf660/pyproject.toml
[m1t-readme]: https://github.com/fin-ai-lab/market-1t/blob/38da67c065c12e0373a5d56a52a2685d6eccf660/README.md
[m1t-snapshot]: https://github.com/fin-ai-lab/market-1t/blob/38da67c065c12e0373a5d56a52a2685d6eccf660/src/market_1t/snapshot.py#L342-L344
[mds-enc]: https://github.com/mosaicml/streaming/blob/v0.13.0/streaming/base/format/mds/encodings.py
[mds-stream]: https://github.com/mosaicml/streaming/blob/v0.13.0/streaming/base/stream.py
[nyfed-api]: https://markets.newyorkfed.org/static/docs/markets-api.yml
[nyfed-rates]: https://www.newyorkfed.org/markets/reference-rates/additional-information-about-reference-rates
[nyfed-terms]: https://www.newyorkfed.org/privacy/termsofuse
[nyse-dec2025-news]: https://news.bgov.com/capital-markets/nyse-says-stock-market-hours-unchanged-on-dec-24-and-dec-26
[nyse-hours]: https://www.nyse.com/trade/hours-calendars
[obstore]: https://pypi.org/pypi/obstore/0.12.1/json
[openfigi]: https://www.openfigi.com/about/figi
[pandas-31]: https://pandas.pydata.org/docs/whatsnew/v3.1.0.html
[pmc-nyse]: https://github.com/rsheftel/pandas_market_calendars/blob/v5.6.0/pandas_market_calendars/holidays/nyse.py
[polars-hash]: https://github.com/pola-rs/polars/blob/py-1.6.0/crates/polars-core/src/hashing/vector_hasher.rs
[pypi-hfhub]: https://pypi.org/project/huggingface-hub/2.4.0/
[pypi-hfxet]: https://pypi.org/pypi/hf-xet/1.8.0/json
[pypi-streaming]: https://pypi.org/project/mosaicml-streaming/0.13.0/
[pypi-zstandard]: https://pypi.org/pypi/zstandard/0.25.0/json
[pypi-zstd]: https://pypi.org/project/zstd/
[pypi-zstd-1573]: https://pypi.org/project/zstd/1.5.7.3/
[rel-8176]: https://www.sec.gov/rule-release/33-8176
[rel-8400]: https://www.sec.gov/rule-release/33-8400
[sec-10s]: https://dart.deloitte.com/USDART/home/publications/deloitte/heads-up/2026/sec-proposes-semi-annual-reporting
[sec-2003-41]: https://www.sec.gov/newsroom/press-releases/2003-41-sec-provides-guidance-filers-reporting-pension-fund-blackout-periods-non-gaap-financial-data
[sec-aapl]: https://data.sec.gov/submissions/CIK0000320193.json
[sec-aapl-001]: https://data.sec.gov/submissions/CIK0000320193-submissions-001.json
[sec-access]: https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data
[sec-api]: https://www.sec.gov/search-filings/edgar-application-programming-interfaces
[sec-bulk]: https://www.sec.gov/Archives/edgar/daily-index/bulkdata/submissions.zip
[sec-cal]: https://www.sec.gov/submit-filings/filer-support-resources/edgar-calendar
[sec-closed-dec2025]: https://www.sec.gov/newsroom/whats-new/edgar-will-be-closed-december-24-2025-through-december-26-2025
[sec-closed-jan2025]: https://www.sec.gov/newsroom/whats-new/edgar-closed-january-9-2025
[sec-digest-2003]: https://webarchive.library.unt.edu/web/20090507192504id_/http://www.sec.gov/news/digest/dig072403.txt
[sec-faq]: https://www.sec.gov/about/webmaster-frequently-asked-questions
[sec-fast]: https://www.sec.gov/resources-small-businesses/small-business-compliance-guides/fast-act-modernization-simplification-regulation-s-k
[sec-fsds]: https://www.sec.gov/dera/data/financial-statement-data-sets.html
[sec-fsds-pdf]: https://www.sec.gov/files/financial-statement-data-sets.pdf
[sec-hdr-25]: https://www.sec.gov/Archives/edgar/data/320193/000114036125025275/0001140361-25-025275.hdr.sgml
[sec-hdr-aapl-20]: https://www.sec.gov/Archives/edgar/data/320193/000032019320000060/0000320193-20-000060.hdr.sgml
[sec-hdr-aapl-26]: https://www.sec.gov/Archives/edgar/data/320193/000032019326000018/0000320193-26-000018.hdr.sgml
[sec-idx-1994]: https://www.sec.gov/Archives/edgar/data/320193/000091898394000004/0000918983-94-000004-index.htm
[sec-idx-2003]: https://www.sec.gov/Archives/edgar/data/320193/000110465903004649/0001104659-03-004649-index.htm
[sec-jpm]: https://data.sec.gov/submissions/CIK0000019617.json
[sec-masteridx]: https://www.sec.gov/Archives/edgar/full-index/2024/QTR1/master.idx
[sec-phasein]: https://www.sec.gov/files/rules/final/33-7427.txt
[sec-privacy]: https://www.sec.gov/about/privacy-information
[sec-status]: https://www.sec.gov/submit-filings/filer-support-resources/how-do-i-guides/determine-status-my-filing
[sec-tickers]: https://www.sec.gov/files/company_tickers.json
[sec-xom-old]: https://data.sec.gov/submissions/CIK0000034088.json
[sf-anchors]: https://github.com/galilai-group/stable-finance/blob/a3dd98e1caeab454ba4bd0ce1645ffee9a3237e6/src/stable_finance/dataset/anchors.py
[sf-densify]: https://github.com/galilai-group/stable-finance/blob/a3dd98e1caeab454ba4bd0ce1645ffee9a3237e6/src/stable_finance/dataset/densify.py
[sf-ingest]: https://github.com/galilai-group/stable-finance/blob/main/src/stable_finance/dataset/datasets/market1t/ingest.py
[sf-repo]: https://github.com/galilai-group/stable-finance/tree/a3dd98e1caeab454ba4bd0ce1645ffee9a3237e6
[sf-schema]: https://github.com/galilai-group/stable-finance/blob/a3dd98e1caeab454ba4bd0ce1645ffee9a3237e6/src/stable_finance/dataset/schema.py
[sf-spec]: https://github.com/galilai-group/stable-finance/blob/main/src/stable_finance/dataset/datasets/market1t/spec.py
[sf-transforms]: https://github.com/galilai-group/stable-finance/blob/a3dd98e1caeab454ba4bd0ce1645ffee9a3237e6/src/stable_finance/dataset/transforms.py#L89-L113
[sf-writemds]: https://github.com/galilai-group/stable-finance/blob/a3dd98e1caeab454ba4bd0ce1645ffee9a3237e6/src/stable_finance/dataset/write_mds.py
[sifma-gf]: https://www.sifma.org/news/press-releases/sifma-fixed-income-market-close-recommendations-in-the-u-s-the-u-k-and-japan-for-good-friday-easter-monday-holidays-2026
[tfwm-dl]: https://github.com/fin-ai-lab/tfwm/blob/main/market_jepa/market1t.py
[tfwm-holidays]: https://github.com/fin-ai-lab/tfwm/blob/e739329a630c14cdb1ed2834a2461bfbfe17e8b5/data/market_holidays.csv
[tfwm-readme]: https://github.com/fin-ai-lab/tfwm/blob/e739329a630c14cdb1ed2834a2461bfbfe17e8b5/README.md
[usmpd]: https://www.frbsf.org/research-and-insights/data-and-indicators/us-monetary-policy-event-study-database/
[ust-datagov]: https://catalog.data.gov/dataset/interest-rate-statistics-daily-treasury-yield-curve-rates
[ust-infosheet]: https://home.treasury.gov/policy-issues/financing-the-government/yield-curve-methodology-change-information-sheet
[ust-method]: https://home.treasury.gov/policy-issues/financing-the-government/interest-rate-statistics/treasury-yield-curve-methodology
[uv-resolution]: https://github.com/astral-sh/uv/blob/0.13.8/docs/concepts/resolution.md
[wayback-client]: https://wayback.readthedocs.io/en/latest/release-history.html
[xcal-632]: https://github.com/gerrymanoim/exchange_calendars/issues/632
[xcal-default]: https://github.com/gerrymanoim/exchange_calendars/blob/4.13.2/exchange_calendars/exchange_calendar.py
[xcal-pypi]: https://pypi.org/pypi/exchange-calendars/4.13.2/json
[xcal-xnys]: https://github.com/gerrymanoim/exchange_calendars/blob/4.13.2/exchange_calendars/exchange_calendar_xnys.py
[zipline-fix]: https://github.com/fovi-llc/zipline-polygon-bundle/blob/main/fix_2019-08-12.sh
[zoneinfo]: https://docs.python.org/3.12/library/zoneinfo.html
