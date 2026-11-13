"""The source adapter contract: ``plan() -> fetch() -> normalize()``.

M0 defines the contract, its data models and the guards. Concrete adapters come in M1.

* :meth:`SourceAdapter.plan` lists what would be fetched, with a size and time estimate,
  without downloading anything. Files already in the landing zone (same remote version
  and checksum) are marked ``already_present``, so a re-run plans zero bytes.
* :meth:`SourceAdapter.fetch` is a **concrete template method**. Adapters cannot skip
  its steps, which always run in this order:
  1. print the estimate;
  2. check the ``MJ_OFFLINE`` kill switch;
  3. refuse an unsafe data directory;
  4. work out missing credentials from ``required_env``;
  5. enforce the size budget (``--max-gb`` / ``--yes``).
  Only then does it call the adapter's :meth:`SourceAdapter._download` with an
  :class:`ApprovedPlan`.
* :meth:`SourceAdapter.normalize` turns manifest files into point-in-time Parquet tables
  carrying ``event_time``, ``knowledge_time``, ``source`` and ``ingested_at``, and records
  their lineage.

Landing-zone rules (implemented in M1): ``raw/`` is write-once. A changed remote object
is stored under a new path and never overwrites bytes an older manifest points to. Each
entry records the object's remote version (HF commit, ETag, Last-Modified). A manifest
lists the full state of its request, including files kept from earlier fetches, which
are identified by ``origin_fetch_id``.

URIs and request values recorded here never contain credentials; the validators refuse
them.
"""

from __future__ import annotations

import abc
import math
import re
import urllib.parse
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import PurePosixPath
from types import MappingProxyType
from typing import Annotated, Any, ClassVar, Final, Literal

from pydantic import (
    AfterValidator,
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    PlainSerializer,
    model_validator,
)

from mjepa_harness.log import REDACTOR, SENSITIVE_KEY_PATTERN
from mjepa_harness.net import require_network
from mjepa_harness.paths import DataLayout, check_data_dir_safe
from mjepa_harness.settings import Settings

BYTES_PER_GB: Final = 1_000_000_000
"""Decimal gigabytes, as used by --max-gb and every printed estimate."""

PIT_COLUMNS: Final[tuple[str, ...]] = ("event_time", "knowledge_time", "source", "ingested_at")
"""Columns every normalized table must carry (plus ``asset_id`` where relevant)."""

_SENSITIVE_QUERY_KEY: Final = re.compile(rf"(?i)^(?:[a-z0-9_-]*[_-])?(?:{SENSITIVE_KEY_PATTERN})$")
_WINDOWS_DRIVE: Final = re.compile(r"^[A-Za-z]:")


# --------------------------------------------------------------------------- field types


def _to_utc(value: datetime) -> datetime:
    return value.astimezone(UTC)


UtcDatetime = Annotated[AwareDatetime, AfterValidator(_to_utc)]
"""Timezone-aware input, stored normalised to UTC."""


def _check_relative_path(value: str) -> str:
    path = PurePosixPath(value)
    if (
        not value
        or "\\" in value
        or _WINDOWS_DRIVE.match(value)
        or path.is_absolute()
        or any(part in ("..", ".") for part in path.parts)
        or str(path) != value
    ):
        raise ValueError(
            f"{value!r} must be a normalised relative POSIX path (no '..', '.', '/' prefix, "
            "backslash or drive letter)"
        )
    return value


RelPath = Annotated[str, AfterValidator(_check_relative_path)]


def _contains_credentials(text: str) -> bool:
    if REDACTOR.redact(text) != text:
        return True
    parts = urllib.parse.urlsplit(text)
    if parts.username or parts.password:
        return True
    return any(
        _SENSITIVE_QUERY_KEY.match(key)
        for key, _ in urllib.parse.parse_qsl(parts.query, keep_blank_values=True)
    )


def _check_credential_free(value: str) -> str:
    if _contains_credentials(value):
        raise ValueError(
            "URI or value appears to contain credentials (userinfo, a key/token/signature "
            "parameter or a registered secret); record it with strip_credentials()"
        )
    return value


CredentialFreeStr = Annotated[str, AfterValidator(_check_credential_free)]


