from __future__ import annotations

from pathlib import Path

import pytest

from mjepa_harness.settings import (
    CREDENTIAL_ENV_VARS,
    Credentials,
    MissingCredentialError,
    Settings,
    resolve_data_dir,
    resolve_log_format,
    resolve_log_level,
)

SECRET = "sk_EXAMPLE_9f8e7d6c5b4a3210"


def test_default_data_dir_is_outside_repo_under_home() -> None:
    assert resolve_data_dir({"HOME": "/home/alice"}) == Path("/home/alice/data/market-jepa")


def test_env_var_overrides_default_and_empty_means_unset() -> None:
    env = {"HOME": "/h", "MJ_DATA_DIR": "/mnt/fast/mj"}
    assert resolve_data_dir(env) == Path("/mnt/fast/mj")
    assert resolve_data_dir({"HOME": "/h", "MJ_DATA_DIR": "   "}) == Path("/h/data/market-jepa")


def test_cli_override_beats_env() -> None:
    env = {"HOME": "/h", "MJ_DATA_DIR": "/from/env"}
    assert resolve_data_dir(env, override="/from/cli") == Path("/from/cli")


def test_variables_and_tilde_are_expanded() -> None:
    env = {"HOME": "/h", "SCRATCH": "/scratch", "MJ_DATA_DIR": "${SCRATCH}/mj"}
    assert resolve_data_dir(env) == Path("/scratch/mj")
    assert resolve_data_dir({"HOME": "/h", "MJ_DATA_DIR": "~/x"}) == Path("/h/x")


def test_unknown_variable_is_an_error_not_a_literal_directory() -> None:
    with pytest.raises(ValueError, match=r"\$NOPE"):
        resolve_data_dir({"HOME": "/h", "MJ_DATA_DIR": "$NOPE/mj"})


def test_credentials_are_masked_everywhere() -> None:
    creds = Credentials.from_env({"FRED_API_KEY": SECRET})
    assert creds.is_set("FRED_API_KEY")
    assert SECRET not in repr(creds)
    assert SECRET not in str(creds.get("FRED_API_KEY"))
    assert SECRET not in repr(Settings.from_env({"HOME": "/h", "FRED_API_KEY": SECRET}))
    assert creds.require("FRED_API_KEY") == SECRET
    assert creds.secret_values() == (SECRET,)


def test_presence_lists_every_credential_without_values() -> None:
    presence = Credentials.from_env({"HF_TOKEN": SECRET}).presence()
    assert set(presence) == set(CREDENTIAL_ENV_VARS)
    assert presence["HF_TOKEN"] is True
    assert presence["FRED_API_KEY"] is False


def test_whitespace_only_credential_counts_as_missing() -> None:
    assert not Credentials.from_env({"FRED_API_KEY": "   "}).is_set("FRED_API_KEY")


def test_missing_credential_error_is_actionable() -> None:
    with pytest.raises(MissingCredentialError, match=r"FRED_API_KEY.*HUMAN_TODO"):
        Credentials.from_env({}).require("FRED_API_KEY")


def test_unknown_credential_name_is_rejected() -> None:
    with pytest.raises(KeyError):
        Credentials.from_env({}).get("AWS_SECRET_ACCESS_KEY")


def test_log_level_and_format_validation() -> None:
    assert resolve_log_level({"MJ_LOG_LEVEL": "debug"}) == "DEBUG"
    assert resolve_log_format({}) == "text"
    with pytest.raises(ValueError, match="invalid log level"):
        resolve_log_level({"MJ_LOG_LEVEL": "LOUD"})
    with pytest.raises(ValueError, match="invalid log format"):
        resolve_log_format({"MJ_LOG_FORMAT": "xml"})
