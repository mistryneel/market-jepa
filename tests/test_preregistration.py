"""Pre-registration lock for the primary endpoint.

If ``test_bundle_matches_the_pin`` fails, you changed the endpoint bundle
(``configs/endpoint.yaml``, ``configs/splits.yaml`` or an event calendar it scores).
That is allowed only while ``status: draft`` and only together with (1) an update of
``PREREGISTERED_BUNDLE_FINGERPRINT`` in ``src/mjepa_harness/preregistration.py`` and
(2) a dated entry in ``docs/harness/DECISIONS.md`` that cites the new value, both in
the same commit. Once locked-test data has been read, the endpoint must not change.
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path

import pytest

from mjepa_harness.config import ConfigError, load_harness_config
from mjepa_harness.preregistration import (
    PREREGISTERED_BUNDLE_FINGERPRINT,
    PreregistrationError,
    bundle_fingerprint,
    require_locked_preregistration,
    verify_preregistration,
)

# The sentence from the project brief (section 1), verbatim.
BRIEF_STATEMENT = (
    "Mean out-of-sample Stein loss of 5-trading-day covariance forecasts (trading days 1 to 5 "
    "after the event) for the top 500 US stocks by prior-month dollar volume (price above $5, "
    "universe rebuilt monthly). It is taken across every scheduled FOMC and CPI announcement "
    "in the locked test period, paired by event, and compared with a block bootstrap across "
    "months."
)


@pytest.fixture
def repo_copy(repo_root: Path, tmp_path: Path) -> Path:
    """configs/ and data_ref/ copied into a scratch repo layout."""
    target = tmp_path / "repo"
    shutil.copytree(repo_root / "configs", target / "configs")
    shutil.copytree(repo_root / "data_ref", target / "data_ref")
    return target


def test_bundle_matches_the_pin(config_dir: Path) -> None:
    report = verify_preregistration(load_harness_config(config_dir))
    assert report.matches_pin, (
        f"endpoint bundle is {report.fingerprint}, pin is {report.pinned}; "
        "see this module's docstring before updating the pin"
    )


def test_decisions_cites_the_pinned_fingerprint(repo_root: Path) -> None:
    decisions = (repo_root / "docs" / "harness" / "DECISIONS.md").read_text(encoding="utf-8")
    assert PREREGISTERED_BUNDLE_FINGERPRINT in decisions


def test_statement_is_the_brief_verbatim(config_dir: Path) -> None:
    statement = load_harness_config(config_dir).endpoint.statement
    assert re.sub(r"\s+", " ", statement).strip() == BRIEF_STATEMENT


def test_draft_endpoint_cannot_unlock_the_test_period(config_dir: Path) -> None:
    with pytest.raises(PreregistrationError, match="status=draft"):
        require_locked_preregistration(load_harness_config(config_dir))


def test_locking_requires_every_field_decided(repo_copy: Path) -> None:
    path = repo_copy / "configs" / "endpoint.yaml"
    path.write_text(path.read_text().replace("status: draft", "status: locked"), encoding="utf-8")
    with pytest.raises(ConfigError, match=r"refit_policy"):
        load_harness_config(repo_copy / "configs")


def test_calendar_contents_are_part_of_the_bundle(repo_copy: Path) -> None:
    configs = repo_copy / "configs"
    before = bundle_fingerprint(load_harness_config(configs))
    calendar = repo_copy / "data_ref" / "calendars" / "fomc.csv"
    calendar.parent.mkdir(parents=True, exist_ok=True)
    calendar.write_text("event_id,actual_release_utc\nfomc-2022-01-26,2022-01-26T19:00:00Z\n")
    with_calendar = bundle_fingerprint(load_harness_config(configs))
    calendar.write_text("event_id,actual_release_utc\nfomc-2022-01-26,2022-01-26T19:30:00Z\n")
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