def strip_credentials(url: str) -> str:
    """``url`` without userinfo and without key/token/signature-like query parameters."""
    parts = urllib.parse.urlsplit(url)
    netloc = parts.hostname or ""
    if parts.port is not None:
        netloc = f"{netloc}:{parts.port}"
    query = [
        (key, value)
        for key, value in urllib.parse.parse_qsl(parts.query, keep_blank_values=True)
        if not _SENSITIVE_QUERY_KEY.match(key)
    ]
    return urllib.parse.urlunsplit(
        (parts.scheme, netloc, parts.path, urllib.parse.urlencode(query), parts.fragment)
    )


JsonScalar = str | int | float | bool | None


def _freeze_request(value: Mapping[str, Any]) -> Mapping[str, Any]:
    frozen: dict[str, Any] = {}
    for key, item in value.items():
        if isinstance(item, list | tuple):
            frozen[key] = tuple(item)
            texts = [str(x) for x in item]
        else:
            frozen[key] = item
            texts = [str(item)]
        for text in (key, *texts):
            _check_credential_free(text)
    return MappingProxyType(frozen)


RequestMapping = Annotated[
    Mapping[str, JsonScalar | tuple[JsonScalar, ...] | list[JsonScalar]],
    AfterValidator(_freeze_request),
    PlainSerializer(lambda v: {k: list(x) if isinstance(x, tuple) else x for k, x in v.items()}),
]
"""Immutable, credential-free request parameters (JSON scalars or lists of them)."""

AttributeMapping = Annotated[
    Mapping[str, str],
    AfterValidator(lambda v: MappingProxyType(dict(v))),
    PlainSerializer(lambda v: dict(v)),
]


