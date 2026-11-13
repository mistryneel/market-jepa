"""Runtime settings, read from environment variables only.

Credentials never come from YAML, code or files read by the harness. To keep a
local ``.env`` file, load it into the environment yourself, for example with
``uv run --env-file .env mjepa doctor``; ``.env`` is git-ignored.

Secret values are wrapped in :class:`pydantic.SecretStr` (masked ``repr``) and
are registered with the log redactor by :func:`mjepa_harness.log.configure_logging`.
"""

from __future__ import annotations

import os
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final, Literal

from pydantic import SecretStr

DEFAULT_DATA_DIR: Final = "~/data/market-jepa"
"""Default for ``$MJ_DATA_DIR``. Must stay outside the repository."""

CREDENTIAL_ENV_VARS: Final[tuple[str, ...]] = (
    "MASSIVE_API_KEY",
    "MASSIVE_S3_ACCESS_KEY_ID",
    "MASSIVE_S3_SECRET_ACCESS_KEY",
    "FRED_API_KEY",
    "SEC_USER_AGENT",
    "HF_TOKEN",
)
"""Every credential the harness may use. All are optional at start-up; an adapter
that needs one calls :meth:`Credentials.require` and fails with a clear message."""

CREDENTIAL_PURPOSE: Final[Mapping[str, str]] = {
    "MASSIVE_API_KEY": "Massive REST API (reference data, corporate actions)",
    "MASSIVE_S3_ACCESS_KEY_ID": "Massive flat files (S3-compatible)",
    "MASSIVE_S3_SECRET_ACCESS_KEY": "Massive flat files (S3-compatible)",
    "FRED_API_KEY": "FRED / ALFRED API",
    "SEC_USER_AGENT": "SEC EDGAR fair-access User-Agent ('Name contact@example.org')",
    "HF_TOKEN": "Hugging Face Hub (optional for public datasets; raises rate limits)",
}

LogFormat = Literal["text", "json"]
_LOG_LEVELS: Final = frozenset({"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"})


class MissingCredentialError(RuntimeError):
    """A data source needs a credential that is not set in the environment."""

    def __init__(self, name: str, purpose: str) -> None:
        super().__init__(
            f"Environment variable {name} is not set; it is needed for {purpose}. "
            "Set it in your shell or a git-ignored .env file loaded with "
            "`uv run --env-file .env ...`. See docs/harness/HUMAN_TODO.md."
        )
        self.name = name


@dataclass(frozen=True)
class Credentials:
    """Credentials present in the environment. Values are never printed."""

    _values: Mapping[str, SecretStr] = field(default_factory=dict, repr=False)

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> Credentials:
        source = os.environ if env is None else env
        values: dict[str, SecretStr] = {}
        for name in CREDENTIAL_ENV_VARS:
            raw = source.get(name, "").strip()
            if raw:
                values[name] = SecretStr(raw)
        return cls(values)

    def is_set(self, name: str) -> bool:
        self._check_known(name)
        return name in self._values

    def get(self, name: str) -> SecretStr | None:
        self._check_known(name)
        return self._values.get(name)

    def require(self, name: str, purpose: str | None = None) -> str:
        """Return the raw secret or raise :class:`MissingCredentialError`.

        Only call this at the point of use (building a request); never log the result.
        """
        value = self.get(name)
        if value is None:
            raise MissingCredentialError(name, purpose or CREDENTIAL_PURPOSE[name])
        return value.get_secret_value()

    def presence(self) -> dict[str, bool]:
        """Map of credential name -> whether it is set. Safe to print."""
        return {name: name in self._values for name in CREDENTIAL_ENV_VARS}

    def secret_values(self) -> tuple[str, ...]:
        """Raw values, for registration with the log redactor only."""
        return tuple(v.get_secret_value() for v in self._values.values())

    def __repr__(self) -> str:
        present = sorted(self._values)
        return f"Credentials(present={present})"

    @staticmethod
    def _check_known(name: str) -> None:
        if name not in CREDENTIAL_ENV_VARS:
            raise KeyError(f"unknown credential {name!r}; known: {', '.join(CREDENTIAL_ENV_VARS)}")


