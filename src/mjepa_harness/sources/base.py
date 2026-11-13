"""The source adapter contract: ``plan() -> fetch() -> normalize()``.

M0 defines the contract, its data models and the guards. Concrete adapters come in M1.

Adapters implement three methods:

* ``_plan`` lists what would be fetched, with a size and time estimate, without
  downloading anything. Files already in the landing zone (same remote version and
  checksum) are marked ``already_present``, so a re-run plans zero bytes.
* ``_download`` writes an approved plan into the write-once landing zone.
* :meth:`SourceAdapter.normalize` turns manifest files into point-in-time Parquet tables
  carrying ``event_time``, ``knowledge_time``, ``source`` and ``ingested_at``, and
  records their lineage.

The public :meth:`SourceAdapter.plan` and :meth:`SourceAdapter.fetch` are **final
template methods**: a subclass that overrides either fails at class definition, and
mypy reports it. ``plan`` honours the ``MJ_OFFLINE`` kill switch. ``fetch`` always runs,
in order:
1. print the estimate;
2. the kill switch;
3. the data-dir guard;
4. missing credentials;
5. the ``--max-gb``/``--yes`` budget.

It then hands ``_download`` an :class:`ApprovedPlan` (which only ``fetch`` can create).
That plan carries a :class:`ByteBudget` capping the bytes actually downloaded.

Landing-zone rules (writer in M1): ``raw/`` is write-once. A changed remote object is
stored under a new path. Entries record the remote version (HF commit, ETag,
Last-Modified), and a manifest lists the full state of its request (files kept from
earlier fetches carry ``origin_fetch_id``).

No string anywhere in a plan or manifest may carry credentials: URL userinfo, sensitive
query or mapping keys, registered secret values, or vendor token shapes. Use
:func:`strip_credentials` to record a URL that needed a key.
"""

from __future__ import annotations

import abc
import math
import re
import urllib.parse
from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import PurePosixPath
from types import MappingProxyType
from typing import Annotated, Any, ClassVar, Final, Literal, Self, final

from pydantic import (
    AfterValidator,
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    PlainSerializer,
    model_validator,
)

from mjepa_harness.log import REDACTOR, SENSITIVE_KEY_PATTERN, TOKEN_SHAPES
from mjepa_harness.net import require_network
from mjepa_harness.paths import DataLayout, check_data_dir_safe
from mjepa_harness.settings import Settings

BYTES_PER_GB: Final = 1_000_000_000
"""Decimal gigabytes, as used by --max-gb and every printed estimate."""

PIT_COLUMNS: Final[tuple[str, ...]] = ("event_time", "knowledge_time", "source", "ingested_at")
"""Columns every normalized table must carry (plus ``asset_id`` where relevant)."""

ESTIMATE_OVERRUN_FACTOR: Final = 1.5
"""With --yes and fully sized plans, downloads may exceed the plan by at most this factor."""

_SENSITIVE_KEY: Final = re.compile(rf"(?i)^(?:[a-z0-9_-]*[_-])?(?:{SENSITIVE_KEY_PATTERN})$")
_PAGINATION_KEYS: Final = frozenset(
    {"cursor", "page_token", "next_page_token", "continuation_token", "pagetoken", "nexttoken"}
)
_WINDOWS_DRIVE: Final = re.compile(r"^[A-Za-z]:")


# --------------------------------------------------------------------------- credentials


def is_sensitive_key(key: str) -> bool:
    """A query-parameter or mapping key that names a credential (pagination keys excepted)."""
    return key.lower() not in _PAGINATION_KEYS and bool(_SENSITIVE_KEY.match(key))


def carries_credentials(text: str) -> bool:
    """True if ``text`` contains URL userinfo, a credential query parameter, a registered
    secret value or a vendor token shape. Free text such as "token bucket" is fine."""
    if REDACTOR.contains_registered(text) or TOKEN_SHAPES.search(text):
        return True
    if "://" in text or "?" in text:
        parts = urllib.parse.urlsplit(text)
        if parts.username or parts.password:
            return True
        pairs = urllib.parse.parse_qsl(parts.query, keep_blank_values=True)
        if any(is_sensitive_key(key) for key, _ in pairs):
            return True
    return False


