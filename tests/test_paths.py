from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from mjepa_harness.paths import (
    DataLayout,
    UnsafeDataDirError,
    check_data_dir_safe,
    containing_worktree,
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
    with pytest.raises(ValueError, match="outside the data root"):
        layout.ensure(layout.root / ".." / "escaped")


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


def test_data_dir_outside_any_repo_is_safe(tmp_path: Path, git_repo: Path) -> None:
    check_data_dir_safe(tmp_path / "outside")
    check_data_dir_safe(tmp_path / "outside", [git_repo, None])


def test_ignored_data_dir_inside_repo_is_safe(git_repo: Path) -> None:
    check_data_dir_safe(git_repo / "data")


def test_unignored_data_dir_inside_repo_is_refused(git_repo: Path) -> None:
    # *.parquet is ignored, but manifests (.json) and CSVs would still be committable.
    with pytest.raises(UnsafeDataDirError, match="NOT git-ignored"):
        check_data_dir_safe(git_repo / "mydata")


def test_the_containing_repo_is_found_without_being_named(tmp_path: Path, git_repo: Path) -> None:
    """A data dir inside some other checkout (e.g. a sibling worktree) is still refused."""
    assert containing_worktree(git_repo / "mydata" / "deeper") == git_repo.resolve()
    assert containing_worktree(tmp_path / "nowhere") is None
    with pytest.raises(UnsafeDataDirError):
        check_data_dir_safe(git_repo / "mydata", repo_roots=[])


def test_symlink_and_dotdot_spellings_are_resolved(tmp_path: Path, git_repo: Path) -> None:
    link = tmp_path / "innocent-looking"
    link.symlink_to(git_repo / "mydata", target_is_directory=False)
    with pytest.raises(UnsafeDataDirError):
        check_data_dir_safe(link)
    with pytest.raises(UnsafeDataDirError):
        check_data_dir_safe(git_repo / "data" / ".." / "mydata")


def test_case_variants_are_resolved_on_case_insensitive_filesystems(git_repo: Path) -> None:
    variant_root = git_repo.parent / git_repo.name.upper()  # e.g. .../REPO for .../repo
    if not variant_root.exists():
        pytest.skip("case-sensitive filesystem")
    with pytest.raises(UnsafeDataDirError):
        check_data_dir_safe(variant_root / "mydata")


def test_repo_root_as_data_dir_is_refused(git_repo: Path) -> None:
    with pytest.raises(UnsafeDataDirError, match="repository root"):
        check_data_dir_safe(git_repo)


def test_ensure_refuses_before_creating_anything(git_repo: Path) -> None:
    layout = DataLayout(git_repo / "mydata")
    with pytest.raises(UnsafeDataDirError):
        layout.ensure(layout.raw_dir("fred"))
    assert not (git_repo / "mydata").exists()


def test_find_repo_root(git_repo: Path) -> None:
    nested = git_repo / "a" / "b"
    nested.mkdir(parents=True)
    assert find_repo_root(nested) == git_repo
