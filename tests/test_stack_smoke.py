"""The storage stack works on this platform: Polars -> Parquet -> PyArrow -> DuckDB.

CI runs this on x86_64 Linux, aarch64 Linux and arm64 macOS, so a missing or broken
wheel shows up here rather than in M1.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import duckdb
import polars as pl
import pyarrow as pa
import pyarrow.parquet as pq


def test_timezone_aware_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "pit.parquet"
    knowledge = [
        datetime(2020, 3, 16, 20, 0, tzinfo=UTC),
        datetime(2020, 3, 17, 20, 0, tzinfo=UTC),
    ]
    frame = pl.DataFrame(
        {
            "asset_id": ["A", "B"],
            "event_time": knowledge,
            "knowledge_time": knowledge,
            "close": [1.5, 2.5],
        }
    )
    frame.write_parquet(path)

    table = pq.read_table(path)
    knowledge_type = table.schema.field("knowledge_time").type
    assert isinstance(knowledge_type, pa.TimestampType)
    assert knowledge_type.tz == "UTC"

    assert pl.read_parquet(path).equals(frame)

    con = duckdb.connect(
        config={"autoinstall_known_extensions": False, "autoload_known_extensions": False}
    )
    try:
        row = con.execute(
            "SELECT count(*), max(close) FROM read_parquet(?) "
            "WHERE knowledge_time <= TIMESTAMPTZ '2020-03-16 20:00:00+00'",
            [str(path)],
        ).fetchone()
    finally:
        con.close()
    assert row == (1, 1.5)
