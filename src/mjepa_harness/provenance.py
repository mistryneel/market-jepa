"""Code provenance for manifests and the run registry: package version + git state.

"Dirty" is conservative: tracked changes *and untracked files* under the paths that
affect results (:data:`RESULT_AFFECTING_PATHS`) count, and an unknown state is
reported as ``dirty-unknown`` rather than clean. A non-editable install outside a git
checkout reports ``nogit`` (no SHA is guessed).
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from mjepa_harness import __version__
from mjepa_harness.paths import find_repo_root

RESULT_AFFECTING_PATHS: Final = (
    "src",
    "configs",
    "data_ref",
    "pyproject.toml",
    "uv.lock",
    ".python-version",
)


@dataclass(frozen=True)
class CodeVersion:
    package_version: str
    git_sha: str | None
    git_dirty: bool | None

    def __str__(self) -> str:
        if self.git_sha is None:
            return f"{self.package_version}+nogit"
        suffix = {None: ".dirty-unknown", True: ".dirty", False: ""}[self.git_dirty]
        return f"{self.package_version}+g{self.git_sha[:12]}{suffix}"

    @property
    def is_clean(self) -> bool:
        """True only for a known SHA with known-clean result-affecting paths."""
        return self.git_sha is not None and self.git_dirty is False


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


def running_from_checkout_source(package_dir: Path, root: Path) -> bool:
    """True if the imported package is the ``src/`` tree of the checkout at ``root``."""
    return package_dir.resolve().is_relative_to((root / "src").resolve())


def code_version(repo: Path | None = None) -> CodeVersion:
    """Version of the code that is running.

    ``git_sha`` is None outside a git checkout or before the first commit. ``git_dirty``
    is True if any result-affecting path has uncommitted changes or untracked files,
    and None if git could not tell.
    """
    package_dir = Path(__file__).resolve().parent
    root = repo if repo is not None else find_repo_root(package_dir)
    if root is None:
        return CodeVersion(__version__, None, None)
    if repo is None and not running_from_checkout_source(package_dir, root):
        # e.g. a wheel installed into a venv that happens to sit inside some checkout:
        # that checkout's SHA says nothing about the code actually running.
        return CodeVersion(__version__, None, None)
    head = _git(root, "rev-parse", "--verify", "--quiet", "HEAD")
    if head is None or head.returncode != 0 or not head.stdout.strip():
        return CodeVersion(__version__, None, None)
    status = _git(
        root, "status", "--porcelain", "--untracked-files=all", "--", *RESULT_AFFECTING_PATHS
    )
    dirty = None if status is None or status.returncode != 0 else bool(status.stdout.strip())
    return CodeVersion(__version__, head.stdout.strip(), dirty)
