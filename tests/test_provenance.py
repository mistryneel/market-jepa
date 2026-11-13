from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from mjepa_harness import __version__
from mjepa_harness.provenance import code_version


def test_outside_git_reports_nogit(tmp_path: Path) -> None:
    version = code_version(tmp_path)
    assert version.git_sha is None
    assert str(version) == f"{__version__}+nogit"


def test_sha_and_dirty_flag_in_a_repo(tmp_path: Path) -> None:
    git = shutil.which("git")
    if git is None:
        pytest.skip("git not available")
    repo = tmp_path / "repo"
    repo.mkdir()

    def run(*args: str) -> None:
        # conftest makes git hermetic (no global config, so no signing prompts).
        subprocess.run([git, "-C", str(repo), *args], check=True, capture_output=True, timeout=30)

    run("init", "-q")
    assert code_version(repo).git_sha is None  # no commits yet
    (repo / "f.txt").write_text("a", encoding="utf-8")
    run("add", "f.txt")
    run("commit", "-q", "-m", "init")
    clean = code_version(repo)
    assert clean.git_sha is not None
    assert len(clean.git_sha) == 40
    assert clean.git_dirty is False
    assert str(clean).endswith(clean.git_sha[:12])
    (repo / "f.txt").write_text("b", encoding="utf-8")
    dirty = code_version(repo)
    assert dirty.git_dirty is True
    assert str(dirty).endswith(".dirty")
