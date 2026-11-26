from __future__ import annotations

import pytest

from mjepa_harness.config import CrspSourceConfig
from mjepa_harness.sources.crsp import (
    CRSP_DAILY_OUTPUT_COLUMNS,
    CRSP_DATASETS,
    CRSP_DELISTING_OUTPUT_COLUMNS,
    CRSP_SECURITY_MASTER_OUTPUT_COLUMNS,
    CrspAdapter,
)


def _adapter_without_context() -> CrspAdapter:
    # Planning is intentionally offline in PR1 and does not touch SourceContext.
    # Bypassing __init__ keeps this unit test independent of filesystem/data-dir setup.
    return CrspAdapter.__new__(CrspAdapter)


def test_crsp_plan_is_offline_and_has_no_vendor_table_guess() -> None:
    plan = _adapter_without_context().plan(
        dataset="daily_stock",
        start="2022-01-01",
        end="2022-01-31",
    )

    assert plan.source == "crsp"
    assert plan.request == {
        "dataset": "daily_stock",
        "start": "2022-01-01",
        "end": "2022-01-31",
        "access": "wrds",
        "layout": "ciz",
    }
    assert len(plan.files) == 1
    assert plan.files[0].remote_uri == "wrds://crsp/daily_stock"
    assert plan.files[0].expected_bytes is None
    assert plan.files[0].estimated_bytes is None
    assert "table" not in plan.request
    assert "schema" not in plan.request


def test_crsp_plan_defaults_to_daily_stock() -> None:
    plan = _adapter_without_context().plan(start="2005-01-01", end="2005-01-03")
    assert plan.request["dataset"] == "daily_stock"


@pytest.mark.parametrize("dataset", CRSP_DATASETS)
def test_crsp_plan_supports_contract_datasets(dataset: str) -> None:
    plan = _adapter_without_context().plan(
        dataset=dataset,
        start="2020-01-01",
        end="2020-01-02",
    )
    assert plan.request["dataset"] == dataset


@pytest.mark.parametrize(
    ("start", "end"),
    [
        ("2022/01/01", "2022-01-02"),
        ("2022-01-01", "not-a-date"),
        (None, "2022-01-02"),
    ],
)
def test_crsp_plan_rejects_bad_dates(
    start: str | None,
    end: str | None,
) -> None:
    with pytest.raises(ValueError, match="ISO date"):
        _adapter_without_context().plan(
            start=start,
            end=end,
        )


def test_crsp_plan_rejects_reverse_range() -> None:
    with pytest.raises(ValueError, match="end must be on or after start"):
        _adapter_without_context().plan(start="2022-02-01", end="2022-01-01")


def test_crsp_plan_rejects_unknown_dataset() -> None:
    with pytest.raises(ValueError, match="dataset must be one of"):
        _adapter_without_context().plan(
            dataset="mystery_table",
            start="2022-01-01",
            end="2022-01-02",
        )


def test_crsp_normalized_contract_keeps_pit_columns_and_asset_id() -> None:
    for columns in (
        CRSP_DAILY_OUTPUT_COLUMNS,
        CRSP_SECURITY_MASTER_OUTPUT_COLUMNS,
        CRSP_DELISTING_OUTPUT_COLUMNS,
    ):
        assert columns[:5] == (
            "asset_id",
            "event_time",
            "knowledge_time",
            "source",
            "ingested_at",
        )


def test_crsp_config_defaults_are_contract_only() -> None:
    cfg = CrspSourceConfig()
    assert cfg.access == "wrds"
    assert cfg.product_layout == "ciz"
    assert cfg.frequency == "daily"
    assert cfg.asset_id == "PERMNO"
    assert cfg.include_delisted is True
    assert cfg.wrds_schema is None
    assert cfg.daily_table is None
    assert cfg.security_master_table is None
    assert cfg.delisting_table is None
