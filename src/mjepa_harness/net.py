"""Process-wide network kill switch for the harness's own network code.

Every code path in the harness that reaches the network (source adapters, HTTP/S3
clients) calls :func:`require_network` first. ``MJ_OFFLINE=1`` (set by the unit-test
configuration) makes those paths refuse, independently of any socket-level guard.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Final

_TRUTHY: Final = frozenset({"1", "true", "yes", "on"})


class NetworkDisabledError(RuntimeError):
    """The harness is in offline mode (``MJ_OFFLINE``) and code tried to use the network."""


def network_allowed(env: Mapping[str, str] | None = None) -> bool:
    source = os.environ if env is None else env
    return source.get("MJ_OFFLINE", "").strip().lower() not in _TRUTHY


def require_network(purpose: str, env: Mapping[str, str] | None = None) -> None:
    if not network_allowed(env):
        raise NetworkDisabledError(f"MJ_OFFLINE is set; refusing network access for {purpose}")
