"""YAML configuration: strict schemas, safe loading and fingerprints.

Five files live in ``configs/``: ``sources``, ``universe``, ``splits``, ``events`` and
``endpoint``. They hold no secrets. Each is validated by a frozen pydantic model with
``extra="forbid"`` (a typo is an error, not a silently ignored key) and strict types
(no ``"500"`` -> ``500`` coercion). The YAML loader rejects duplicate keys.

``endpoint.yaml`` is the pre-registered primary endpoint. Its fingerprint (SHA-256 of
the canonical JSON of the *parsed* model, so comments and formatting do not matter) is
pinned in ``tests/test_preregistration.py``.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Annotated, Any, Final, Literal, Self

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

# --------------------------------------------------------------------------- loading


class ConfigError(ValueError):
    """A config file is missing, malformed or inconsistent."""


class _UniqueKeyLoader(yaml.SafeLoader):
    """SafeLoader that rejects duplicate mapping keys (PyYAML silently keeps the last)."""


def _construct_unique_mapping(
    loader: _UniqueKeyLoader, node: yaml.MappingNode, deep: bool = False
) -> dict[Any, Any]:
    loader.flatten_mapping(node)
    seen: set[Any] = set()
    for key_node, _value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in seen:
            line = key_node.start_mark.line + 1
            raise ConfigError(f"duplicate key {key!r} at line {line}")
        seen.add(key)
    return loader.construct_mapping(node, deep=deep)


_UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_unique_mapping
)


def _freeze(obj: Any) -> Any:
    """YAML sequences become tuples, matching the frozen models' ``tuple[...]`` fields."""
    if isinstance(obj, dict):
        return {key: _freeze(value) for key, value in obj.items()}
    if isinstance(obj, list):
        return tuple(_freeze(item) for item in obj)
    return obj


def load_yaml(path: Path) -> Any:
    """Parse one YAML file safely (no arbitrary tags, no duplicate keys); lists -> tuples."""
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ConfigError(f"config file not found: {path}") from exc
    try:
        return _freeze(yaml.load(text, Loader=_UniqueKeyLoader))  # noqa: S506 - SafeLoader subclass
    except ConfigError as exc:
        raise ConfigError(f"{path}: {exc}") from exc
    except yaml.YAMLError as exc:
        raise ConfigError(f"{path}: invalid YAML: {exc}") from exc


# --------------------------------------------------------------------------- base model


