"""Logging with secret redaction, applied in two independent layers.

1. **Record level.** :func:`install_record_redaction` wraps the global LogRecord factory,
   so every record is scrubbed when it is *created*. That covers every handler,
   including pytest's captured-log report, ``logging.lastResort`` and handlers added by
   other code. The factory renders the message, drops the raw ``args`` (a call with
   mismatched arguments can no longer make logging print them), and pre-renders and
   scrubs exception text and stack info. (``extra=`` fields are attached by
   ``Logger.makeRecord`` *after* the factory runs, so only layer 2 sees them: never
   put secrets in ``extra``, and give any handler that prints extras a
   :class:`RedactingFormatter`.)
2. **Output level.** The handler installed by :func:`configure_logging` scrubs the
   final formatted text again.

Both layers remove (a) the exact values of registered credentials, plus their
URL-encoded forms, and (b) generic secret shapes: ``api_key=...``-style assignments,
``Authorization: Bearer ...`` headers, Hugging Face tokens and AWS access-key ids.

Redaction is defence in depth. Code must still never put credentials into messages,
exceptions or URLs it logs. Timestamps are UTC, to match the point-in-time store.
"""

from __future__ import annotations

import json
import logging
import re
import sys
import threading
import urllib.parse
from collections.abc import Callable, Iterable
from datetime import UTC, datetime
from typing import IO, Any, Final, override

from mjepa_harness.settings import Credentials, LogFormat

REDACTED: Final = "***REDACTED***"
MIN_SECRET_LENGTH: Final = 6
"""Registered values shorter than this are ignored: redacting e.g. ``"a"`` would
destroy every log line, and real credentials are much longer."""

SENSITIVE_KEY_PATTERN: Final = (
    r"api[_-]?key|apikey|access[_-]?key(?:[_-]?id)?|secret(?:[_-]?access)?(?:[_-]?key)?"
    r"|client[_-]?secret|private[_-]?key|credentials?|token|access[_-]?token|refresh[_-]?token"
    r"|auth[_-]?token|password|passwd|signature|x-amz-signature|x-amz-credential"
    r"|x-amz-security-token|authorization"
)
"""Key names whose values are secrets. Shared with the repository hygiene scan."""

# key=value, key: value, "key", "value" (query strings, headers, kwargs and tuple reprs,
# JSON) -> keep the key, drop the value. The look-behind excludes letters and digits but
# not "_", so FRED_API_KEY= and aws_secret_access_key= are caught.
_KEY_VALUE_RE: Final = re.compile(
    rf"(?i)(?<![A-Za-z0-9])({SENSITIVE_KEY_PATTERN})"
    r"([\"']?\s*[=:]\s*[\"']?|[\"']\s*,\s*[\"'])"
    r"([^\s&\"',;}\])]+)"
)
_AUTH_SCHEME_RE: Final = re.compile(r"(?i)\b(Bearer|Basic|Token)\s+[A-Za-z0-9\-._~+/]{6,}=*")
_TOKEN_SHAPES: Final = re.compile(
    r"\bhf_[A-Za-z0-9]{20,}\b"  # Hugging Face user access tokens
    r"|\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"  # AWS-style access key ids
)


class SecretRedactor:
    """Thread-safe set of secret strings to scrub from log output."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._secrets: frozenset[str] = frozenset()

    def register(self, values: Iterable[str]) -> None:
        additions: set[str] = set()
        for value in values:
            if len(value) < MIN_SECRET_LENGTH:
                continue
            additions.add(value)
            for encoded in (urllib.parse.quote(value, safe=""), urllib.parse.quote_plus(value)):
                if encoded != value:
                    additions.add(encoded)
        with self._lock:
            self._secrets = self._secrets | additions

    def clear(self) -> None:
        with self._lock:
            self._secrets = frozenset()

    def redact(self, text: str) -> str:
        secrets = self._secrets  # snapshot; the frozenset swap is atomic
        for secret in sorted(secrets, key=len, reverse=True):
            if secret in text:
                text = text.replace(secret, REDACTED)
        # Order matters: scheme-prefixed credentials ("Authorization: Bearer <token>") must
        # be scrubbed before the key=value rule, which would otherwise consume only the
        # scheme word and leave the token behind.
        text = _AUTH_SCHEME_RE.sub(lambda m: f"{m.group(1)} {REDACTED}", text)
        text = _TOKEN_SHAPES.sub(REDACTED, text)
        return _KEY_VALUE_RE.sub(lambda m: f"{m.group(1)}{m.group(2)}{REDACTED}", text)


REDACTOR: Final = SecretRedactor()
"""Process-wide redactor used by the record factory and the CLI's handler."""


def redact(text: str) -> str:
    """Scrub ``text`` with the process-wide redactor (for anything printed, not logged)."""
    return REDACTOR.redact(text)


# --------------------------------------------------------------------------- record level

_EXCEPTION_FORMATTER: Final = logging.Formatter()
_factory_lock = threading.Lock()
_base_factory: Callable[..., logging.LogRecord] | None = None
_factory_redactor: SecretRedactor = REDACTOR


