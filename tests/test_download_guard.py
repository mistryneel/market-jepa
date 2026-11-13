from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from mjepa_harness.sources import ADAPTERS
from mjepa_harness.sources.base import (
    BYTES_PER_GB,
    PIT_COLUMNS,
    DownloadRefusedError,
    FetchPlan,
    Manifest,
    ManifestEntry,
    PlannedFile,
    check_download_budget,
    format_estimate,
)

GB = BYTES_PER_GB


def _plan(
    *sizes: int | None, present: tuple[bool, ...] = (), missing: tuple[str, ...] = ()
) -> FetchPlan:
    flags = present or (False,) * len(sizes)
    files = tuple(
        PlannedFile(
            remote_uri=f"https://example.org/f{i}",
            relative_path=f"f{i}",
            expected_bytes=size,
            already_present=flag,
        )
        for i, (size, flag) in enumerate(zip(sizes, flags, strict=True))
    )
    return FetchPlan(
        source="test",
        request={"month": "2020-03"},
        files=files,
        estimate_basis="unit test",
        estimated_seconds=120.0,
        missing_credentials=missing,
    )


def test_over_budget_is_refused_without_yes() -> None:
    plan = _plan(int(1.5 * GB), int(1.5 * GB))
    with pytest.raises(DownloadRefusedError, match=r"3\.000 GB, above the --max-gb limit of 2 GB"):
        check_download_budget(plan, max_gb=2.0, yes=False)
    check_download_budget(plan, max_gb=2.0, yes=True)
    check_download_budget(plan, max_gb=5.0, yes=False)


def test_unknown_size_requires_yes() -> None:
    plan = _plan(100, None)
    assert plan.bytes_to_fetch is None
    with pytest.raises(DownloadRefusedError, match="size is unknown"):
        check_download_budget(plan, max_gb=2.0, yes=False)
    check_download_budget(plan, max_gb=2.0, yes=True)


def test_already_present_files_cost_nothing() -> None:
    plan = _plan(3 * GB, 3 * GB, present=(True, True))
    assert plan.bytes_to_fetch == 0
    check_download_budget(plan, max_gb=2.0, yes=False)
    assert "0 file(s) to fetch (2 already present)" in format_estimate(plan)


def test_missing_credentials_refuse_even_with_yes() -> None:
    plan = _plan(10, missing=("FRED_API_KEY",))
    with pytest.raises(DownloadRefusedError, match="FRED_API_KEY"):
        check_download_budget(plan, max_gb=2.0, yes=True)


def test_estimate_mentions_files_size_and_time() -> None:
    text = format_estimate(_plan(GB // 2))
    assert "1 file(s) to fetch" in text
    assert "0.500 GB" in text
    assert "~2.0 min" in text


def test_non_positive_budget_is_rejected() -> None:
    with pytest.raises(ValueError, match="positive"):
        check_download_budget(_plan(1), max_gb=0, yes=False)


def _entry(**overrides: object) -> ManifestEntry:
    fields: dict[str, object] = {
        "relative_path": "x.csv",
        "size_bytes": 3,
        "sha256": "a" * 64,
        "source_url": "https://example.org/x.csv",
        "fetched_at": datetime(2026, 11, 12, tzinfo=UTC),
    }
    fields.update(overrides)
    return ManifestEntry.model_validate(fields)


def test_manifest_requires_timezone_aware_times_and_real_checksums() -> None:
    with pytest.raises(ValidationError):
        _entry(fetched_at=datetime(2026, 11, 12))  # noqa: DTZ001 - naive on purpose
    with pytest.raises(ValidationError):
        _entry(sha256="not-a-sha")
    start = datetime(2026, 11, 12, tzinfo=UTC)
    with pytest.raises(ValidationError, match="finished_at is before started_at"):
        Manifest(
            source="test",
            fetch_id="f1",
            request={},
            code_version="0.1.0+nogit",
            started_at=start,
            finished_at=start - timedelta(seconds=1),
            entries=(_entry(),),
        )


def test_pit_columns_match_the_brief() -> None:
    assert PIT_COLUMNS == ("event_time", "knowledge_time", "source", "ingested_at")


def test_no_adapters_registered_before_m1() -> None:
    assert ADAPTERS == {}