def strip_credentials(url: str) -> str:
    """``url`` without userinfo and without credential query parameters."""
    parts = urllib.parse.urlsplit(url)
    netloc = parts.hostname or ""
    if parts.port is not None:
        netloc = f"{netloc}:{parts.port}"
    query = [
        (key, value)
        for key, value in urllib.parse.parse_qsl(parts.query, keep_blank_values=True)
        if not is_sensitive_key(key)
    ]
    return urllib.parse.urlunsplit(
        (parts.scheme, netloc, parts.path, urllib.parse.urlencode(query), parts.fragment)
    )


def _string_leaves(value: Any) -> Iterator[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, Mapping):
        for item in value.values():
            yield from _string_leaves(item)
    elif isinstance(value, list | tuple):
        for item in value:
            yield from _string_leaves(item)


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

JsonScalar = str | int | float | bool | None


def _check_keys(mapping: Mapping[str, Any]) -> None:
    for key in mapping:
        if is_sensitive_key(key):
            raise ValueError(f"mapping key {key!r} names a credential; never record credentials")


def _freeze_request(value: Mapping[str, Any]) -> Mapping[str, Any]:
    _check_keys(value)
    return MappingProxyType(
        {
            key: tuple(item) if isinstance(item, list | tuple) else item
            for key, item in value.items()
        }
    )


def _freeze_attributes(value: Mapping[str, str]) -> Mapping[str, str]:
    _check_keys(value)
    return MappingProxyType(dict(value))


RequestMapping = Annotated[
    Mapping[str, JsonScalar | tuple[JsonScalar, ...] | list[JsonScalar]],
    AfterValidator(_freeze_request),
    PlainSerializer(lambda v: {k: list(x) if isinstance(x, tuple) else x for k, x in v.items()}),
]
"""Immutable request parameters (JSON scalars or lists of them); no credential keys."""

AttributeMapping = Annotated[
    Mapping[str, str],
    AfterValidator(_freeze_attributes),
    PlainSerializer(lambda v: dict(v)),
]


