# data_ref: small committed reference tables

Only small reference tables may live here: each under 1 MB, with a provenance entry in
[`SOURCES.yaml`](SOURCES.yaml). Examples are the FOMC and BLS release calendars built in M1.
Everything else, raw or derived, lives under `$MJ_DATA_DIR` and never enters git.

`tests/test_repo_hygiene.py` enforces these rules on every test run:

- every `.csv`/`.tsv` file here has an entry in `SOURCES.yaml` with `path`, `description`,
  `source_urls` (https), `retrieved` (a date) and `licence`;
- no file in the repository is 1 MB or larger;
- data-like files (`.csv`, `.parquet`, archives, ...) appear only under `data_ref/`.
