"""CRSP/WRDS source contract for daily U.S. equities.

This first M1 change intentionally does *not* connect to WRDS or download licensed
CRSP rows.  It fixes the source vocabulary, normalized-table contract and an
offline query plan so the live extraction can be implemented and verified in the
next change after inspecting the account's current CIZ schemas/tables.

The normalized contract is provider-independent:

* ``crsp_daily_stock``: one row per security/session with raw close, total return,
  volume and shares outstanding;
* ``crsp_security_master``: point-in-time identifiers and listing attributes;
* ``crsp_delistings``: delisting events and returns.

CRSP's permanent security identifier (PERMNO) becomes ``asset_id``.  No vendor
column names beyond PERMNO are pinned here because WRDS' current CIZ layout is
verified against the authenticated account in PR2.
"""

from __future__ import annotations

from datetime import date
from typing import Final

from mjepa_harness.sources.base import (
    ApprovedPlan,
    FetchPlan,
    JsonScalar,
    Manifest,
    NormalizedTable,
    PlannedFile,
    SourceAdapter,
)

CRSP_DATASETS: Final[tuple[str, ...]] = (
    "daily_stock",
    "security_master",
    "delistings",
)

CRSP_DAILY_OUTPUT_COLUMNS: Final[tuple[str, ...]] = (
    "asset_id",
    "event_time",
    "knowledge_time",
    "source",
    "ingested_at",
    "raw_close",
    "total_return",
    "volume",
    "shares_outstanding",
)

CRSP_SECURITY_MASTER_OUTPUT_COLUMNS: Final[tuple[str, ...]] = (
    "asset_id",
    "event_time",
    "knowledge_time",
    "source",
    "ingested_at",
    "ticker",
    "company_name",
    "share_code",
    "exchange_code",
    "security_status",
)

CRSP_DELISTING_OUTPUT_COLUMNS: Final[tuple[str, ...]] = (
    "asset_id",
    "event_time",
    "knowledge_time",
    "source",
    "ingested_at",
    "delisting_code",
    "delisting_return",
)


def _iso_date(name: str, value: object) -> date:
    if not isinstance(value, str):
        raise ValueError(f"{name} must be an ISO date string (YYYY-MM-DD)")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be an ISO date string (YYYY-MM-DD)") from exc


def _dataset(value: object) -> str:
    if value is None:
        return "daily_stock"
    if not isinstance(value, str) or value not in CRSP_DATASETS:
        choices = ", ".join(CRSP_DATASETS)
        raise ValueError(f"dataset must be one of: {choices}")
    return value


class CrspAdapter(SourceAdapter):
    """CRSP contract; live WRDS extraction and normalization land in PR2.

    The class is deliberately not registered in ``sources.ADAPTERS`` yet.  Importing
    it therefore cannot make a partially implemented source appear runnable to the
    CLI.  PR2 registers it only after an authenticated WRDS smoke test has pinned the
    current CIZ schema/table names.
    """

    name = "crsp"
    plan_requires_network = False

    def _plan(self, **request: JsonScalar | list[JsonScalar]) -> FetchPlan:
        start = _iso_date("start", request.get("start"))
        end = _iso_date("end", request.get("end"))
        if end < start:
            raise ValueError("end must be on or after start")

        dataset = _dataset(request.get("dataset"))
        start_text = start.isoformat()
        end_text = end.isoformat()

        return FetchPlan(
            source=self.name,
            request={
                "dataset": dataset,
                "start": start_text,
                "end": end_text,
                "access": "wrds",
                "layout": "ciz",
            },
            files=(
                PlannedFile(
                    remote_uri=f"wrds://crsp/{dataset}",
                    relative_path=f"exports/{dataset}/{start_text}_{end_text}.parquet",
                ),
            ),
            estimate_basis=(
                "unknown until PR2 pins the authenticated WRDS CIZ query and measures a sample"
            ),
            estimated_seconds=0.0,
            notes=(
                "contract-only PR: no WRDS query is executed",
                "download size is intentionally unknown, so fetch would require explicit approval",
                "PERMNO is normalized to asset_id; raw vendor column names are pinned in PR2",
            ),
        )

    def _download(self, approved: ApprovedPlan) -> Manifest:
        del approved
        raise NotImplementedError(
            "CRSP live extraction is intentionally deferred to PR2 after the authenticated "
            "WRDS CIZ schema/table names are inspected and pinned"
        )

    def normalize(self, manifest: Manifest) -> tuple[NormalizedTable, ...]:
        del manifest
        raise NotImplementedError(
            "CRSP normalization is intentionally deferred to PR2 with the verified CIZ mapping"
        )