class _Frozen(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


# --------------------------------------------------------------------------- models


class PlannedFile(_Frozen):
    remote_uri: CredentialFreeStr
    relative_path: RelPath = Field(description="destination under raw/<source>/")
    expected_bytes: int | None = Field(default=None, ge=0, description="exact, from a listing")
    estimated_bytes: int | None = Field(default=None, ge=0, description="heuristic estimate")
    expected_checksum: str | None = Field(
        default=None, description="'sha256:<hex>' when known, else e.g. 'etag:<value>'"
    )
    remote_version: str | None = Field(
        default=None, description="e.g. 'hf:<commit sha>', 'etag:<value>', 'last-modified:<iso>'"
    )
    already_present: bool = False

    @property
    def size_hint(self) -> int | None:
        return self.expected_bytes if self.expected_bytes is not None else self.estimated_bytes


class FetchPlan(_Frozen):
    source: str
    request: RequestMapping
    files: tuple[PlannedFile, ...]
    estimate_basis: str = Field(description="how sizes/times were estimated, e.g. 'HF tree API'")
    estimated_seconds: float = Field(ge=0, description="required: rule 4 prints a time estimate")
    required_credentials: tuple[str, ...] = ()
    missing_credentials: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()

    @property
    def files_to_fetch(self) -> tuple[PlannedFile, ...]:
        return tuple(f for f in self.files if not f.already_present)

    @property
    def known_bytes(self) -> int:
        """Bytes still to download over the pending files whose size is known or estimated."""
        return sum(f.size_hint or 0 for f in self.files_to_fetch)

    @property
    def unknown_size_count(self) -> int:
        return sum(1 for f in self.files_to_fetch if f.size_hint is None)


class CodeVersionRecord(_Frozen):
    package_version: str
    git_sha: str | None
    git_dirty: bool | None


class ManifestEntry(_Frozen):
    relative_path: RelPath = Field(description="storage path under raw/<source>/ (write-once)")
    size_bytes: int = Field(ge=0)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_url: CredentialFreeStr
    fetched_at: UtcDatetime
    remote_version: str | None = None
    http_etag: str | None = None
    origin_fetch_id: str | None = Field(
        default=None, description="fetch that downloaded the file, if not this one"
    )
    attributes: AttributeMapping = Field(
        default_factory=dict,
        description="source-specific facts, e.g. {'quote_size_convention': 'shares'}",
    )


class Manifest(_Frozen):
    schema_version: Literal[2] = 2
    source: str
    fetch_id: str
    request: RequestMapping
    code_version: CodeVersionRecord
    started_at: UtcDatetime
    finished_at: UtcDatetime
    entries: tuple[ManifestEntry, ...]

    @model_validator(mode="after")
    def _times_ordered(self) -> Manifest:
        if self.finished_at < self.started_at:
            raise ValueError("manifest finished_at is before started_at")
        return self


class NormalizedTable(_Frozen):
    name: str
    path: RelPath = Field(description="path under pit/")
    rows: int = Field(ge=0)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    input_fetch_ids: tuple[str, ...]
    code_version: CodeVersionRecord
    min_knowledge_time: UtcDatetime | None = None
    max_knowledge_time: UtcDatetime | None = None


# --------------------------------------------------------------------------- guard


class DownloadRefusedError(RuntimeError):
    """A planned download exceeds the size budget (or its size is unknown) without --yes."""


def format_estimate(plan: FetchPlan) -> str:
    """One-line human estimate: files, GB (and how many sizes are unknown), time."""
    pending = len(plan.files_to_fetch)
    present = len(plan.files) - pending
    unknown = plan.unknown_size_count
    size_text = f"{plan.known_bytes / BYTES_PER_GB:.3f} GB"
    if unknown:
        size_text += f" + {unknown} file(s) of unknown size"
    return (
        f"[{plan.source}] {pending} file(s) to fetch ({present} already present), "
        f"{size_text}, ~{plan.estimated_seconds / 60:.1f} min (basis: {plan.estimate_basis})"
    )


def check_download_budget(plan: FetchPlan, *, max_gb: float, yes: bool) -> None:
    """Rule 4: refuse anything over ``max_gb`` (or partly of unknown size) unless ``yes``.

    Missing credentials are refused even with ``yes``.
    """
    if not math.isfinite(max_gb) or max_gb <= 0:
        raise ValueError(f"max_gb must be a positive finite number, got {max_gb!r}")
    if plan.missing_credentials:
        missing = ", ".join(plan.missing_credentials)
        raise DownloadRefusedError(
            f"[{plan.source}] missing credentials: {missing}. See docs/harness/HUMAN_TODO.md."
        )
    if yes:
        return
    known_gb = plan.known_bytes / BYTES_PER_GB
    if plan.unknown_size_count:
        raise DownloadRefusedError(
            f"[{plan.source}] {plan.unknown_size_count} file(s) have unknown size (known part: "
            f"{known_gb:.3f} GB); re-run with --yes to proceed anyway"
        )
    if plan.known_bytes > max_gb * BYTES_PER_GB:
        raise DownloadRefusedError(
            f"[{plan.source}] planned download is {known_gb:.3f} GB, above the --max-gb limit "
            f"of {max_gb:g} GB; re-run with --yes (or a higher --max-gb)"
        )


# --------------------------------------------------------------------------- adapter


@dataclass(frozen=True)
class SourceContext:
    """What an adapter may use: settings (incl. credentials), the data layout, provenance."""

    settings: Settings
    layout: DataLayout
    code_version: CodeVersionRecord


@dataclass(frozen=True)
class ApprovedPlan:
    """A plan that passed every guard. Only :meth:`SourceAdapter.fetch` creates one."""

    plan: FetchPlan
    max_gb: float
    yes: bool
    approved_at: datetime


class SourceAdapter(abc.ABC):
    """Base class for every data source (M1 implements one subclass per source)."""

    name: ClassVar[str]
    required_env: ClassVar[tuple[str, ...]] = ()

    def __init__(self, context: SourceContext) -> None:
        self.context = context

    @abc.abstractmethod
    def plan(self, **request: JsonScalar | list[JsonScalar]) -> FetchPlan:
        """Describe what would be fetched. Must not download data."""

    def fetch(
        self, plan: FetchPlan, *, max_gb: float, yes: bool, echo: Callable[[str], Any]
    ) -> Manifest:
        """Run every guard in order, then download. Adapters implement :meth:`_download`."""
        if plan.source != self.name:
            raise ValueError(f"plan is for source {plan.source!r}, not {self.name!r}")
        echo(format_estimate(plan))
        require_network(f"fetching {self.name}")
        check_data_dir_safe(self.context.layout.root)
        credentials = self.context.settings.credentials
        missing = tuple(name for name in self.required_env if not credentials.is_set(name))
        checked = plan.model_copy(
            update={
                "required_credentials": self.required_env,
                "missing_credentials": tuple(dict.fromkeys((*plan.missing_credentials, *missing))),
            }
        )
        check_download_budget(checked, max_gb=max_gb, yes=yes)
        approved = ApprovedPlan(plan=checked, max_gb=max_gb, yes=yes, approved_at=datetime.now(UTC))
        return self._download(approved)

    @abc.abstractmethod
    def _download(self, approved: ApprovedPlan) -> Manifest:
        """Download ``approved.plan`` into the write-once landing zone; write its manifest."""

    @abc.abstractmethod
    def normalize(self, manifest: Manifest) -> Sequence[NormalizedTable]:
        """Turn raw files into point-in-time Parquet tables."""
