"""The network guard itself: unit tests cannot reach the network, by construction.

Blocked-network probes target 192.0.2.1 (TEST-NET-1, never routable) or the reserved
``.invalid`` TLD, so even a regressed guard cannot reach a real host.
"""

from __future__ import annotations

import _socket
import asyncio
import os
import socket
import tempfile
import textwrap
import urllib.request
from pathlib import Path

import pyarrow.fs
import pytest

BLOCKED = "must not touch the network"
TEST_NET = ("192.0.2.1", 80)


def test_create_connection_is_blocked() -> None:
    with pytest.raises(RuntimeError, match=BLOCKED):
        socket.create_connection(TEST_NET, timeout=1)


@pytest.mark.parametrize(
    "resolve",
    [
        lambda: socket.getaddrinfo("example.invalid", 443),
        lambda: socket.gethostbyname("example.invalid"),
        lambda: socket.gethostbyname_ex("example.invalid"),
        lambda: socket.gethostbyaddr("192.0.2.1"),
        lambda: socket.getnameinfo(TEST_NET, 0),
    ],
)
def test_name_resolution_is_blocked(resolve: object) -> None:
    assert callable(resolve)
    with pytest.raises(RuntimeError, match=BLOCKED):
        resolve()


def test_raw_tcp_connect_is_blocked() -> None:
    for connect in ("connect", "connect_ex"):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        with sock, pytest.raises(RuntimeError, match=BLOCKED):
            getattr(sock, connect)(TEST_NET)


def test_c_level_socket_module_is_blocked() -> None:
    sock = _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM)
    try:
        with pytest.raises(RuntimeError, match=BLOCKED):
            sock.connect(TEST_NET)
    finally:
        sock.close()


def test_udp_sendto_is_blocked() -> None:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    with sock, pytest.raises(RuntimeError, match=BLOCKED):
        sock.sendto(b"x", ("192.0.2.1", 53))


def test_stdlib_http_client_is_blocked() -> None:
    with pytest.raises(RuntimeError, match=BLOCKED):
        urllib.request.urlopen("http://example.invalid/", timeout=1)


def test_asyncio_is_blocked() -> None:
    async def connect() -> None:
        await asyncio.open_connection("192.0.2.1", 80)

    with pytest.raises(RuntimeError, match=BLOCKED):
        asyncio.run(connect())


def test_remote_pyarrow_filesystems_are_blocked() -> None:
    with pytest.raises(RuntimeError, match=BLOCKED):
        pyarrow.fs.S3FileSystem(region="us-east-1")


def test_unix_sockets_still_work() -> None:
    left, right = socket.socketpair()
    with left, right:
        left.sendall(b"ok")
        assert right.recv(2) == b"ok"
    # A path-based AF_UNIX server too (short dir: macOS limits socket paths to 104 bytes).
    with tempfile.TemporaryDirectory(dir="/tmp") as short:
        path = str(Path(short) / "s")
        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        with server, client:
            server.bind(path)
            server.listen(1)
            client.connect(path)
            conn, _ = server.accept()
            with conn:
                client.sendall(b"hi")
                assert conn.recv(2) == b"hi"


def test_native_library_fallbacks_are_set() -> None:
    assert os.environ["HTTPS_PROXY"] == "http://127.0.0.1:9"
    assert os.environ["HF_HUB_OFFLINE"] == "1"
    assert os.environ["MJ_OFFLINE"] == "1"


def test_unit_tests_run_without_credentials() -> None:
    from mjepa_harness.settings import CREDENTIAL_ENV_VARS

    assert not any(os.environ.get(name) for name in CREDENTIAL_ENV_VARS)


_INNER_UNIT = """
import os
import socket
import tempfile
from pathlib import Path

import pytest


def test_1_unit_test_that_uses_the_network_fails() -> None:
    socket.create_connection(("192.0.2.1", 80), timeout=0.5)


@pytest.mark.integration
def test_2_integration_is_skipped_without_the_flag() -> None:
    raise AssertionError("must not run without --run-integration")


def test_3_guard_still_active_after_an_integration_item() -> None:
    with pytest.raises(RuntimeError, match="must not touch the network"):
        socket.getaddrinfo("example.invalid", 80)


def test_4_planted_credentials_are_scrubbed() -> None:
    assert os.environ.get("FRED_API_KEY") is None
"""

_INNER_INTEGRATION = """
import socket
from collections.abc import Callable

import pytest


@pytest.mark.integration
def test_1_integration_has_the_network_back() -> None:
    socket.getaddrinfo("localhost", None)  # resolves locally; raises if the guard were on


@pytest.mark.integration
def test_2_integration_without_credentials_skips(
    require_env: Callable[..., dict[str, str]],
) -> None:
    require_env("MJEPA_TEST_DEFINITELY_UNSET_CREDENTIAL")
    raise AssertionError("should have been skipped")


def test_3_unit_guard_restored_after_integration() -> None:
    with pytest.raises(RuntimeError, match="must not touch the network"):
        socket.getaddrinfo("example.invalid", 80)
"""


def _inner_suite(pytester: pytest.Pytester, repo_root: Path) -> None:
    """A throwaway suite laid out like this repo, with its real conftest and pytest config."""
    pytester.makepyprojecttoml((repo_root / "pyproject.toml").read_text(encoding="utf-8"))
    tests = pytester.path / "tests"
    tests.mkdir()
    (tests / "conftest.py").write_text(
        (repo_root / "tests" / "conftest.py").read_text(encoding="utf-8"), encoding="utf-8"
    )
    (tests / "test_inner_unit.py").write_text(textwrap.dedent(_INNER_UNIT), encoding="utf-8")
    (tests / "test_inner_integration.py").write_text(
        textwrap.dedent(_INNER_INTEGRATION), encoding="utf-8"
    )


def test_guard_and_gating_with_the_real_config(
    pytester: pytest.Pytester, repo_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _inner_suite(pytester, repo_root)
    monkeypatch.setenv("FRED_API_KEY", "planted-EXAMPLE-credential")
    result = pytester.runpytest_subprocess("-p", "no:cacheprovider", "tests/test_inner_unit.py")
    result.assert_outcomes(failed=1, passed=2, skipped=1)
    result.stdout.fnmatch_lines(["*must not touch the network*"])
    # A user's own -m filter must not bring integration tests (and the network) back.
    by_marker = pytester.runpytest_subprocess("-p", "no:cacheprovider", "-m", "integration")
    by_marker.assert_outcomes(skipped=3, deselected=4)


def test_run_integration_flag_restores_then_reinstates_the_guard(
    pytester: pytest.Pytester, repo_root: Path
) -> None:
    _inner_suite(pytester, repo_root)
    result = pytester.runpytest_subprocess(
        "-p", "no:cacheprovider", "--run-integration", "tests/test_inner_integration.py"
    )
    result.assert_outcomes(passed=2, skipped=1)
