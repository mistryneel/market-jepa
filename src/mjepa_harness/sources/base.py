"""The source adapter contract: ``plan() -> fetch() -> normalize()``.

M0 defines the contract and the download guard only; concrete adapters arrive in M1.

* :meth:`SourceAdapter.plan` lists what would be fetched, with a size/time estimate,
  without downloading anything. It marks files already present in the landing zone
  (same size and checksum) so a re-run plans zero bytes.
* :meth:`SourceAdapter.fetch` downloads the plan into ``raw/<source>/`` (resumable,
  idempotent; partial files go to ``tmp/`` and are renamed atomically) and writes a
  :class:`Manifest` of files, sizes, SHA-256 checksums, source URL, fetch time and code
  version. Callers must pass the plan through :func:`check_download_budget` first.
* :meth:`SourceAdapter.normalize` turns manifest files into point-in-time Parquet
  tables carrying ``event_time``, ``knowledge_time``, ``source`` and ``ingested_at``.

Rule: a remote URI recorded in a plan or manifest never contains credentials.
"""

from __future__ import annotations

import abc
from collections.abc import Mapping, Sequence
from typing import ClassVar, Final, Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

BYTES_PER_GB: Final = 1_000_000_000
"""Decimal gigabytes, as used by --max-gb and every printed estimate."""

PIT_COLUMNS: Final[tuple[str, ...]] = ("event_time", "knowledge_time", "source", "ingested_at")
"""Columns every normalized table must carry (plus ``asset_id`` where relevant)."""


class _Frozen(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


JsonScalar = str | int | float | bool | None


class PlannedFile(_Frozen):
    remote_uri: str = Field(description="remote location, never containing credentials")
    relative_path: str = Field(description="destination under raw/<source>/")
    expected_bytes: int | None = Field(default=None, ge=0)
    expected_checksum: str | None = Field(
        default=None, description="'sha256:<hex>' when known, else e.g. 'etag:<value>'"
    )
    already_present: bool = False


class FetchPlan(_Frozen):
    source: str
    request: Mapping[str, JsonScalar | list[JsonScalar]]
    files: tuple[PlannedFile, ...]
    estimate_basis: str = Field(description="how sizes/times were estimated, e.g. 'HF tree API'")
    estimated_seconds: float | None = Field(default=None, ge=0)
    required_credentials: tuple[str, ...] = ()
    missing_credentials: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()

    @property
    def files_to_fetch(self) -> tuple[PlannedFile, ...]:
        return tuple(f for f in self.files if not f.already_present)

    @property
    def bytes_to_fetch(self) -> int | None:
        """Total bytes still to download, or None if any pending file's size is unknown."""
        sizes = [f.expected_bytes for f in self.files_to_fetch]
        if any(size is None for size in sizes):
            return None
        return sum(size for size in sizes if size is not None)


class ManifestEntry(_Frozen):
    relative_path: str
    size_bytes: int = Field(ge=0)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_url: str = Field(description="never contains credentials")
    fetched_at: AwareDatetime
    http_etag: str | None = None
    attributes: Mapping[str, str] = Field(
        default_factory=dict,
        description="source-specific facts, e.g. {'quote_size_convention': 'shares'}",
    )


class Manifest(_Frozen):
    schema_version: Literal[1] = 1
    source: str
    fetch_id: str
    request: Mapping[str, JsonScalar | list[JsonScalar]]
    code_version: str
    started_at: AwareDatetime
    finished_at: AwareDatetime
    entries: tuple[ManifestEntry, ...]

    @model_validator(mode="after")
    def _times_ordered(self) -> Manifest:
        if self.finished_at < self.started_at:
            raise ValueError("manifest finished_at is before started_at")
        return self


class NormalizedTable(_Frozen):
    name: str
    path: str
    rows: int = Field(ge=0)
    min_knowledge_time: AwareDatetime | None = None
    max_knowledge_time: AwareDatetime | None = None


class SourceAdapter(abc.ABC):
    """Base class for every data source (M1 implements one subclass per source)."""

    name: ClassVar[str]
    required_env: ClassVar[tuple[str, ...]] = ()

    @abc.abstractmethod
    def plan(self, **request: JsonScalar | list[JsonScalar]) -> FetchPlan:
        """Describe what would be fetched; must not download data."""

    @abc.abstractmethod
    def fetch(self, plan: FetchPlan) -> Manifest:
        """Download ``plan`` into the raw landing zone and write its manifest."""

    @abc.abstractmethod
    def normalize(self, manifest: Manifest) -> Sequence[NormalizedTable]:
        """Turn raw files into point-in-time Parquet tables."""


# --------------------------------------------------------------------------- guard


class DownloadRefusedError(RuntimeError):
    """A planned download exceeds the size budget (or its size is unknown) without --yes."""


def format_estimate(plan: FetchPlan) -> str:
    """One-line human estimate: files, GB and time."""
    pending = len(plan.files_to_fetch)
    present = len(plan.files) - pending
    size = plan.bytes_to_fetch
    size_text = "unknown size" if size is None else f"{size / BYTES_PER_GB:.3f} GB"
    if plan.estimated_seconds is None:
        time_text = "unknown time"
    else:
        time_text = f"~{plan.estimated_seconds / 60:.1f} min"
    return (
        f"[{plan.source}] {pending} file(s) to fetch ({present} already present), "
        f"{size_text}, {time_text} (basis: {plan.estimate_basis})"
    )


def check_download_budget(plan: FetchPlan, *, max_gb: float, yes: bool) -> None:
    """Enforce rule 4: refuse anything over ``max_gb`` (or of unknown size) unless ``yes``."""
    if max_gb <= 0:
        raise ValueError("max_gb must be positive")
    if plan.missing_credentials:
        missing = ", ".join(plan.missing_credentials)
        raise DownloadRefusedError(
            f"[{plan.source}] missing credentials: {missing}. See docs/harness/HUMAN_TODO.md."
        )
    if yes:
        return
    size = plan.bytes_to_fetch
    if size is None:
        raise DownloadRefusedError(
            f"[{plan.source}] download size is unknown; re-run with --yes to proceed anyway"
        )
    if size > max_gb * BYTES_PER_GB:
        raise DownloadRefusedError(
            f"[{plan.source}] planned download is {size / BYTES_PER_GB:.3f} GB, above the "
            f"--max-gb limit of {max_gb:g} GB; re-run with --yes (or a higher --max-gb)"
        )
