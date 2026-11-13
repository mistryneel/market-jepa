"""Pre-registration lock for the primary endpoint.

If ``test_bundle_matches_the_literal_pin`` fails, you changed the endpoint bundle
(``configs/endpoint.yaml``, ``configs/splits.yaml`` or an event calendar it scores).
That is allowed only while ``status: draft`` and only together with:
1. an update of ``PREREGISTERED_BUNDLE_FINGERPRINT`` in
   ``src/mjepa_harness/preregistration.py``;
2. the same value in ``PINNED`` below;
3. a dated entry in ``docs/harness/DECISIONS.md`` that cites it.

All three go in the same commit. Once locked-test data has been read, the endpoint must
not change.
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import Any

import pytest
import yaml
from typer.testing import CliRunner

from mjepa_harness import preregistration
from mjepa_harness.cli import app
from mjepa_harness.config import ConfigError, load_harness_config
from mjepa_harness.preregistration import (
    PREREGISTERED_BUNDLE_FINGERPRINT,
    PreregistrationError,
    bundle_fingerprint,
    require_locked_preregistration,
    verify_preregistration,
)
from mjepa_harness.provenance import CodeVersion

# The literal pin, deliberately duplicated so the test does not trust the code under test.
PINNED = "sha256:00a5d1536f45dd0104cd8cf5c96bde5f61230f94422df4daa3fd1db33673e889"

# The sentence from the project brief (section 1), verbatim.
BRIEF_STATEMENT = (
    "Mean out-of-sample Stein loss of 5-trading-day covariance forecasts (trading days 1 to 5 "
    "after the event) for the top 500 US stocks by prior-month dollar volume (price above $5, "
    "universe rebuilt monthly). It is taken across every scheduled FOMC and CPI announcement "
    "in the locked test period, paired by event, and compared with a block bootstrap across "
    "months."
)
CLEAN = CodeVersion("0.1.0", "a" * 40, False)


@pytest.fixture
def repo_copy(repo_root: Path, tmp_path: Path) -> Path:
    """configs/ and data_ref/ copied into a scratch repo layout."""
    target = tmp_path / "repo"
    shutil.copytree(repo_root / "configs", target / "configs")
    shutil.copytree(repo_root / "data_ref", target / "data_ref")
    return target


def _write_calendars(repo: Path, fomc_time: str = "19:00:00Z") -> None:
    calendars = repo / "data_ref" / "calendars"
    calendars.mkdir(parents=True, exist_ok=True)
    (calendars / "fomc.csv").write_text(
        f"event_id,actual_release_utc\nfomc-2022-01-26,2022-01-26T{fomc_time}\n"
    )
    (calendars / "bls_cpi.csv").write_text(
        "event_id,actual_release_utc\ncpi-2022-01-12,2022-01-12T13:30:00Z\n"
    )


def _decide_everything_and_lock(repo: Path) -> None:
    """Fill every undecided field with an arbitrary valid choice and set status: locked."""
    configs = repo / "configs"
    endpoint: Any = yaml.safe_load((configs / "endpoint.yaml").read_text())
    universe: Any = yaml.safe_load((configs / "universe.yaml").read_text())
    decided_universe = {
        "share_class_rule": "all_classes",
        "exchanges": ["XNYS", "XNAS"],
        "min_sessions_in_prior_month": 15,
    }
    universe.update(decided_universe)
    endpoint["universe"].update(decided_universe)
    endpoint["definitions"].update(
        {
            "refit_policy": "frozen_at_end_of_tune_period",
            "min_history_sessions": 504,
            "unscheduled_actions": "ignore",
        }
    )
    endpoint["decision_rule"].update(
        {
            "baseline_specs": {
                "ledoit_wolf_linear": {
                    "hyperparameter_grid": {"window": [504.0, 756.0]},
                    "selection": "min_mean_inverse_stein_over_tune_period_events",
                    "tie_break": "most_regularised",
                }
            },
            "success_criterion": "primary_comparison_decides_baselines_are_holm_secondary",
        }
    )
    endpoint["decision_rule"]["bootstrap"].update({"scheme": "moving_block", "block_length": 3})
    endpoint["status"] = "locked"
    (configs / "endpoint.yaml").write_text(yaml.safe_dump(endpoint, sort_keys=False))
    (configs / "universe.yaml").write_text(yaml.safe_dump(universe, sort_keys=False))


def test_bundle_matches_the_literal_pin(config_dir: Path) -> None:
    fingerprint = bundle_fingerprint(load_harness_config(config_dir))
    assert fingerprint == PINNED, (
        f"endpoint bundle is {fingerprint}, the pin is {PINNED}; "
        "see this module's docstring before updating it"
    )
    assert PREREGISTERED_BUNDLE_FINGERPRINT == PINNED


def test_decisions_cites_the_pinned_fingerprint(repo_root: Path) -> None:
    decisions = (repo_root / "docs" / "harness" / "DECISIONS.md").read_text(encoding="utf-8")
    assert PINNED in decisions


def test_statement_is_the_brief_verbatim(config_dir: Path) -> None:
    statement = load_harness_config(config_dir).endpoint.statement
    assert re.sub(r"\s+", " ", statement).strip() == BRIEF_STATEMENT


def test_doctor_fails_when_the_bundle_differs_from_the_pin(repo_copy: Path) -> None:
    splits = repo_copy / "configs" / "splits.yaml"
    splits.write_text(
        splits.read_text().replace("embargo_trading_days: 5", "embargo_trading_days: 6")
    )
    result = CliRunner().invoke(
        app, ["--config-dir", str(repo_copy / "configs"), "doctor"], terminal_width=250
    )
    assert result.exit_code == 1
    assert re.search(r"pre-registration\s+│\s+FAIL", result.stdout), result.stdout


def test_draft_endpoint_cannot_unlock_the_test_period(config_dir: Path) -> None:
    with pytest.raises(PreregistrationError, match="status=draft"):
        require_locked_preregistration(load_harness_config(config_dir), code=CLEAN)


def test_locking_requires_every_field_decided(repo_copy: Path) -> None:
    path = repo_copy / "configs" / "endpoint.yaml"
    path.write_text(path.read_text().replace("status: draft", "status: locked"), encoding="utf-8")
    with pytest.raises(ConfigError, match=r"refit_policy"):
        load_harness_config(repo_copy / "configs")


def test_unlock_gate_end_to_end(repo_copy: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    configs = repo_copy / "configs"
    _decide_everything_and_lock(repo_copy)
    _write_calendars(repo_copy)
    cfg = load_harness_config(configs)
    monkeypatch.setattr(
        preregistration, "PREREGISTERED_BUNDLE_FINGERPRINT", bundle_fingerprint(cfg)
    )

    report = require_locked_preregistration(cfg, code=CLEAN, expected_config_dir=configs)
    assert report.ready_to_unlock

    dirty = CodeVersion("0.1.0", "a" * 40, True)
    with pytest.raises(PreregistrationError, match="not a clean commit"):
        require_locked_preregistration(cfg, code=dirty, expected_config_dir=configs)
    with pytest.raises(PreregistrationError, match="configs must come from"):
        require_locked_preregistration(cfg, code=CLEAN)  # not the repository's configs/

    _write_calendars(repo_copy, fomc_time="19:30:00Z")  # an edited calendar breaks the pin
    with pytest.raises(PreregistrationError, match="DIFFERS from pin"):
        require_locked_preregistration(
            load_harness_config(configs), code=CLEAN, expected_config_dir=configs
        )

    (repo_copy / "data_ref" / "calendars" / "bls_cpi.csv").unlink()  # re-pinned, but missing
    cfg = load_harness_config(configs)
    monkeypatch.setattr(
        preregistration, "PREREGISTERED_BUNDLE_FINGERPRINT", bundle_fingerprint(cfg)
    )
    with pytest.raises(PreregistrationError, match="calendars missing: CPI"):
        require_locked_preregistration(cfg, code=CLEAN, expected_config_dir=configs)


def test_calendar_contents_are_part_of_the_bundle(repo_copy: Path) -> None:
    configs = repo_copy / "configs"
    before = bundle_fingerprint(load_harness_config(configs))
    _write_calendars(repo_copy)
    with_calendar = bundle_fingerprint(load_harness_config(configs))
    _write_calendars(repo_copy, fomc_time="19:30:00Z")
    edited = bundle_fingerprint(load_harness_config(configs))
    assert len({before, with_calendar, edited}) == 3


@pytest.mark.parametrize(
    ("file", "old", "new"),
    [
        ("splits.yaml", "embargo_trading_days: 5", "embargo_trading_days: 6"),
        ("universe.yaml", "tie_break: asset_id_ascending", "tie_break: null"),
        ("endpoint.yaml", "alpha: 0.05", "alpha: 0.1"),
    ],
)
def test_protocol_changes_move_the_bundle(repo_copy: Path, file: str, old: str, new: str) -> None:
    configs = repo_copy / "configs"
    before = bundle_fingerprint(load_harness_config(configs))
    for name in {file, "endpoint.yaml"} if file == "universe.yaml" else {file}:
        path = configs / name
        text = path.read_text(encoding="utf-8")
        assert old in text
        path.write_text(text.replace(old, new), encoding="utf-8")
    assert bundle_fingerprint(load_harness_config(configs)) != before


def test_survivorship_switch_cannot_be_turned_off(repo_copy: Path) -> None:
    sources = repo_copy / "configs" / "sources.yaml"
    sources.write_text(
        sources.read_text().replace("include_delisted: true", "include_delisted: false")
    )
    with pytest.raises(ConfigError, match="survivorship"):
        load_harness_config(repo_copy / "configs")


def test_report_lists_undecided_fields(config_dir: Path) -> None:
    report = verify_preregistration(load_harness_config(config_dir))
    assert "definitions.refit_policy" in report.undecided
    assert not report.ready_to_unlock
