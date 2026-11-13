"""Shared test configuration: the network guard, integration gating and isolation.

Rule: unit tests never touch the network. Layers, strongest first:

1. **CI (Linux)** runs the unit tests in a network namespace with no network at all,
   so even native code and child processes cannot connect.
2. **Audit hook** (this file): a ``sys.addaudithook`` hook raises
   :class:`NetworkAccessInUnitTestError` on every non-AF_UNIX ``socket.connect``,
   ``sendto``/``sendmsg`` and on all name resolution (``getaddrinfo``,
   ``gethostbyname*``, ``gethostbyaddr``, ``getnameinfo``). Audit events fire inside
   CPython's C socket module, so ``_socket``, ``ssl``, ``asyncio``, ``http.client`` and
   ``urllib`` are all covered. Active from session start (collection included).
3. **Native-library fallbacks**:
   - remote PyArrow filesystems (S3/GCS/Azure/HDFS) refuse construction while guarded;
   - in sessions without ``--run-integration``, Arrow's S3 subsystem is finalized, so
     ``s3://`` URIs fail too;
   - proxy variables point at a closed local port, so Rust/C++ HTTP clients that honour
     them fail fast;
   - Hugging Face is offline;
   - ``MJ_OFFLINE=1`` makes the harness's own plan/fetch paths refuse the network.

   Child processes are only stopped by layer 1. CI runs Linux tests in a network
   namespace and macOS tests under ``sandbox-exec`` with outbound IP denied.

Integration tests (``@pytest.mark.integration``) are skipped unless ``--run-integration``
is passed; a ``-m`` filter alone cannot select them. They get the real network and
real credentials, and must call ``require_env(...)`` so they skip when credentials are
missing. Unit tests run with credentials removed, ``MJ_DATA_DIR`` in a temporary
directory and hermetic git (no global/system config: no commit-signing prompts, no
global excludes, fixed identity).
"""

from __future__ import annotations

import logging
import os
import socket
import sys
from collections.abc import Callable, Generator, Iterator
from pathlib import Path
from typing import Any, Final

import pytest

from mjepa_harness.log import REDACTOR, install_record_redaction
from mjepa_harness.settings import CREDENTIAL_ENV_VARS, Credentials

NETWORK_BLOCKED_MESSAGE: Final = (
    "unit tests must not touch the network; mark live-data tests with "
    "@pytest.mark.integration and run them with `pytest --run-integration`"
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
GIT_PATH_ENV_VARS: Final = (
    "GIT_DIR",
    "GIT_WORK_TREE",
    "GIT_INDEX_FILE",
    "GIT_COMMON_DIR",
    "GIT_OBJECT_DIRECTORY",
    "GIT_ALTERNATE_OBJECT_DIRECTORIES",
)

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
    "MJ_OFFLINE": "1",
}

_BLOCKED_SOCKET_EVENTS: Final = frozenset(
    {
        "socket.getaddrinfo",
        "socket.gethostbyname",
        "socket.gethostbyaddr",
        "socket.getnameinfo",
    }
)
_ADDRESSED_SOCKET_EVENTS: Final = frozenset({"socket.connect", "socket.sendto", "socket.sendmsg"})
_REMOTE_PYARROW_FILESYSTEMS: Final = (
    "S3FileSystem",
    "GcsFileSystem",
    "AzureFileSystem",
    "HadoopFileSystem",
)


class NetworkAccessInUnitTestError(RuntimeError):
    """Raised when a unit test tries to reach the network."""


class _Guard:
    active = False
    saved_env: dict[str, str | None] = {}  # noqa: RUF012 - module-level singleton state
    pyarrow_installed = False


def _audit_hook(event: str, args: tuple[Any, ...]) -> None:
    if not _Guard.active or not event.startswith("socket."):
        return
    if event in _BLOCKED_SOCKET_EVENTS:
        raise NetworkAccessInUnitTestError(f"{NETWORK_BLOCKED_MESSAGE} ({event})")
    if event in _ADDRESSED_SOCKET_EVENTS:
        family = getattr(args[0], "family", None)
        if family != socket.AF_UNIX and (event == "socket.connect" or args[1] is not None):
            raise NetworkAccessInUnitTestError(f"{NETWORK_BLOCKED_MESSAGE} ({event})")