class _Frozen(BaseModel):
    """Frozen, extra-forbidding, and credential-free in every string it holds."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    @model_validator(mode="after")
    def _no_credentials_anywhere(self) -> Self:
        for text in _string_leaves(self.model_dump(mode="json")):
            if carries_credentials(text):
                raise ValueError(
                    "a field carries credentials (URL userinfo, a credential query parameter, "
                    "a registered secret or a token); record it with strip_credentials()"
                )
        return self


# --------------------------------------------------------------------------- models


class PlannedFile(_Frozen):
    remote_uri: str
    relative_path: RelPath = Field(description="destination under raw/<source>/")
    expected_bytes: int | None = Field(default=None, ge=0, description="exact, from a listing")
    estimated_bytes: int | None = Field(
        default=None, gt=0, description="heuristic estimate; must be positive"
    )
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
    source_url: str = Field(description="as recorded by strip_credentials()")
    fetched_at: UtcDatetime
    remote_version: str | None = None
    http_etag: str | None = None
    origin_fetch_id: str | None = Field(
        default=None, description="fetch that downloaded the file, if not this one"
    )
    attributes: AttributeMapping = Field(
        default_factory=dict,
        validate_default=True,
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
    planned_bytes: int | None = Field(default=None, ge=0)
    downloaded_bytes: int = Field(default=0, ge=0)
    entries: tuple[ManifestEntry, ...]

    @model_validator(mode="after")
    def _times_ordered(self) -> Self:
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
    """A download exceeds its budget (or its size is unknown) without --yes."""


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


class ByteBudget:
    """Counts bytes actually downloaded; the landing-zone writer calls :meth:`consume`.

    Without --yes the cap is ``max_gb``. With --yes and a fully sized plan, the cap is
    :data:`ESTIMATE_OVERRUN_FACTOR` x the plan, so a wildly wrong estimate cannot turn
    an approved 1 GB into 100 GB. With --yes and unknown sizes there is no cap: the
    user accepted that explicitly.
    """

    def __init__(self, source: str, limit_bytes: int | None) -> None:
        self.source = source
        self.limit_bytes = limit_bytes
        self.used_bytes = 0

    def consume(self, n_bytes: int) -> None:
        if n_bytes < 0:
            raise ValueError("n_bytes must be non-negative")
        self.used_bytes += n_bytes
        if self.limit_bytes is not None and self.used_bytes > self.limit_bytes:
            raise DownloadRefusedError(
                f"[{self.source}] downloaded {self.used_bytes} B, above the approved budget of "
                f"{self.limit_bytes} B; aborting (the plan's size estimate was wrong)"
            )

    @classmethod
    def for_plan(cls, plan: FetchPlan, *, max_gb: float, yes: bool) -> ByteBudget:
        if not yes:
            return cls(plan.source, int(max_gb * BYTES_PER_GB))
        if plan.unknown_size_count:
            return cls(plan.source, None)
        return cls(plan.source, math.ceil(plan.known_bytes * ESTIMATE_OVERRUN_FACTOR))


# --------------------------------------------------------------------------- adapter


@dataclass(frozen=True)
class SourceContext:
    """What an adapter may use: settings (incl. credentials), the data layout, provenance."""

    settings: Settings
    layout: DataLayout
    code_version: CodeVersionRecord


_APPROVAL: Final = object()


@dataclass(frozen=True)
class ApprovedPlan:
    """A plan that passed every guard. Only :meth:`SourceAdapter.fetch` can create one."""

    plan: FetchPlan
    max_gb: float
    yes: bool
    approved_at: datetime
    budget: ByteBudget
    _token: object = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self._token is not _APPROVAL:
            raise TypeError("ApprovedPlan is created only by SourceAdapter.fetch()")


class SourceAdapter(abc.ABC):
    """Base class for every data source (M1 implements one subclass per source)."""

    name: ClassVar[str]
    required_env: ClassVar[tuple[str, ...]] = ()
    plan_requires_network: ClassVar[bool] = True

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        for method in ("plan", "fetch"):
            if method in cls.__dict__:
                raise TypeError(
                    f"{cls.__name__} must not override SourceAdapter.{method}(); "
                    f"implement _{'plan' if method == 'plan' else 'download'}() instead"
                )

    def __init__(self, context: SourceContext) -> None:
        self.context = context

    @final
    def plan(self, **request: JsonScalar | list[JsonScalar]) -> FetchPlan:
        """Describe what would be fetched (never downloads data)."""
        if self.plan_requires_network:
            require_network(f"planning {self.name}")
        plan = self._plan(**request)
        if plan.source != self.name:
            raise ValueError(f"{type(self).__name__}._plan returned a plan for {plan.source!r}")
        return plan

    @final
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
        approved = ApprovedPlan(
            plan=checked,
            max_gb=max_gb,
            yes=yes,
            approved_at=datetime.now(UTC),
            budget=ByteBudget.for_plan(checked, max_gb=max_gb, yes=yes),
            _token=_APPROVAL,
        )
        return self._download(approved)

    @abc.abstractmethod
    def _plan(self, **request: JsonScalar | list[JsonScalar]) -> FetchPlan:
        """Build the plan. Must not download data."""

    @abc.abstractmethod
    def _download(self, approved: ApprovedPlan) -> Manifest:
        """Download ``approved.plan`` into the write-once landing zone; write its manifest.

        Call ``approved.budget.consume(n)`` for every chunk written.
        """

    @abc.abstractmethod
    def normalize(self, manifest: Manifest) -> Sequence[NormalizedTable]:
        """Turn raw files into point-in-time Parquet tables."""
