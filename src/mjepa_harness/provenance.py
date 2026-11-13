"""Code provenance for manifests and the run registry: package version + git state."""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from mjepa_harness import __version__
from mjepa_harness.paths import find_repo_root


@dataclass(frozen=True)
class CodeVersion:
    package_version: str
    git_sha: str | None
    git_dirty: bool | None

    def __str__(self) -> str:
        if self.git_sha is None:
            return f"{self.package_version}+nogit"
        suffix = ".dirty" if self.git_dirty else ""
        return f"{self.package_version}+g{self.git_sha[:12]}{suffix}"


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str] | None:
    git = shutil.which("git")
    if git is None:
        return None
    try:
        return subprocess.run(  # noqa: S603 - fixed argv, no shell
            [git, "-C", str(repo), *args],
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None


def code_version(repo: Path | None = None) -> CodeVersion:
    """Version of the code that is running. ``git_sha`` is None outside a git checkout or
    before the first commit; ``git_dirty`` reports uncommitted changes to tracked files."""
    root = repo if repo is not None else find_repo_root(Path(__file__).resolve().parent)
    if root is None:
        return CodeVersion(__version__, None, None)
    head = _git(root, "rev-parse", "--verify", "--quiet", "HEAD")
    if head is None or head.returncode != 0 or not head.stdout.strip():
        return CodeVersion(__version__, None, None)
    status = _git(root, "status", "--porcelain", "--untracked-files=no")
    dirty = None if status is None or status.returncode != 0 else bool(status.stdout.strip())
    return CodeVersion(__version__, head.stdout.strip(), dirty)
