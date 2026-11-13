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
from dataclasses import dataclass
from pathlib import Path
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
        """Create the given directories (which must live under ``root``)."""
        for directory in dirs:
            if not directory.is_relative_to(self.root):
                raise ValueError(f"{directory} is outside the data root {self.root}")
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


def check_data_dir_safe(data_dir: Path, repo_root: Path | None) -> None:
    """Refuse a data directory inside the repository unless git ignores it.

    Data must never be committable. Outside the repo is always fine; inside it, every
    path under ``data_dir`` must be git-ignored (checked with ``git check-ignore``).
    """
    if repo_root is None:
        return
    data_dir = data_dir.absolute()
    repo_root = repo_root.absolute()
    if not data_dir.is_relative_to(repo_root):
        return
    if data_dir == repo_root:
        raise UnsafeDataDirError(f"data dir {data_dir} is the repository root itself")
    git = shutil.which("git")
    if git is None:
        raise UnsafeDataDirError(
            f"data dir {data_dir} is inside the repository {repo_root} and git is not "
            "available to confirm it is ignored; move MJ_DATA_DIR outside the repo"
        )
    # Probe names deliberately use extensions that .gitignore does NOT ignore globally
    # (manifests are .json, landing files may be .csv): the directory itself must be ignored.
    probes = (data_dir / "mjepa-probe.json", data_dir / "raw" / "probe" / "mjepa-probe.csv")
    for probe in probes:
        result = subprocess.run(  # noqa: S603 - fixed argv, no shell
            [git, "-C", str(repo_root), "check-ignore", "-q", "--no-index", str(probe)],
            capture_output=True,
            check=False,
            timeout=30,
        )
        if result.returncode != 0:
            raise UnsafeDataDirError(
                f"data dir {data_dir} is inside the repository {repo_root} and is NOT "
                f"git-ignored ({probe.relative_to(data_dir)} would be committable). "
                "Point MJ_DATA_DIR outside the repo (default ~/data/market-jepa)."
            )
