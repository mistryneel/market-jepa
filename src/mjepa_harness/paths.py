"""Layout of the data directory (``$MJ_DATA_DIR``) and guards that keep data out of git.

::

    $MJ_DATA_DIR/
      raw/<source>/...            immutable landing zone: files exactly as fetched
      manifests/<source>/*.json   one manifest per fetch (files, sizes, sha256, URL, time, code)
      pit/<table>/...             normalized point-in-time Parquet tables (M2)
      catalog/mjepa.duckdb        DuckDB catalog of views over pit/ (M2)
      locked/                     locked-test-period labels; read only with --unlock-test (M3)
      registry/                   append-only run registry (M5)
      cache/                      HTTP / Hugging Face caches
      tmp/                        partial downloads; atomically renamed into raw/

Nothing is created at import time; callers ask for directories with :meth:`DataLayout.ensure`.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Final

_SOURCE_NAME_RE: Final = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")


class UnsafeDataDirError(RuntimeError):
    """The data directory would let data end up in git."""


@dataclass(frozen=True)
class DataLayout:
    root: Path

    @property
    def raw(self) -> Path:
        return self.root / "raw"

    @property
    def manifests(self) -> Path:
        return self.root / "manifests"

    @property
    def pit(self) -> Path:
        return self.root / "pit"

    @property
    def catalog(self) -> Path:
        return self.root / "catalog" / "mjepa.duckdb"

    @property
    def locked(self) -> Path:
        return self.root / "locked"

    @property
    def registry(self) -> Path:
        return self.root / "registry"

    @property
    def cache(self) -> Path:
        return self.root / "cache"

    @property
    def tmp(self) -> Path:
        return self.root / "tmp"

    def raw_dir(self, source: str) -> Path:
        return self.raw / _checked_source(source)

    def manifest_dir(self, source: str) -> Path:
        return self.manifests / _checked_source(source)

    def describe(self) -> dict[str, Path]:
        return {
            "root": self.root,
            "raw": self.raw,
            "manifests": self.manifests,
            "pit": self.pit,
            "catalog": self.catalog,
            "locked": self.locked,
            "registry": self.registry,
            "cache": self.cache,
            "tmp": self.tmp,
        }

    def ensure(self, *dirs: Path) -> None:
        """Create the given directories, which must resolve to inside ``root``.

        Refuses before creating anything if the data root is somewhere git could commit.
        """
        root = self.root.resolve()
        for directory in dirs:
            if not directory.resolve().is_relative_to(root):
                raise ValueError(f"{directory} is outside the data root {self.root}")
        check_data_dir_safe(self.root)
        for directory in dirs:
            directory.mkdir(parents=True, exist_ok=True)


def _checked_source(source: str) -> str:
    if not _SOURCE_NAME_RE.fullmatch(source):
        raise ValueError(f"invalid source name {source!r}: use [a-z0-9_-], max 64 chars")
    return source


def find_repo_root(start: Path) -> Path | None:
    """Nearest ancestor of ``start`` (inclusive) containing ``.git`` (dir or worktree file)."""
    for candidate in (start, *start.parents):
        if (candidate / ".git").exists():
            return candidate
    return None


def containing_worktree(path: Path) -> Path | None:
    """Top level of the git work tree that contains ``path``, or None.

    Asks git from the nearest existing ancestor, so symlinks, ``..``, case variants on
    case-insensitive filesystems, linked worktrees and unrelated repositories are all
    resolved the way git itself sees them.
    """
    anchor = path.resolve()  # follows symlinks, even ones whose target does not exist yet
    while not anchor.exists() and anchor != anchor.parent:
        anchor = anchor.parent
    git = shutil.which("git")
    if git is None:
        root = find_repo_root(anchor.resolve())
        return root.resolve() if root is not None else None
    result = subprocess.run(  # noqa: S603 - fixed argv, no shell
        [git, "-C", str(anchor), "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    if result.returncode != 0 or not result.stdout.strip():
        return None
    return Path(result.stdout.strip()).resolve()


def _relative_inside(path: Path, root: Path) -> PurePosixPath | None:
    """``path`` relative to ``root`` if it lies inside it (symlinks and case resolved)."""
    resolved, root = path.resolve(), root.resolve()
    if resolved.is_relative_to(root):
        return PurePosixPath(resolved.relative_to(root).as_posix())
    for ancestor in (resolved, *resolved.parents):
        if ancestor.exists() and root.exists() and ancestor.samefile(root):
            return PurePosixPath(resolved.relative_to(ancestor).as_posix())
    return None


def check_data_dir_safe(data_dir: Path, repo_roots: Iterable[Path | None] = ()) -> None:
    """Refuse a data directory that git could commit.

    The repository that actually contains ``data_dir`` is found with git itself
    (:func:`containing_worktree`); ``repo_roots`` adds further repositories to check, e.g.
    the harness checkout. Outside every work tree is always fine. Inside one, the
    directory itself must be git-ignored there (checked with ``git check-ignore``).
    """
    candidates = {root.resolve() for root in (containing_worktree(data_dir), *repo_roots) if root}
    for root in sorted(candidates):
        relative = _relative_inside(data_dir, root)
        if relative is None:
            continue
        if relative == PurePosixPath("."):
            raise UnsafeDataDirError(f"data dir {data_dir} is the repository root {root} itself")
        git = shutil.which("git")
        if git is None:
            raise UnsafeDataDirError(
                f"data dir {data_dir} is inside the repository {root} and git is not "
                "available to confirm it is ignored; move MJ_DATA_DIR outside the repo"
            )
        # Probe names use extensions that .gitignore does NOT ignore globally (manifests are
        # .json, landing files may be .csv): the directory itself must be ignored.
        for probe in (
            relative / "mjepa-probe.json",
            relative / "raw" / "probe" / "mjepa-probe.csv",
        ):
            result = subprocess.run(  # noqa: S603 - fixed argv, no shell
                [git, "-C", str(root), "check-ignore", "-q", "--no-index", str(probe)],
                capture_output=True,
                check=False,
                timeout=30,
            )
            if result.returncode != 0:
                raise UnsafeDataDirError(
                    f"data dir {data_dir} is inside the git work tree {root} and is NOT "
                    f"git-ignored there ({probe} would be committable). Point MJ_DATA_DIR "
                    "outside every repository (default ~/data/market-jepa)."
                )
