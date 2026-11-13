"""Pre-registration of the primary endpoint, enforced at runtime.

The pinned value is a fingerprint of the *endpoint bundle*: the parsed endpoint config,
the parsed splits config (periods, horizon, purge, embargo) and the SHA-256 of every
event calendar the endpoint scores. A change to any of them changes the fingerprint, so
it can only happen together with an update of :data:`PREREGISTERED_BUNDLE_FINGERPRINT`
in this file and a dated entry in ``docs/harness/DECISIONS.md`` citing the new value
(both checked by ``tests/test_preregistration.py``; ``mjepa doctor`` fails on a mismatch).

:func:`require_locked_preregistration` is what the M3 ``--unlock-test`` gate calls: it
refuses unless the bundle matches the pin, ``status`` is ``locked``, nothing is left
undecided and every calendar exists.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

from mjepa_harness.config import HarnessConfig

PREREGISTERED_BUNDLE_FINGERPRINT: Final = (
    "sha256:fcaf725112066141350ee3d83e6c7db3401680fd29f73c034408d7bbd10f97c9"
)
"""Pinned endpoint-bundle fingerprint. Update only with a dated DECISIONS.md entry."""


class PreregistrationError(RuntimeError):
    """The endpoint bundle does not match its pre-registration, or is not locked."""


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def endpoint_bundle(cfg: HarnessConfig) -> dict[str, Any]:
    """Everything that defines the primary endpoint's number, as plain JSON data."""
    repo_root = cfg.config_dir.parent
    calendars: dict[str, dict[str, str | None]] = {}
    for event_type in cfg.endpoint.events.types:
        relative = cfg.events.types[event_type].calendar
        path = (repo_root / relative) if relative is not None else None
        calendars[event_type] = {
            "path": relative,
            "sha256": _sha256_file(path) if path is not None and path.is_file() else None,
        }
    return {
        "endpoint": cfg.endpoint.model_dump(mode="json"),
        "splits": cfg.splits.model_dump(mode="json"),
        "calendars": calendars,
    }


def bundle_fingerprint(cfg: HarnessConfig) -> str:
    canonical = json.dumps(
        endpoint_bundle(cfg), sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class PreregistrationReport:
    fingerprint: str
    pinned: str
    status: str
    undecided: tuple[str, ...]
    missing_calendars: tuple[str, ...]

    @property
    def matches_pin(self) -> bool:
        return self.fingerprint == self.pinned

    @property
    def ready_to_unlock(self) -> bool:
        return (
            self.matches_pin
            and self.status == "locked"
            and not self.undecided
            and not self.missing_calendars
        )

    def describe(self) -> str:
        parts = [f"status={self.status}", f"bundle {self.fingerprint}"]
        parts.append("matches pin" if self.matches_pin else f"DIFFERS from pin {self.pinned}")
        if self.undecided:
            parts.append(f"{len(self.undecided)} undecided field(s)")
        if self.missing_calendars:
            parts.append(f"calendars missing: {', '.join(self.missing_calendars)}")
        return "; ".join(parts)


def verify_preregistration(cfg: HarnessConfig) -> PreregistrationReport:
    bundle = endpoint_bundle(cfg)
    missing = tuple(
        event_type for event_type, info in bundle["calendars"].items() if info["sha256"] is None
    )
    return PreregistrationReport(
        fingerprint=bundle_fingerprint(cfg),
        pinned=PREREGISTERED_BUNDLE_FINGERPRINT,
        status=cfg.endpoint.status,
        undecided=tuple(cfg.endpoint.undecided()),
        missing_calendars=missing,
    )


def require_locked_preregistration(cfg: HarnessConfig) -> PreregistrationReport:
    """Gate for any read of locked-test data (M3): raise unless fully pre-registered."""
    report = verify_preregistration(cfg)
    if not report.ready_to_unlock:
        raise PreregistrationError(
            "locked-test data cannot be read: the endpoint is not a locked, complete, "
            f"pin-matching pre-registration ({report.describe()})"
        )
    return report
