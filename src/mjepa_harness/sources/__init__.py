"""Data-source adapters, all behind :class:`mjepa_harness.sources.base.SourceAdapter`.

Adapters register themselves in :data:`ADAPTERS` (M1).
"""

from __future__ import annotations

from mjepa_harness.sources.base import SourceAdapter

ADAPTERS: dict[str, type[SourceAdapter]] = {}


def register[A: SourceAdapter](cls: type[A]) -> type[A]:
    """Class decorator adding an adapter to :data:`ADAPTERS` under ``cls.name``."""
    name = cls.name
    if name in ADAPTERS and ADAPTERS[name] is not cls:
        raise ValueError(f"duplicate source adapter name {name!r}")
    ADAPTERS[name] = cls
    return cls


__all__ = ["ADAPTERS", "SourceAdapter", "register"]
