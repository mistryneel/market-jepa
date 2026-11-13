from __future__ import annotations

import io
import json
import logging
import re
import urllib.parse

import pytest

from mjepa_harness import cli
from mjepa_harness.log import REDACTED, SecretRedactor, configure_logging

SECRET = "Zx9-very-secret-key-0042"
SPECIAL_SECRET = "p@ss/word+1=="


@pytest.fixture
def capture() -> tuple[logging.Logger, io.StringIO, SecretRedactor]:
    redactor = SecretRedactor()
    stream = io.StringIO()
    configure_logging(
        "DEBUG", "text", secrets=[SECRET, SPECIAL_SECRET], redactor=redactor, stream=stream
    )
    # The autouse fixture in conftest removes the handler after the test.
    return logging.getLogger("mjepa_harness.test"), stream, redactor


def test_registered_secret_is_redacted_in_message_and_args(
    capture: tuple[logging.Logger, io.StringIO, SecretRedactor],
) -> None:
    log, stream, _ = capture
    log.info("using key %s for %s", SECRET, "FRED")
    log.warning(f"inline {SECRET}")
    out = stream.getvalue()
    assert SECRET not in out
    assert out.count(REDACTED) == 2


def test_secret_in_exception_traceback_is_redacted(
    capture: tuple[logging.Logger, io.StringIO, SecretRedactor],
) -> None:
    log, stream, _ = capture
    try:
        raise ValueError(f"HTTP 403 for https://api.example.com/v3?apiKey={SECRET}")
    except ValueError:
        log.exception("request failed")
    out = stream.getvalue()
    assert "Traceback" in out
    assert SECRET not in out


def test_url_encoded_secret_is_redacted(
    capture: tuple[logging.Logger, io.StringIO, SecretRedactor],
) -> None:
    log, stream, _ = capture
    log.info("GET /x?q=%s", urllib.parse.quote(SPECIAL_SECRET, safe=""))
    assert urllib.parse.quote(SPECIAL_SECRET, safe="") not in stream.getvalue()


@pytest.mark.parametrize(
    ("line", "leaked"),
    [
        (
            "GET https://api.stlouisfed.org/fred/series/observations?series_id=DGS10&api_key=abcdef0123456789abcdef&file_type=json",
            "abcdef0123456789abcdef",
        ),
        (
            "headers={'Authorization': 'Bearer eyJhbGciOiJIUzI1NiJ9.payload.sig'}",
            "eyJhbGciOiJIUzI1NiJ9",
        ),
        (
            "token hf_EXAMPLEbCdEfGhIjKlMnOpQrStUvWxYz0 loaded",
            "hf_EXAMPLEbCdEfGhIjKlMnOpQrStUvWxYz0",
        ),
        ("aws key AKIAIOSFODNN7EXAMPLE in env", "AKIAIOSFODNN7EXAMPLE"),
        (
            "s3 url ...&X-Amz-Signature=0f1e2d3c4b5a69788796a5b4c3d2e1f0&...",
            "0f1e2d3c4b5a69788796a5b4c3d2e1f0",
        ),
        ('{"secret_access_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"}', "wJalrXUtnFEMI"),
    ],
)
def test_unregistered_secret_shapes_are_redacted(
    capture: tuple[logging.Logger, io.StringIO, SecretRedactor], line: str, leaked: str
) -> None:
    log, stream, _ = capture
    log.info(line)
    out = stream.getvalue()
    assert leaked not in out
    assert REDACTED in out


def test_harmless_text_is_untouched(
    capture: tuple[logging.Logger, io.StringIO, SecretRedactor],
) -> None:
    log, stream, _ = capture
    log.info("fetched series_id=DGS10 with 1234 tokens of context")
    assert "series_id=DGS10 with 1234 tokens of context" in stream.getvalue()


def test_short_values_are_not_registered() -> None:
    redactor = SecretRedactor()
    redactor.register(["abc"])
    assert redactor.redact("abcabc") == "abcabc"


def test_text_timestamps_are_utc(
    capture: tuple[logging.Logger, io.StringIO, SecretRedactor],
) -> None:
    log, stream, _ = capture
    log.info("hello")
    assert re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z INFO", stream.getvalue())


def test_json_format_is_redacted_and_valid() -> None:
    redactor = SecretRedactor()
    stream = io.StringIO()
    configure_logging("INFO", "json", secrets=[SECRET], redactor=redactor, stream=stream)
    log = logging.getLogger("mjepa_harness.test.json")
    try:
        raise RuntimeError(SECRET)
    except RuntimeError:
        log.exception("failed with %s", SECRET)
    record = json.loads(stream.getvalue().strip().splitlines()[-1])
    assert record["level"] == "ERROR"
    assert record["ts"].endswith("+00:00")
    assert SECRET not in json.dumps(record)


def test_configure_logging_is_idempotent_and_quiets_url_loggers() -> None:
    stream = io.StringIO()
    configure_logging("DEBUG", stream=stream, redactor=SecretRedactor())
    configure_logging("DEBUG", stream=stream, redactor=SecretRedactor())
    ours = [h for h in logging.getLogger().handlers if h.get_name() == "mjepa-harness"]
    assert len(ours) == 1
    assert logging.getLogger("httpx").level >= logging.WARNING


def test_cli_main_logs_unexpected_errors_without_secrets(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("MASSIVE_API_KEY", SECRET)

    def exploding_app() -> None:
        raise RuntimeError(
            f"HTTP 401 from https://api.massive.com/v3/reference/tickers?apiKey={SECRET}"
        )

    monkeypatch.setattr(cli, "app", exploding_app)
    with pytest.raises(SystemExit) as excinfo:
        cli.main()
    assert excinfo.value.code == 1
    captured = capsys.readouterr()
    assert "unexpected error" in captured.err
    assert SECRET not in captured.err
    assert SECRET not in captured.out