_VAR_RE: Final = re.compile(r"\$(?:\{(\w+)\}|(\w+))")


def _env_str(env: Mapping[str, str], name: str) -> str | None:
    raw = env.get(name, "").strip()
    return raw or None


def _expand_path(raw: str, env: Mapping[str, str]) -> Path:
    """Expand ``$VAR``/``${VAR}`` and a leading ``~`` using ``env``; return an absolute path.

    Unknown variables are an error (a silently unexpanded ``$VAR`` directory would put
    data somewhere surprising).
    """

    def _sub(match: re.Match[str]) -> str:
        name = match.group(1) or match.group(2)
        if name not in env:
            raise ValueError(f"path {raw!r} references unset environment variable ${name}")
        return env[name]

    expanded = _VAR_RE.sub(_sub, raw)
    if expanded == "~" or expanded.startswith("~/"):
        home = env.get("HOME") or str(Path.home())
        expanded = home + expanded[1:]
    return Path(expanded).absolute()


def resolve_data_dir(
    env: Mapping[str, str] | None = None, override: str | Path | None = None
) -> Path:
    """Resolve the data root: explicit override > ``$MJ_DATA_DIR`` > default.

    ``~`` and ``$VARS`` are expanded; the result is absolute. An empty variable counts
    as unset.
    """
    source = os.environ if env is None else env
    raw = str(override) if override is not None else _env_str(source, "MJ_DATA_DIR")
    return _expand_path(raw if raw is not None else DEFAULT_DATA_DIR, source)


def resolve_config_dir(
    env: Mapping[str, str] | None = None, override: str | Path | None = None
) -> Path:
    """Resolve the YAML config directory: override > ``$MJ_CONFIG_DIR`` > repo ``configs/``.

    The repo location is found relative to this file (src layout, editable install as
    created by ``uv sync``), falling back to ``./configs`` in the working directory.
    """
    source = os.environ if env is None else env
    raw = str(override) if override is not None else _env_str(source, "MJ_CONFIG_DIR")
    if raw is not None:
        return _expand_path(raw, source)
    repo_configs = Path(__file__).resolve().parents[2] / "configs"
    if repo_configs.is_dir():
        return repo_configs
    return (Path.cwd() / "configs").absolute()


def resolve_log_level(env: Mapping[str, str] | None = None, override: str | None = None) -> str:
    source = os.environ if env is None else env
    level = (override or _env_str(source, "MJ_LOG_LEVEL") or "INFO").upper()
    if level not in _LOG_LEVELS:
        raise ValueError(f"invalid log level {level!r}; choose from {sorted(_LOG_LEVELS)}")
    return level


def resolve_log_format(
    env: Mapping[str, str] | None = None, override: str | None = None
) -> LogFormat:
    source = os.environ if env is None else env
    fmt = (override or _env_str(source, "MJ_LOG_FORMAT") or "text").lower()
    if fmt == "text":
        return "text"
    if fmt == "json":
        return "json"
    raise ValueError(f"invalid log format {fmt!r}; choose 'text' or 'json'")


@dataclass(frozen=True)
class Settings:
    """Everything the harness reads from the environment, resolved once per process."""

    data_dir: Path
    config_dir: Path
    log_level: str
    log_format: LogFormat
    credentials: Credentials

    @classmethod
    def from_env(
        cls,
        env: Mapping[str, str] | None = None,
        *,
        data_dir: str | Path | None = None,
        config_dir: str | Path | None = None,
        log_level: str | None = None,
        log_format: str | None = None,
    ) -> Settings:
        source = os.environ if env is None else env
        return cls(
            data_dir=resolve_data_dir(source, data_dir),
            config_dir=resolve_config_dir(source, config_dir),
            log_level=resolve_log_level(source, log_level),
            log_format=resolve_log_format(source, log_format),
            credentials=Credentials.from_env(source),
        )
