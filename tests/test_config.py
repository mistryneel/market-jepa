from __future__ import annotations

import shutil
from datetime import date
from pathlib import Path

import pytest

from mjepa_harness.config import (
    ConfigError,
    EndpointConfig,
    fingerprint,
    load_config,
    load_harness_config,
)


@pytest.fixture
def config_copy(config_dir: Path, tmp_path: Path) -> Path:
    target = tmp_path / "configs"
    shutil.copytree(config_dir, target)
    return target


def _replace(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    assert old in text, f"{old!r} not found in {path.name}"
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def test_repo_configs_load_and_are_consistent(config_dir: Path) -> None:
    cfg = load_harness_config(config_dir)
    assert set(cfg.fingerprints()) == {"sources", "universe", "splits", "events", "endpoint"}
    assert all(v.startswith("sha256:") for v in cfg.fingerprints().values())


def test_endpoint_encodes_the_brief(config_dir: Path) -> None:
    ep = load_harness_config(config_dir).endpoint
    assert ep.metric.name == "inverse_stein"
    assert ep.metric.loss == "tr(H^-1 S) + logdet(H)"
    assert ep.target.name == "realized_covariance"
    assert (ep.horizon.unit, ep.horizon.first, ep.horizon.last) == ("trading_day", 1, 5)
    assert ep.universe.top_n == 500
    assert ep.universe.ranking == "prior_month_dollar_volume"
    assert ep.universe.min_price_usd == 5.0
    assert ep.universe.rebuild == "monthly"
    assert set(ep.events.types) == {"FOMC", "CPI"}
    assert ep.events.scheduled_only is True
    assert (ep.period.start, ep.period.end) == (date(2022, 1, 1), date(2026, 6, 30))
    assert ep.aggregation == "mean_over_events"
    assert ep.decision_rule.pairing == "by_event"
    assert ep.decision_rule.bootstrap.block_unit == "calendar_month"
    assert ep.decision_rule.multiplicity == "holm_over_baseline_comparisons"
    assert ep.universe.price_rule is not None
    assert "strictly_above" in ep.universe.price_rule  # "price above $5"
    assert ep.status == "draft"


def test_splits_encode_the_brief(config_dir: Path) -> None:
    splits = load_harness_config(config_dir).splits
    periods = splits.periods
    assert periods.train.start is not None  # explicit, not "whatever data is on disk"
    assert periods.train.end == date(2018, 12, 31)
    assert (periods.tune.start, periods.tune.end) == (date(2019, 1, 1), date(2021, 12, 31))
    locked = periods.locked_test
    assert (locked.start, locked.end) == (date(2022, 1, 1), date(2026, 6, 30))
    horizon = splits.label_horizon_trading_days
    assert horizon == splits.purge_trading_days == splits.embargo_trading_days == 5


def test_unknown_key_is_rejected(config_copy: Path) -> None:
    _replace(config_copy / "universe.yaml", "top_n: 500", "top_n: 500\ntop_nn: 600")
    with pytest.raises(ConfigError, match="top_nn"):
        load_harness_config(config_copy)


def test_duplicate_key_is_rejected(config_copy: Path) -> None:
    _replace(config_copy / "universe.yaml", "top_n: 500", "top_n: 500\ntop_n: 400")
    with pytest.raises(ConfigError, match="duplicate key 'top_n'"):
        load_harness_config(config_copy)


@pytest.mark.parametrize(
    ("old", "new"),
    [
        ("top_n: 500", 'top_n: "500"'),  # no str -> int coercion
        ("min_price_usd: 5.0", 'min_price_usd: "5"'),  # no str -> float coercion
        ("rebuild: monthly", "rebuild: yes"),  # YAML 1.1 boolean trap
    ],
)
def test_types_are_not_coerced(config_copy: Path, old: str, new: str) -> None:
    _replace(config_copy / "universe.yaml", old, new)
    with pytest.raises(ConfigError):
        load_harness_config(config_copy)


def test_unsafe_yaml_tags_are_refused(config_copy: Path) -> None:
    (config_copy / "universe.yaml").write_text(
        '!!python/object/apply:os.system ["echo pwned"]\n', encoding="utf-8"
    )
    with pytest.raises(ConfigError, match="invalid YAML"):
        load_harness_config(config_copy)


def test_non_contiguous_periods_are_rejected(config_copy: Path) -> None:
    _replace(config_copy / "splits.yaml", "start: 2019-01-01", "start: 2019-01-02")
    with pytest.raises(ConfigError, match="tune must start the day after train ends"):
        load_harness_config(config_copy)


def test_purge_shorter_than_horizon_is_rejected(config_copy: Path) -> None:
    _replace(config_copy / "splits.yaml", "purge_trading_days: 5", "purge_trading_days: 4")
    with pytest.raises(ConfigError, match="must be >= the label horizon"):
        load_harness_config(config_copy)


def test_universe_mismatch_with_endpoint_is_detected(config_copy: Path) -> None:
    _replace(config_copy / "universe.yaml", "top_n: 500", "top_n: 400")
    with pytest.raises(ConfigError, match=r"endpoint\.universe differs"):
        load_harness_config(config_copy)


def test_locked_period_mismatch_with_endpoint_is_detected(config_copy: Path) -> None:
    _replace(config_copy / "splits.yaml", "end: 2026-06-30", "end: 2026-09-30")
    with pytest.raises(ConfigError, match=r"endpoint\.period differs"):
        load_harness_config(config_copy)


def test_fingerprint_ignores_comments_and_key_order(config_copy: Path) -> None:
    path = config_copy / "endpoint.yaml"
    before = fingerprint(load_config(path, EndpointConfig))
    text = path.read_text(encoding="utf-8")
    reordered = text.replace("version: 1\nstatus: draft", "status: draft  # moved\nversion: 1")
    assert reordered != text
    path.write_text("# a new comment\n" + reordered, encoding="utf-8")
    assert fingerprint(load_config(path, EndpointConfig)) == before


def test_fingerprint_changes_with_content(config_copy: Path) -> None:
    path = config_copy / "endpoint.yaml"
    before = fingerprint(load_config(path, EndpointConfig))
    _replace(path, "last: 5", "last: 4")
    assert fingerprint(load_config(path, EndpointConfig)) != before


@pytest.mark.parametrize(
    ("file", "old", "new", "message"),
    [
        ("splits.yaml", "end: 2021-12-31", "end: 2022-03-31", "locked_test must start"),
        ("splits.yaml", "embargo_trading_days: 5", "embargo_trading_days: 4", "label horizon"),
        (
            "splits.yaml",
            "label_horizon_trading_days: 5",
            "label_horizon_trading_days: 4",
            "shorter than the endpoint",
        ),
        ("splits.yaml", "start: 2005-01-01", "start: 2019-06-01", "after end"),
        ("endpoint.yaml", "types: [FOMC, CPI]", "types: [FOMC, CPI, PPI]", "literal_error"),
        ("endpoint.yaml", "start: 2022-01-01", "start: 2022-02-01", r"endpoint\.period differs"),
        ("endpoint.yaml", "first: 1", "first: 6", "horizon.first must be <= horizon.last"),
        ("events.yaml", "  CPI:\n", "  CPI_RENAMED:\n", "literal_error"),
        ("endpoint.yaml", "alpha: 0.05", "alpha: 1.5", "alpha"),
    ],
)
def test_each_validator_rejects_its_violation(
    config_copy: Path, file: str, old: str, new: str, message: str
) -> None:
    _replace(config_copy / file, old, new)
    with pytest.raises(ConfigError, match=message):
        load_harness_config(config_copy)


def test_endpoint_event_type_missing_from_events_yaml_is_rejected(config_copy: Path) -> None:
    events = config_copy / "events.yaml"
    text = events.read_text(encoding="utf-8")
    start = text.index("  CPI:\n")
    end = text.index("  EMPLOYMENT:\n")
    events.write_text(text[:start] + text[end:], encoding="utf-8")
    with pytest.raises(ConfigError, match=r"endpoint event types not defined in events\.yaml"):
        load_harness_config(config_copy)


def test_horizon_longer_than_the_label_horizon_is_rejected(config_copy: Path) -> None:
    _replace(config_copy / "endpoint.yaml", "last: 5", "last: 6")
    with pytest.raises(ConfigError, match="shorter than the endpoint's last label session"):
        load_harness_config(config_copy)


@pytest.mark.parametrize(
    "bad_yaml",
    [
        "top_n: 500\nexample_date: 2019-02-30\n",  # impossible date -> ValueError in PyYAML
        "? [a, b]\n: 1\n",  # unhashable (list) key -> TypeError
    ],
)
def test_malformed_values_are_config_errors(config_copy: Path, bad_yaml: str) -> None:
    (config_copy / "universe.yaml").write_text(bad_yaml, encoding="utf-8")
    with pytest.raises(ConfigError):
        load_harness_config(config_copy)


def test_missing_config_dir_is_a_clear_error(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="config directory not found"):
        load_harness_config(tmp_path / "nope")
