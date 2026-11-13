from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from typer.testing import CliRunner

from mjepa_harness import __version__
from mjepa_harness.cli import app

SECRET = "cli-secret-value-777777"
runner = CliRunner()


def test_help_lists_commands() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    for command in ("doctor", "paths", "config"):
        assert command in result.stdout


def test_console_script_entry_point_runs() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "mjepa_harness.cli", "--help"],
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )
    assert result.returncode == 0, result.stderr
    assert "doctor" in result.stdout


def test_version() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert f"mjepa-harness {__version__}" in result.stdout


def test_doctor_passes_without_credentials_and_reports_them_missing() -> None:
    result = runner.invoke(app, ["doctor"], terminal_width=200)
    assert result.exit_code == 0, result.stdout
    assert "env FRED_API_KEY" in result.stdout
    assert "missing" in result.stdout
    assert "status=draft" in result.stdout


def test_doctor_never_prints_secret_values(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("MASSIVE_API_KEY", "FRED_API_KEY", "HF_TOKEN", "SEC_USER_AGENT"):
        monkeypatch.setenv(name, f"{SECRET}-{name}")
    result = runner.invoke(app, ["doctor"], terminal_width=200)
    assert result.exit_code == 0
    assert SECRET not in result.stdout
    assert SECRET not in (result.stderr or "")


def test_doctor_fails_on_data_dir_inside_repo_that_git_does_not_ignore(repo_root: Path) -> None:
    if shutil.which("git") is None:
        pytest.skip("git not available")
    unsafe = repo_root / "configs" / "not-ignored-data"
    result = runner.invoke(app, ["--data-dir", str(unsafe), "doctor"], terminal_width=200)
    assert result.exit_code == 1
    assert "NOT" in result.stdout
    assert not unsafe.exists()


def test_config_validate_and_show() -> None:
    result = runner.invoke(app, ["config", "validate"], terminal_width=200)
    assert result.exit_code == 0
    assert "endpoint.yaml" in result.stdout
    shown = runner.invoke(app, ["config", "show", "endpoint"], terminal_width=200)
    assert shown.exit_code == 0
    assert "primary-post-event-stein-5d" in shown.stdout
    bad = runner.invoke(app, ["config", "show", "nonsense"])
    assert bad.exit_code != 0


def test_config_validate_fails_on_broken_config(config_dir: Path, tmp_path: Path) -> None:
    broken = tmp_path / "configs"
    shutil.copytree(config_dir, broken)
    (broken / "splits.yaml").write_text("periods: []\n", encoding="utf-8")
    result = runner.invoke(app, ["--config-dir", str(broken), "config", "validate"])
    assert result.exit_code == 1
    assert "config error" in result.stdout


def test_paths_creates_nothing() -> None:
    data_dir = Path(os.environ["MJ_DATA_DIR"])
    result = runner.invoke(app, ["paths"], terminal_width=200)
    assert result.exit_code == 0
    assert "locked" in result.stdout
    assert not data_dir.exists()


def test_invalid_log_level_is_a_usage_error() -> None:
    result = runner.invoke(app, ["--log-level", "LOUD", "paths"])
    assert result.exit_code == 2
