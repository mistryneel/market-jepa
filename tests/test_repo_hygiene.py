"""Rule 1, enforced: no data or secrets in git.

Checks every file git would commit (tracked files plus untracked files that are not
ignored), so violations fail *before* the commit happens.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from datetime import date
from pathlib import Path
from typing import Any

import pytest
import yaml

from mjepa_harness.settings import CREDENTIAL_ENV_VARS

REPO = Path(__file__).resolve().parents[1]
MAX_FILE_BYTES = 1_000_000  # "under 1 MB"
DATA_SUFFIXES = frozenset(
    {
        ".csv", ".tsv", ".parquet", ".feather", ".arrow", ".ipc", ".duckdb", ".db",
        ".sqlite", ".mds", ".zst", ".zstd", ".gz", ".zip", ".tar", ".h5", ".hdf5",
        ".npy", ".npz", ".pkl", ".pickle", ".xlsx", ".xls",
    }
)  # fmt: skip
DATA_REF_TABLE_SUFFIXES = frozenset({".csv", ".tsv"})
DATA_REF_META_FILES = frozenset({"README.md", "SOURCES.yaml"})

# Real credential values from the developer's environment, captured at import time
# (before the autouse fixture scrubs the environment for each test).
_REAL_SECRET_VALUES = tuple(
    value for name in CREDENTIAL_ENV_VARS if len(value := os.environ.get(name, "").strip()) >= 8
)
_SECRET_SHAPES = re.compile(
    r"hf_[A-Za-z0-9]{30,}"  # Hugging Face token
    r"|(?:AKIA|ASIA)[0-9A-Z]{16}"  # AWS access key id
    r"|-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"
    r"|ghp_[A-Za-z0-9]{36}|github_pat_[A-Za-z0-9_]{50,}"  # GitHub tokens
    r"|sk-ant-[A-Za-z0-9_-]{20,}"  # Anthropic keys
)
_PLACEHOLDER_MARKER = "EXAMPLE"  # test fixtures use obviously fake values containing this


def _git() -> str:
    git = shutil.which("git")
    if git is None or not (REPO / ".git").exists():
        pytest.skip("not a git checkout")
    return git


def committable_files() -> list[Path]:
    """Tracked files plus untracked, non-ignored files (what `git add -A` would stage)."""
    result = subprocess.run(
        [_git(), "-C", str(REPO), "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
        capture_output=True,
        check=True,
        timeout=60,
    )
    rels = sorted({p for p in result.stdout.decode().split("\0") if p})
    return [REPO / rel for rel in rels if (REPO / rel).is_file()]


def _rel(path: Path) -> str:
    return path.relative_to(REPO).as_posix()


def _is_data_file(path: Path) -> bool:
    return any(suffix in DATA_SUFFIXES for suffix in path.suffixes)


def test_no_large_files() -> None:
    too_big = [
        f"{_rel(p)} ({p.stat().st_size} B)"
        for p in committable_files()
        if p.stat().st_size >= MAX_FILE_BYTES
    ]
    assert not too_big, f"files >= 1 MB must not be committed: {too_big}"


def test_data_files_only_in_data_ref() -> None:
    misplaced = [
        _rel(p)
        for p in committable_files()
        if _is_data_file(p) and not _rel(p).startswith("data_ref/")
    ]
    assert not misplaced, f"data files outside data_ref/: {misplaced}"


def test_data_ref_tables_have_source_notes() -> None:
    sources_path = REPO / "data_ref" / "SOURCES.yaml"
    sources: Any = yaml.safe_load(sources_path.read_text(encoding="utf-8")) or {}
    entries = sources.get("files") or []
    by_path: dict[str, dict[str, Any]] = {}
    for entry in entries:
        assert isinstance(entry, dict), f"bad entry in SOURCES.yaml: {entry!r}"
        missing = {"path", "description", "source_urls", "retrieved", "licence"} - set(entry)
        assert not missing, f"SOURCES.yaml entry {entry.get('path')!r} lacks {sorted(missing)}"
        urls = entry["source_urls"]
        assert urls, f"{entry['path']}: source_urls is empty"
        assert all(str(url).startswith("https://") for url in urls), entry["path"]
        assert isinstance(entry["retrieved"], date), f"{entry['path']}: retrieved must be a date"
        by_path[entry["path"]] = entry

    data_ref_files = [p for p in committable_files() if _rel(p).startswith("data_ref/")]
    for path in data_ref_files:
        rel = path.relative_to(REPO / "data_ref").as_posix()
        if rel in DATA_REF_META_FILES:
            continue
        assert path.suffix in DATA_REF_TABLE_SUFFIXES, f"unexpected file type in data_ref/: {rel}"
        assert rel in by_path, f"data_ref/{rel} has no source note in data_ref/SOURCES.yaml"
    for rel in by_path:
        assert (REPO / "data_ref" / rel).is_file(), f"SOURCES.yaml lists missing file {rel}"


def test_no_env_files_committed() -> None:
    env_files = [
        _rel(p)
        for p in committable_files()
        if p.name.startswith(".env") and p.name != ".env.example"
    ]
    assert not env_files, f"never commit env files: {env_files}"


def test_env_example_lists_every_credential_with_empty_values() -> None:
    lines = (REPO / ".env.example").read_text(encoding="utf-8").splitlines()
    assignments = dict(
        line.split("=", 1) for line in lines if line.strip() and not line.lstrip().startswith("#")
    )
    for name in CREDENTIAL_ENV_VARS:
        assert name in assignments, f".env.example must list {name}"
        assert assignments[name].strip() == "", f".env.example must not contain a value for {name}"
    assert "MJ_DATA_DIR" in assignments


def test_no_secrets_in_committable_files() -> None:
    offenders: list[str] = []
    for path in committable_files():
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for match in _SECRET_SHAPES.finditer(text):
            if _PLACEHOLDER_MARKER not in match.group(0):
                offenders.append(f"{_rel(path)}: secret-shaped string {match.group(0)[:8]}...")
        for value in _REAL_SECRET_VALUES:
            if value in text:
                offenders.append(f"{_rel(path)}: contains the value of a credential from your env")
    assert not offenders, offenders


@pytest.mark.parametrize(
    "path",
    [
        ".env",
        ".env.local",
        "data/raw/x.csv",
        "prices.parquet",
        "catalog/mjepa.duckdb",
        "shard.00000.mds.zstd",
        "day_aggs/2020-03-02.csv.gz",
        ".venv/bin/python",
    ],
)
def test_gitignore_covers_secret_and_data_paths(path: str) -> None:
    result = subprocess.run(
        [_git(), "-C", str(REPO), "check-ignore", "-q", "--no-index", path], check=False, timeout=30
    )
    assert result.returncode == 0, f"{path} is not git-ignored"


@pytest.mark.parametrize(
    "path", [".env.example", "data_ref/calendars/fomc.csv", "configs/endpoint.yaml", "uv.lock"]
)
def test_gitignore_keeps_committed_files_visible(path: str) -> None:
    result = subprocess.run(
        [_git(), "-C", str(REPO), "check-ignore", "-q", "--no-index", path], check=False, timeout=30
    )
    assert result.returncode == 1, f"{path} must not be git-ignored"