def _redact_with_all(text: str) -> str:
    text = REDACTOR.redact(text)
    extra = _factory_redactor
    return text if extra is REDACTOR else extra.redact(text)


def _scrub_record(record: logging.LogRecord) -> None:
    try:
        message = record.getMessage()
    except Exception:  # mismatched %-arguments: never let logging print the raw args
        count = len(record.args) if isinstance(record.args, tuple) else 1
        message = f"{record.msg!s} [log formatting failed; {count} argument(s) suppressed]"
    record.msg = _redact_with_all(message)
    record.args = None
    if record.exc_info and not record.exc_text:
        record.exc_text = _redact_with_all(_EXCEPTION_FORMATTER.formatException(record.exc_info))
    if record.stack_info:
        record.stack_info = _redact_with_all(record.stack_info)


def _redacting_record_factory(*args: Any, **kwargs: Any) -> logging.LogRecord:
    base = _base_factory if _base_factory is not None else logging.LogRecord
    record = base(*args, **kwargs)
    _scrub_record(record)
    return record


def install_record_redaction(redactor: SecretRedactor = REDACTOR) -> None:
    """Scrub every LogRecord at creation time (idempotent).

    Records are always scrubbed with the process-wide :data:`REDACTOR`, plus
    ``redactor`` when a different one is given (the most recent call wins).
    """
    global _base_factory, _factory_redactor
    with _factory_lock:
        _factory_redactor = redactor
        if _base_factory is None:
            _base_factory = logging.getLogRecordFactory()
            logging.setLogRecordFactory(_redacting_record_factory)


# --------------------------------------------------------------------------- output level


class RedactingFormatter(logging.Formatter):
    """Wrap another formatter and scrub secrets from its complete output."""

    def __init__(self, inner: logging.Formatter, redactor: SecretRedactor) -> None:
        super().__init__()
        self._inner = inner
        self._redactor = redactor

    @override
    def format(self, record: logging.LogRecord) -> str:
        return self._redactor.redact(self._inner.format(record))


class UtcTextFormatter(logging.Formatter):
    """``2026-11-12T16:40:00.123Z LEVEL logger: message``."""

    def __init__(self) -> None:
        super().__init__("%(asctime)s %(levelname)-8s %(name)s: %(message)s")

    @override
    def formatTime(self, record: logging.LogRecord, datefmt: str | None = None) -> str:
        stamp = datetime.fromtimestamp(record.created, tz=UTC)
        return stamp.strftime("%Y-%m-%dT%H:%M:%S.") + f"{stamp.microsecond // 1000:03d}Z"


class JsonFormatter(logging.Formatter):
    """One JSON object per line; secret-bearing fields are redacted before encoding."""

    def __init__(self, redactor: SecretRedactor) -> None:
        super().__init__()
        self._redactor = redactor

    @override
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, str] = {
            "ts": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": self._redactor.redact(record.getMessage()),
        }
        if record.exc_info or record.exc_text:
            text = record.exc_text or self.formatException(record.exc_info)  # type: ignore[arg-type]
            payload["exc"] = self._redactor.redact(text)
        if record.stack_info:
            payload["stack"] = self._redactor.redact(self.formatStack(record.stack_info))
        return json.dumps(payload, ensure_ascii=False)


_HANDLER_NAME: Final = "mjepa-harness"
_NOISY_LOGGERS: Final = (
    "httpx",
    "httpcore",
    "urllib3",
    "botocore",
    "boto3",
    "s3transfer",
    "huggingface_hub",
    "filelock",
    "fsspec",
)
"""Third-party loggers that log full request URLs (possibly with keys) at INFO/DEBUG."""


def configure_logging(
    level: str = "INFO",
    fmt: LogFormat = "text",
    *,
    secrets: Iterable[str] | None = None,
    redactor: SecretRedactor = REDACTOR,
    stream: IO[str] | None = None,
) -> logging.Handler:
    """Install record-level redaction and (idempotently) one redacting stderr handler.

    ``secrets`` default to every credential currently in the environment.
    """
    redactor.register(Credentials.from_env().secret_values() if secrets is None else secrets)
    install_record_redaction(redactor)
    inner: logging.Formatter = JsonFormatter(redactor) if fmt == "json" else UtcTextFormatter()
    handler = logging.StreamHandler(stream if stream is not None else sys.stderr)
    handler.set_name(_HANDLER_NAME)
    handler.setFormatter(RedactingFormatter(inner, redactor))

    root = logging.getLogger()
    for existing in list(root.handlers):
        if existing.get_name() == _HANDLER_NAME:
            root.removeHandler(existing)
    root.addHandler(handler)
    numeric_level = logging.getLevelNamesMapping()[level]
    root.setLevel(numeric_level)
    quiet_level = max(logging.WARNING, numeric_level)
    for name in _NOISY_LOGGERS:
        logging.getLogger(name).setLevel(quiet_level)
    logging.captureWarnings(True)
    return handler