class StrictModel(BaseModel):
    """Frozen, typo-proof, coercion-free base for every config model."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


PositiveInt = Annotated[int, Field(gt=0)]
NonNegativeInt = Annotated[int, Field(ge=0)]
PositiveFloat = Annotated[float, Field(gt=0)]
Month = Annotated[str, Field(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")]
EventType = Literal["FOMC", "CPI", "EMPLOYMENT", "EARNINGS"]


# --------------------------------------------------------------------------- universe


class UniverseSpec(StrictModel):
    """Monthly point-in-time universe (configs/universe.yaml; embedded in the endpoint)."""

    top_n: PositiveInt
    ranking: Literal["prior_month_dollar_volume"]
    min_price_usd: PositiveFloat
    rebuild: Literal["monthly"]
    membership_knowledge: Literal["before_month_start"] = Field(
        description="membership for month m uses only data knowable before m starts"
    )


# --------------------------------------------------------------------------- splits


class Period(StrictModel):
    """Inclusive date range of US trading dates. ``start=None`` means earliest available."""

    start: date | None
    end: date

    @model_validator(mode="after")
    def _ordered(self) -> Self:
        if self.start is not None and self.start > self.end:
            raise ValueError(f"period start {self.start} is after end {self.end}")
        return self

    def contains(self, day: date) -> bool:
        return (self.start is None or self.start <= day) and day <= self.end


class Periods(StrictModel):
    train: Period
    tune: Period
    locked_test: Period

    @model_validator(mode="after")
    def _contiguous(self) -> Self:
        if self.tune.start != self.train.end + timedelta(days=1):
            raise ValueError("tune must start the day after train ends")
        if self.locked_test.start != self.tune.end + timedelta(days=1):
            raise ValueError("locked_test must start the day after tune ends")
        return self


class SplitsConfig(StrictModel):
    periods: Periods
    label_horizon_trading_days: PositiveInt
    purge_trading_days: NonNegativeInt
    embargo_trading_days: NonNegativeInt

    @model_validator(mode="after")
    def _purge_covers_horizon(self) -> Self:
        horizon = self.label_horizon_trading_days
        if self.purge_trading_days < horizon or self.embargo_trading_days < horizon:
            raise ValueError(
                f"purge ({self.purge_trading_days}) and embargo ({self.embargo_trading_days}) "
                f"must be >= the label horizon ({horizon} trading days)"
            )
        return self


# --------------------------------------------------------------------------- events


class EventTypeSpec(StrictModel):
    description: str
    calendar: str | None = Field(
        description="repo-relative CSV under data_ref/, or null when derived from another source"
    )


class EventsConfig(StrictModel):
    timezone: Literal["America/New_York"]
    types: dict[EventType, EventTypeSpec]


# --------------------------------------------------------------------------- endpoint


class Horizon(StrictModel):
    unit: Literal["trading_day"]
    first: PositiveInt
    last: PositiveInt

    @model_validator(mode="after")
    def _ordered(self) -> Self:
        if self.first > self.last:
            raise ValueError("horizon.first must be <= horizon.last")
        return self

    @property
    def length(self) -> int:
        return self.last - self.first + 1


class EventSelection(StrictModel):
    types: tuple[EventType, ...]
    scheduled_only: bool


class EndpointPeriod(StrictModel):
    name: Literal["locked_test"]
    start: date
    end: date


class Comparison(StrictModel):
    pairing: Literal["by_event"]
    test: Literal["block_bootstrap"]
    block_unit: Literal["calendar_month"]


class EndpointDefinitions(StrictModel):
    """Operational definitions the pre-registered sentence leaves open.

    Proposed at M0 and pending human confirmation (see DECISIONS.md); they are part of
    the fingerprint, so changing them is a visible, deliberate act.
    """

    forecast_origin: Literal["last_close_strictly_before_announcement"]
    day_1: Literal["first_session_closing_after_announcement"]
    returns: Literal["daily_close_to_close_total_return"]
    realized_covariance: Literal["sum_of_outer_products_of_daily_returns_no_demeaning"]
    stein_singular_target: Literal["drop_forecast_independent_logdet_term"]


class EndpointConfig(StrictModel):
    """The pre-registered primary endpoint (configs/endpoint.yaml)."""

    id: str
    version: PositiveInt
    status: Literal["draft", "locked"]
    statement: str
    metric: Literal["stein_loss"]
    target: Literal["realized_covariance"]
    horizon: Horizon
    universe: UniverseSpec
    events: EventSelection
    period: EndpointPeriod
    aggregation: Literal["mean_over_events"]
    comparison: Comparison
    definitions: EndpointDefinitions


# --------------------------------------------------------------------------- sources


class DownloadPolicy(StrictModel):
    max_gb_default: PositiveFloat
    max_retries: NonNegativeInt
    backoff_initial_seconds: PositiveFloat
    backoff_max_seconds: PositiveFloat


class FredSourceConfig(StrictModel):
    series: tuple[str, ...]
    use_alfred_vintages: bool


class MonthRange(StrictModel):
    first: Month
    last: Month


class Market1TSourceConfig(StrictModel):
    repos: dict[Literal["sparse", "dense", "daystore"], str]
    default_layout: Literal["sparse", "dense", "daystore"]
    test_month: Month
    coverage: MonthRange


class MassiveSourceConfig(StrictModel):
    flat_file_products: tuple[str, ...]
    optional_flat_file_products: tuple[str, ...]
    include_delisted: bool


class EdgarSourceConfig(StrictModel):
    forms: tuple[str, ...]
    earnings_8k_item: str
    max_requests_per_second: Annotated[float, Field(gt=0, le=10)]


class CryptoSourceConfig(StrictModel):
    top_n: PositiveInt
    bars: tuple[Literal["1d", "1h"], ...]
    ranking: Literal["trailing_dollar_volume"]
    exclude_stablecoins_and_wrapped: bool


class SourcesConfig(StrictModel):
    download: DownloadPolicy
    fred: FredSourceConfig
    market1t: Market1TSourceConfig
    massive: MassiveSourceConfig
    edgar: EdgarSourceConfig
    crypto: CryptoSourceConfig


# --------------------------------------------------------------------------- registry

CONFIG_MODELS: Final[dict[str, type[StrictModel]]] = {
    "sources": SourcesConfig,
    "universe": UniverseSpec,
    "splits": SplitsConfig,
    "events": EventsConfig,
    "endpoint": EndpointConfig,
}


def load_config[M: StrictModel](path: Path, model: type[M]) -> M:
    data = load_yaml(path)
    if not isinstance(data, dict):
        raise ConfigError(f"{path}: top level must be a mapping, got {type(data).__name__}")
    try:
        return model.model_validate(data)
    except ValidationError as exc:
        raise ConfigError(f"{path}: {exc}") from exc


def canonical_json(model: BaseModel) -> str:
    """Deterministic JSON: sorted keys, no whitespace, ISO dates."""
    return json.dumps(
        model.model_dump(mode="json"), sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )


def fingerprint(model: BaseModel) -> str:
    digest = hashlib.sha256(canonical_json(model).encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


@dataclass(frozen=True)
class HarnessConfig:
    config_dir: Path
    sources: SourcesConfig
    universe: UniverseSpec
    splits: SplitsConfig
    events: EventsConfig
    endpoint: EndpointConfig

    def models(self) -> dict[str, StrictModel]:
        return {
            "sources": self.sources,
            "universe": self.universe,
            "splits": self.splits,
            "events": self.events,
            "endpoint": self.endpoint,
        }

    def fingerprints(self) -> dict[str, str]:
        return {name: fingerprint(model) for name, model in self.models().items()}


def _cross_check(cfg: HarnessConfig) -> None:
    endpoint, splits = cfg.endpoint, cfg.splits
    problems: list[str] = []
    if endpoint.universe != cfg.universe:
        problems.append("endpoint.universe differs from universe.yaml")
    locked = splits.periods.locked_test
    if (endpoint.period.start, endpoint.period.end) != (locked.start, locked.end):
        problems.append("endpoint.period differs from splits.periods.locked_test")
    if endpoint.horizon.length != splits.label_horizon_trading_days:
        problems.append("endpoint horizon length differs from splits.label_horizon_trading_days")
    missing = [t for t in endpoint.events.types if t not in cfg.events.types]
    if missing:
        problems.append(f"endpoint event types not defined in events.yaml: {missing}")
    if problems:
        raise ConfigError("inconsistent configs: " + "; ".join(problems))


def load_harness_config(config_dir: Path) -> HarnessConfig:
    """Load and cross-validate all five config files from ``config_dir``."""
    if not config_dir.is_dir():
        raise ConfigError(f"config directory not found: {config_dir}")
    cfg = HarnessConfig(
        config_dir=config_dir,
        sources=load_config(config_dir / "sources.yaml", SourcesConfig),
        universe=load_config(config_dir / "universe.yaml", UniverseSpec),
        splits=load_config(config_dir / "splits.yaml", SplitsConfig),
        events=load_config(config_dir / "events.yaml", EventsConfig),
        endpoint=load_config(config_dir / "endpoint.yaml", EndpointConfig),
    )
    _cross_check(cfg)
    return cfg
