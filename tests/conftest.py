"""Shared test configuration: the network guard and environment isolation.

Rule: unit tests never touch the network.

* A socket-level guard is installed for the whole session (collection included):
  ``socket.socket.connect``/``connect_ex``, ``socket.create_connection`` and
  ``socket.getaddrinfo`` raise. AF_UNIX sockets keep working.
* Native libraries (polars, DuckDB, pyarrow: Rust/C++) bypass Python sockets, so proxy
  variables are pointed at a closed local port and Hugging Face is forced offline as a
  second line of defence.
* Tests marked ``@pytest.mark.integration`` get the real network back for their
  duration. They are deselected by default (``-m "not integration"`` in pyproject) and
  must call the ``require_env`` fixture so they skip when credentials are missing.
* Unit tests run with credentials removed from the environment and ``MJ_DATA_DIR``
  pointed at a temporary directory, so a developer's real keys and data are never used.
* git is hermetic in unit tests: global and system git config are ignored (no commit
  signing prompts from a developer's signing agent, no global excludes) and a fixed
  test identity is used.
"""

from __future__ import annotations

import logging
import os
import socket
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any, Final, NoReturn

import pytest

from mjepa_harness.settings import CREDENTIAL_ENV_VARS

NETWORK_BLOCKED_MESSAGE: Final = (
    "unit tests must not touch the network; mark live-data tests with "
    "@pytest.mark.integration and run them with `uv run pytest -m integration`"
)

HARNESS_ENV_VARS: Final = ("MJ_DATA_DIR", "MJ_CONFIG_DIR", "MJ_LOG_LEVEL", "MJ_LOG_FORMAT")

HERMETIC_GIT_ENV: Final[dict[str, str]] = {
    "GIT_CONFIG_GLOBAL": os.devnull,
    "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_AUTHOR_NAME": "mjepa-tests",
    "GIT_AUTHOR_EMAIL": "tests@example.org",
    "GIT_COMMITTER_NAME": "mjepa-tests",
    "GIT_COMMITTER_EMAIL": "tests@example.org",
    "GIT_TERMINAL_PROMPT": "0",
}

_BLACKHOLE_PROXY: Final = "http://127.0.0.1:9"
OFFLINE_ENV: Final[dict[str, str]] = {
    **{
        name: _BLACKHOLE_PROXY
        for name in (
            "HTTP_PROXY",
            "HTTPS_PROXY",
            "ALL_PROXY",
            "http_proxy",
            "https_proxy",
            "all_proxy",
        )
    },
    "NO_PROXY": "",
    "no_proxy": "",
    "HF_HUB_OFFLINE": "1",
    "HF_DATASETS_OFFLINE": "1",
    "AWS_EC2_METADATA_DISABLED": "true",
}


class NetworkAccessInUnitTestError(RuntimeError):
    """Raised when a unit test tries to open a network connection."""


_REAL: Final[dict[str, Any]] = {
    "connect": socket.socket.connect,
    "connect_ex": socket.socket.connect_ex,
    "create_connection": socket.create_connection,
    "getaddrinfo": socket.getaddrinfo,
}
_saved_env: dict[str, str | None] = {}


def _blocked(*_args: object, **_kwargs: object) -> NoReturn:
    raise NetworkAccessInUnitTestError(NETWORK_BLOCKED_MESSAGE)


def _guarded_connect(self: socket.socket, address: Any) -> None:
    if self.family == socket.AF_UNIX:
        _REAL["connect"](self, address)
        return
    _blocked()


def _guarded_connect_ex(self: socket.socket, address: Any) -> int:
    if self.family == socket.AF_UNIX:
        result: int = _REAL["connect_ex"](self, address)
        return result
    _blocked()


def _install_guard() -> None:
    socket.socket.connect = _guarded_connect  # type: ignore[method-assign,assignment]
    socket.socket.connect_ex = _guarded_connect_ex  # type: ignore[method-assign,assignment]
    socket.create_connection = _blocked
    socket.getaddrinfo = _blocked


def _remove_guard() -> None:
    socket.socket.connect = _REAL["connect"]  # type: ignore[method-assign]
    socket.socket.connect_ex = _REAL["connect_ex"]  # type: ignore[method-assign]
    socket.create_connection = _REAL["create_connection"]
    socket.getaddrinfo = _REAL["getaddrinfo"]


def pytest_configure(config: pytest.Config) -> None:
    for name, value in OFFLINE_ENV.items():
        _saved_env[name] = os.environ.get(name)
        os.environ[name] = value
    _install_guard()


def pytest_unconfigure(config: pytest.Config) -> None:
    _remove_guard()
    for name, value in _saved_env.items():
        if value is None:
            os.environ.pop(name, None)
        else:
            os.environ[name] = value


@pytest.fixture(autouse=True)
def _isolate(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    if request.node.get_closest_marker("integration") is not None:
        # Live test: real sockets and real proxy/offline settings for its duration.
        _remove_guard()
        for name, value in _saved_env.items():
            if value is None:
                monkeypatch.delenv(name, raising=False)
            else:
                monkeypatch.setenv(name, value)
        try:
            yield
        finally:
            _install_guard()
        return

    tmp_root: Path = request.getfixturevalue("tmp_path")
    for name in (*CREDENTIAL_ENV_VARS, *HARNESS_ENV_VARS):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("MJ_DATA_DIR", str(tmp_root / "mj-data"))
    for name, value in HERMETIC_GIT_ENV.items():
        monkeypatch.setenv(name, value)
    yield
    root = logging.getLogger()
    for handler in list(root.handlers):
        if handler.get_name() == "mjepa-harness":
            root.removeHandler(handler)


@pytest.fixture
def require_env() -> Callable[..., dict[str, str]]:
    """For integration tests: skip unless every named variable is set; return their values."""

    def _require(*names: str) -> dict[str, str]:
        missing = [name for name in names if not os.environ.get(name, "").strip()]
        if missing:
            pytest.skip(f"credentials not set: {', '.join(missing)}")
        return {name: os.environ[name] for name in names}

    return _require


@pytest.fixture
def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


@pytest.fixture
def config_dir(repo_root: Path) -> Path:
    return repo_root / "configs"
