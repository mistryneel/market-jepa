"""The network guard itself: unit tests cannot reach the network, by construction."""

from __future__ import annotations

import os
import socket
import textwrap
import urllib.request
from pathlib import Path

import pytest

BLOCKED = "must not touch the network"


def test_create_connection_is_blocked() -> None:
    with pytest.raises(RuntimeError, match=BLOCKED):
        socket.create_connection(("example.com", 443), timeout=1)


def test_dns_resolution_is_blocked() -> None:
    with pytest.raises(RuntimeError, match=BLOCKED):
        socket.getaddrinfo("example.com", 443)


def test_raw_tcp_connect_is_blocked() -> None:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    with sock, pytest.raises(RuntimeError, match=BLOCKED):
        sock.connect(("192.0.2.1", 80))  # TEST-NET-1, never routable
    sock2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    with sock2, pytest.raises(RuntimeError, match=BLOCKED):
        sock2.connect_ex(("192.0.2.1", 80))


def test_stdlib_http_client_is_blocked() -> None:
    with pytest.raises(RuntimeError, match=BLOCKED):
        urllib.request.urlopen("http://example.com/", timeout=1)


def test_unix_sockets_still_work() -> None:
    left, right = socket.socketpair()
    with left, right:
        left.sendall(b"ok")
        assert right.recv(2) == b"ok"


def test_native_library_fallbacks_are_set() -> None:
    assert os.environ["HTTPS_PROXY"] == "http://127.0.0.1:9"
    assert os.environ["HF_HUB_OFFLINE"] == "1"


def test_unit_tests_run_without_credentials() -> None:
    from mjepa_harness.settings import CREDENTIAL_ENV_VARS

    assert not any(os.environ.get(name) for name in CREDENTIAL_ENV_VARS)


def test_guard_fails_unmarked_network_tests_and_skips_integration_without_credentials(
    pytester: pytest.Pytester, repo_root: Path
) -> None:
    """Run a throwaway suite in a subprocess with this repo's conftest and settings."""
    pytester.makeconftest((repo_root / "tests" / "conftest.py").read_text(encoding="utf-8"))
    pytester.makeini(
        textwrap.dedent(
            """
            [pytest]
            addopts = -p no:cacheprovider
            markers =
                integration: live-data test
            """
        )
    )
    pytester.makepyfile(
        test_inner=textwrap.dedent(
            """
            import socket
            from collections.abc import Callable

            import pytest


            def test_sneaky_unit_test_uses_network() -> None:
                socket.create_connection(("example.com", 80), timeout=1)


            @pytest.mark.integration
            def test_live_without_credentials(require_env: Callable[..., dict[str, str]]) -> None:
                require_env("MJEPA_TEST_DEFINITELY_UNSET_CREDENTIAL")
                raise AssertionError("should have been skipped")
            """
        )
    )
    result = pytester.runpytest_subprocess("-m", "integration or not integration")
    result.assert_outcomes(failed=1, skipped=1)
    result.stdout.fnmatch_lines(["*must not touch the network*"])
