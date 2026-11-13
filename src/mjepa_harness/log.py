"""Logging with secret redaction.

Every handler installed by :func:`configure_logging` formats records through a
:class:`RedactingFormatter`, which scrubs (a) the exact values of credentials found in
the environment (plus their URL-encoded forms) and (b) generic secret shapes such as
``apiKey=...`` query parameters, ``Authorization: Bearer ...`` headers, Hugging Face
tokens and AWS access-key ids. The scrub runs on the *final* formatted text, so it also
covers exception tracebacks and stack info.

Timestamps are UTC (ISO 8601 with ``Z``) to match the point-in-time store.
"""

from __future__ import annotations

import json
import logging
import re
import sys
import threading
import urllib.parse
from collections.abc import Iterable
from datetime import UTC, datetime
from typing import IO, Final, override

from mjepa_harness.settings import LogFormat

REDACTED: Final = "***REDACTED***"
MIN_SECRET_LENGTH: Final = 6
"""Registered values shorter than this are ignored: redacting e.g. ``"a"`` would
destroy every log line, and real credentials are much longer."""

_SENSITIVE_KEY = (
    r"api[_-]?key|apikey|access[_-]?key(?:[_-]?id)?|secret(?:[_-]?access)?(?:[_-]?key)?"
    r"|client[_-]?secret|token|access[_-]?token|refresh[_-]?token|auth[_-]?token|password|passwd"
    r"|signature|x-amz-signature|x-amz-credential|x-amz-security-token|authorization"
)
# key=value / key: value (query strings, headers, kwargs reprs, JSON-ish) -> keep key, drop value.
_KEY_VALUE_RE: Final = re.compile(
    rf"(?i)(?<![A-Za-z0-9_])({_SENSITIVE_KEY})([\"']?\s*[=:]\s*[\"']?)([^\s&\"',;}}\]]+)"
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
        secrets = self._secrets  # snapshot; frozenset swap is atomic
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
"""Process-wide redactor used by the CLI's handlers."""


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
        if record.exc_info:
            payload["exc"] = self._redactor.redact(self.formatException(record.exc_info))
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
    secrets: Iterable[str] = (),
    redactor: SecretRedactor = REDACTOR,
    stream: IO[str] | None = None,
) -> logging.Handler:
    """Install (idempotently) one redacting stderr handler on the root logger.

    ``secrets`` are registered with ``redactor`` first, so pass
    ``settings.credentials.secret_values()``.
    """
    redactor.register(secrets)
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
