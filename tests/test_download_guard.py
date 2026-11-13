"""The adapter contract: plan/manifest models, the download guard and the fetch template."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

import pytest
from pydantic import ValidationError

from mjepa_harness.net import NetworkDisabledError
from mjepa_harness.paths import DataLayout, UnsafeDataDirError
from mjepa_harness.settings import Settings
from mjepa_harness.sources import ADAPTERS
from mjepa_harness.sources.base import (
    BYTES_PER_GB,
    PIT_COLUMNS,
    ApprovedPlan,
    CodeVersionRecord,
    DownloadRefusedError,
    FetchPlan,
    JsonScalar,
    Manifest,
    ManifestEntry,
    NormalizedTable,
    PlannedFile,
    SourceAdapter,
    SourceContext,
    check_download_budget,
    format_estimate,
    strip_credentials,
)

CODE = CodeVersionRecord(package_version="0.1.0", git_sha=None, git_dirty=None)


def _plan(
    *sizes: int | None,
    present: tuple[bool, ...] = (),
    missing: tuple[str, ...] = (),
    source: str = "test",
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
        source=source,
        request={"month": "2020-03"},
        files=files,
        estimate_basis="unit test",
        estimated_seconds=120.0,
        missing_credentials=missing,
    )


# --------------------------------------------------------------------------- guard


def test_gigabytes_are_decimal() -> None:
    assert BYTES_PER_GB == 10**9


def test_budget_boundary_is_exact() -> None:
    check_download_budget(_plan(2_000_000_000), max_gb=2.0, yes=False)
    with pytest.raises(DownloadRefusedError, match=r"2\.000 GB, above the --max-gb limit of 2 GB"):
        check_download_budget(_plan(2_000_000_001), max_gb=2.0, yes=False)


def test_over_budget_needs_yes_or_a_higher_limit() -> None:
    plan = _plan(1_500_000_000, 1_500_000_000)
    with pytest.raises(DownloadRefusedError, match=r"3\.000 GB"):
        check_download_budget(plan, max_gb=2.0, yes=False)
    check_download_budget(plan, max_gb=2.0, yes=True)
    check_download_budget(plan, max_gb=5.0, yes=False)


def test_unknown_sizes_are_counted_and_still_need_yes() -> None:
    plan = _plan(1_000_000_000, None, None)
    assert plan.known_bytes == 1_000_000_000
    assert plan.unknown_size_count == 2
    with pytest.raises(
        DownloadRefusedError, match=r"2 file\(s\) have unknown size \(known part: 1\.000"
    ):
        check_download_budget(plan, max_gb=50.0, yes=False)
    check_download_budget(plan, max_gb=2.0, yes=True)
    assert "1.000 GB + 2 file(s) of unknown size" in format_estimate(plan)


def test_estimated_sizes_count_towards_the_budget() -> None:
    file = PlannedFile(
        remote_uri="https://example.org/fred", relative_path="fred.json", estimated_bytes=3 * 10**9
    )
    plan = FetchPlan(
        source="fred", request={}, files=(file,), estimate_basis="heuristic", estimated_seconds=1.0
    )
    with pytest.raises(DownloadRefusedError, match="above the --max-gb"):
        check_download_budget(plan, max_gb=2.0, yes=False)


def test_already_present_files_cost_nothing() -> None:
    plan = _plan(3 * 10**9, 3 * 10**9, present=(True, True))
    assert plan.known_bytes == 0
    check_download_budget(plan, max_gb=2.0, yes=False)
    assert "0 file(s) to fetch (2 already present)" in format_estimate(plan)


def test_missing_credentials_refuse_even_with_yes() -> None:
    with pytest.raises(DownloadRefusedError, match="FRED_API_KEY"):
        check_download_budget(_plan(10, missing=("FRED_API_KEY",)), max_gb=2.0, yes=True)


@pytest.mark.parametrize("bad", [0.0, -1.0, float("nan"), float("inf")])
def test_budget_must_be_positive_and_finite(bad: float) -> None:
    with pytest.raises(ValueError, match="positive finite"):
        check_download_budget(_plan(1), max_gb=bad, yes=False)


def test_estimate_mentions_files_size_and_time() -> None:
    text = format_estimate(_plan(500_000_000))
    assert "1 file(s) to fetch" in text
    assert "0.500 GB" in text
    assert "~2.0 min" in text


# --------------------------------------------------------------------------- validators


@pytest.mark.parametrize(
    "uri",
    [
        "https://user:pw@example.org/x",
        "https://api.stlouisfed.org/fred/series/observations?series_id=DGS10&api_key=abc123def456",
        "https://api.example.com/v3/x?apiKey=abc",
        "https://bucket.s3.amazonaws.com/k?X-Amz-Signature=abcdef&X-Amz-Credential=x",
        "https://huggingface.co/x?token=hf_EXAMPLEbCdEfGhIjKlMnOpQrStUvWxYz0",
    ],
)
def test_credential_bearing_uris_are_refused(uri: str) -> None:
    with pytest.raises(ValidationError, match="credentials"):
        PlannedFile(remote_uri=uri, relative_path="x")
    assert "abc" not in strip_credentials(uri).split("?")[-1] or "series_id" in strip_credentials(
        uri
    )


def test_strip_credentials_keeps_the_rest() -> None:
    url = "https://user:pw@api.stlouisfed.org/fred/series/observations?series_id=DGS10&api_key=abc&file_type=json"
    clean = strip_credentials(url)
    assert (
        clean
        == "https://api.stlouisfed.org/fred/series/observations?series_id=DGS10&file_type=json"
    )
    PlannedFile(remote_uri=clean, relative_path="x")


def test_credentials_in_request_values_are_refused() -> None:
    with pytest.raises(ValidationError, match="credentials"):
        FetchPlan(
            source="t",
            request={"url": "https://x.example/?api_key=EXAMPLEsecretvalue"},
            files=(),
            estimate_basis="b",
            estimated_seconds=0.0,
        )


@pytest.mark.parametrize(
    "bad", ["", "../escape.csv", "a/../../b", "/abs/path", "a\\b", "C:/x", "./a", "a//b"]
)
def test_relative_paths_cannot_escape(bad: str) -> None:
    with pytest.raises(ValidationError):
        PlannedFile(remote_uri="https://example.org/x", relative_path=bad)


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


def test_timestamps_must_be_aware_and_are_stored_in_utc() -> None:
    with pytest.raises(ValidationError):
        _entry(fetched_at=datetime(2026, 11, 12))  # noqa: DTZ001 - naive on purpose
    eastern = timezone(timedelta(hours=-5))
    entry = _entry(fetched_at=datetime(2026, 11, 12, 16, 0, tzinfo=eastern))
    assert entry.fetched_at.tzinfo == UTC
    assert entry.fetched_at.hour == 21


def test_checksums_and_time_order_are_validated() -> None:
    with pytest.raises(ValidationError):
        _entry(sha256="not-a-sha")
    start = datetime(2026, 11, 12, tzinfo=UTC)
    with pytest.raises(ValidationError, match="finished_at is before started_at"):
        Manifest(
            source="test",
            fetch_id="f1",
            request={},
            code_version=CODE,
            started_at=start,
            finished_at=start - timedelta(seconds=1),
            entries=(_entry(),),
        )


def test_request_and_attributes_are_immutable_and_serialisable() -> None:
    entry = _entry(attributes={"quote_size_convention": "shares"})
    with pytest.raises(TypeError):
        entry.attributes["quote_size_convention"] = "lots"  # type: ignore[index]
    plan = _plan(1)
    with pytest.raises(TypeError):
        plan.request["month"] = "2021-01"  # type: ignore[index]
    assert plan.model_dump(mode="json")["request"] == {"month": "2020-03"}
    assert FetchPlan.model_validate_json(plan.model_dump_json()) == plan


def test_normalized_tables_record_lineage() -> None:
    table = NormalizedTable(
        name="fred_observations",
        path="fred/observations.parquet",
        rows=10,
        sha256="b" * 64,
        input_fetch_ids=("f1",),
        code_version=CODE,
    )
    assert table.input_fetch_ids == ("f1",)


def test_pit_columns_match_the_brief() -> None:
    assert PIT_COLUMNS == ("event_time", "knowledge_time", "source", "ingested_at")


def test_no_adapters_registered_before_m1() -> None:
    assert ADAPTERS == {}


# --------------------------------------------------------------------------- template


class _FakeAdapter(SourceAdapter):
    name = "fake"
    required_env = ("FRED_API_KEY",)

    def __init__(self, context: SourceContext) -> None:
        super().__init__(context)
        self.downloaded: list[ApprovedPlan] = []

    def plan(self, **request: JsonScalar | list[JsonScalar]) -> FetchPlan:
        return _plan(10, source="fake")

    def _download(self, approved: ApprovedPlan) -> Manifest:
        self.downloaded.append(approved)
        now = datetime.now(UTC)
        return Manifest(
            source="fake",
            fetch_id="f1",
            request={},
            code_version=CODE,
            started_at=now,
            finished_at=now,
            entries=(),
        )

    def normalize(self, manifest: Manifest) -> Sequence[NormalizedTable]:
        return ()


def _adapter(tmp_path: Path, env: dict[str, str]) -> _FakeAdapter:
    settings = Settings.from_env({"HOME": str(tmp_path), **env})
    return _FakeAdapter(
        SourceContext(settings=settings, layout=DataLayout(settings.data_dir), code_version=CODE)
    )


def test_fetch_refuses_offline_before_downloading(tmp_path: Path) -> None:
    adapter = _adapter(tmp_path, {"FRED_API_KEY": "EXAMPLE-key-123456"})
    printed: list[str] = []
    with pytest.raises(NetworkDisabledError):  # conftest sets MJ_OFFLINE=1 for unit tests
        adapter.fetch(adapter.plan(), max_gb=2.0, yes=False, echo=printed.append)
    assert printed  # the estimate is printed first
    assert "file(s) to fetch" in printed[0]
    assert adapter.downloaded == []


def test_fetch_runs_every_guard_in_order(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MJ_OFFLINE", "0")
    no_key = _adapter(tmp_path, {})
    with pytest.raises(DownloadRefusedError, match="FRED_API_KEY"):
        no_key.fetch(no_key.plan(), max_gb=2.0, yes=True, echo=lambda _: None)
    assert no_key.downloaded == []

    adapter = _adapter(tmp_path, {"FRED_API_KEY": "EXAMPLE-key-123456"})
    manifest = adapter.fetch(adapter.plan(), max_gb=2.0, yes=False, echo=lambda _: None)
    assert manifest.source == "fake"
    assert adapter.downloaded[0].plan.required_credentials == ("FRED_API_KEY",)
    with pytest.raises(ValueError, match="not 'fake'"):
        adapter.fetch(_plan(1, source="other"), max_gb=2.0, yes=False, echo=lambda _: None)


def test_fetch_refuses_an_unsafe_data_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, repo_root: Path
) -> None:
    import shutil

    if shutil.which("git") is None or not (repo_root / ".git").exists():
        pytest.skip("needs a git checkout")
    monkeypatch.setenv("MJ_OFFLINE", "0")
    adapter = _adapter(
        tmp_path,
        {"FRED_API_KEY": "EXAMPLE-key-123456", "MJ_DATA_DIR": str(repo_root / "configs" / "x")},
    )
    with pytest.raises(UnsafeDataDirError):
        adapter.fetch(adapter.plan(), max_gb=2.0, yes=True, echo=lambda _: None)
    assert adapter.downloaded == []
