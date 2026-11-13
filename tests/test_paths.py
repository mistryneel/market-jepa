from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from mjepa_harness.paths import (
    DataLayout,
    UnsafeDataDirError,
    check_data_dir_safe,
    find_repo_root,
)


def test_layout_areas_live_under_root(tmp_path: Path) -> None:
    layout = DataLayout(tmp_path / "root")
    for area, path in layout.describe().items():
        assert path.is_relative_to(layout.root), area
    assert layout.locked != layout.pit
    assert layout.raw_dir("fred") == layout.root / "raw" / "fred"


@pytest.mark.parametrize("bad", ["", "../etc", "FRED", "a/b", "x" * 65])
def test_source_names_are_validated(tmp_path: Path, bad: str) -> None:
    with pytest.raises(ValueError, match="invalid source name"):
        DataLayout(tmp_path).raw_dir(bad)


def test_ensure_creates_only_inside_root(tmp_path: Path) -> None:
    layout = DataLayout(tmp_path / "root")
    layout.ensure(layout.raw_dir("fred"))
    assert layout.raw_dir("fred").is_dir()
    with pytest.raises(ValueError, match="outside the data root"):
        layout.ensure(tmp_path / "elsewhere")


@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
    git = shutil.which("git")
    if git is None:
        pytest.skip("git not available")
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run([git, "init", "-q", str(repo)], check=True, timeout=30)
    (repo / ".gitignore").write_text("/data/\n*.parquet\n", encoding="utf-8")
    return repo


def test_data_dir_outside_repo_is_safe(git_repo: Path, tmp_path: Path) -> None:
    check_data_dir_safe(tmp_path / "outside", git_repo)
    check_data_dir_safe(tmp_path / "outside", None)


def test_ignored_data_dir_inside_repo_is_safe(git_repo: Path) -> None:
    check_data_dir_safe(git_repo / "data", git_repo)


def test_unignored_data_dir_inside_repo_is_refused(git_repo: Path) -> None:
    # *.parquet is ignored, but manifests (.json) and CSVs would still be committable.
    with pytest.raises(UnsafeDataDirError, match="NOT git-ignored"):
        check_data_dir_safe(git_repo / "mydata", git_repo)


def test_repo_root_as_data_dir_is_refused(git_repo: Path) -> None:
    with pytest.raises(UnsafeDataDirError, match="repository root"):
        check_data_dir_safe(git_repo, git_repo)


def test_find_repo_root(git_repo: Path) -> None:
    nested = git_repo / "a" / "b"
    nested.mkdir(parents=True)
    assert find_repo_root(nested) == git_repo