def _guarded_filesystem(base: type[Any]) -> type[Any]:
    """A subclass of a remote pyarrow filesystem that refuses construction while guarded.

    It replaces the module attribute once, for good, and checks the guard at *call*
    time. A name bound early (``from pyarrow.fs import S3FileSystem``) therefore follows
    the guard, and ``isinstance`` against the module attribute keeps working.
    """

    def _init(self: Any, *args: Any, **kwargs: Any) -> None:
        if _Guard.active:
            raise NetworkAccessInUnitTestError(f"{NETWORK_BLOCKED_MESSAGE} ({base.__name__})")
        base.__init__(self, *args, **kwargs)

    return type(base.__name__, (base,), {"__init__": _init, "__module__": base.__module__})


def _install_pyarrow_guard(*, finalize_s3: bool) -> None:
    import pyarrow.fs

    if not _Guard.pyarrow_installed:
        for name in _REMOTE_PYARROW_FILESYSTEMS:
            base = getattr(pyarrow.fs, name, None)
            if isinstance(base, type):
                setattr(pyarrow.fs, name, _guarded_filesystem(base))
        _Guard.pyarrow_installed = True
    if finalize_s3:
        # No integration tests in this session: shut Arrow's S3 subsystem down for good, so
        # FileSystem.from_uri("s3://...") and s3:// paths fail too (in-process only).
        pyarrow.fs.finalize_s3()


def _set_guard(active: bool) -> None:
    _Guard.active = active


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--run-integration",
        action="store_true",
        default=False,
        help="run @pytest.mark.integration tests (live network, real credentials)",
    )


def pytest_configure(config: pytest.Config) -> None:
    # Scrub every log record (pytest's captured-log report included) of the developer's
    # real credentials, before the per-test fixture removes them from the environment.
    REDACTOR.register(Credentials.from_env().secret_values())
    install_record_redaction(REDACTOR)
    for name, value in OFFLINE_ENV.items():
        _Guard.saved_env[name] = os.environ.get(name)
        os.environ[name] = value
    sys.addaudithook(_audit_hook)  # permanent for the process; toggled by _Guard.active
    _install_pyarrow_guard(finalize_s3=not config.getoption("--run-integration"))
    _set_guard(True)


def pytest_unconfigure(config: pytest.Config) -> None:
    _set_guard(False)
    for name, value in _Guard.saved_env.items():
        if value is None:
            os.environ.pop(name, None)
        else:
            os.environ[name] = value


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if config.getoption("--run-integration"):
        return
    skip = pytest.mark.skip(reason="integration test: pass --run-integration to run it")
    for item in items:
        if item.get_closest_marker("integration") is not None:
            item.add_marker(skip)


@pytest.hookimpl(wrapper=True)
def pytest_runtest_makereport(
    item: pytest.Item, call: pytest.CallInfo[None]
) -> Generator[None, pytest.TestReport, pytest.TestReport]:
    """Redact failure reports and captured output, which never pass through logging."""
    report: pytest.TestReport = yield
    if report.longrepr is not None:
        text = str(report.longrepr)
        redacted = REDACTOR.redact(text)
        if redacted != text:
            report.longrepr = redacted
    report.sections = [(name, REDACTOR.redact(content)) for name, content in report.sections]
    return report


@pytest.fixture(autouse=True)
def _isolate(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    if request.node.get_closest_marker("integration") is not None:
        # Live test: real network and the session's original proxy/offline settings.
        for name, value in _Guard.saved_env.items():
            if value is None:
                monkeypatch.delenv(name, raising=False)
            else:
                monkeypatch.setenv(name, value)
        _set_guard(False)
        try:
            yield
        finally:
            _set_guard(True)
        return

    tmp_root: Path = request.getfixturevalue("tmp_path")
    for name in (*CREDENTIAL_ENV_VARS, *HARNESS_ENV_VARS, *GIT_PATH_ENV_VARS):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("MJ_DATA_DIR", str(tmp_root / "mj-data"))
    for name, value in HERMETIC_GIT_ENV.items():
        monkeypatch.setenv(name, value)
    xdg = tmp_root / "xdg-config"  # git also reads $XDG_CONFIG_HOME/git/ignore
    xdg.mkdir(exist_ok=True)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg))
    yield
    root = logging.getLogger()
    for handler in list(root.handlers):
        if handler.get_name() == "mjepa-harness":
            root.removeHandler(handler)
    install_record_redaction(REDACTOR)


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
