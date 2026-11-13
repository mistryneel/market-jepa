"""Rule 1, enforced: no data or secrets in git.

Checks every file git would commit (tracked files plus untracked files that are not
ignored), so violations fail *before* the commit happens. Failure messages name files,
lines and pattern kinds, never secret values. The optional hook in
``scripts/hooks/pre-commit`` runs this module on every commit.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from datetime import date
from pathlib import Path
from typing import Any, Final

import pytest
import yaml

from mjepa_harness.log import SENSITIVE_KEY_PATTERN
from mjepa_harness.settings import CREDENTIAL_ENV_VARS

REPO: Final = Path(__file__).resolve().parents[1]
MAX_FILE_BYTES: Final = 1_000_000  # "under 1 MB"

# Compared case-insensitively against every suffix of a file name.
DATA_SUFFIXES: Final = frozenset(
    {
        ".csv", ".tsv", ".parquet", ".feather", ".arrow", ".ipc", ".duckdb", ".db",
        ".sqlite", ".mds", ".zst", ".zstd", ".gz", ".zip", ".tar", ".h5", ".hdf5",
        ".npy", ".npz", ".pkl", ".pickle", ".xlsx", ".xls",
        # Raw payload formats the sources return (APIs, EDGAR, calendars).
        ".json", ".jsonl", ".ndjson", ".xml", ".html", ".htm", ".txt", ".idx", ".sgml",
        ".dat",
    }
)  # fmt: skip
NON_DATA_ALLOWLIST: Final = frozenset[str]()
"""Repo-relative paths with a data-like suffix that are deliberately committed (none yet)."""
DATA_REF_TABLE_SUFFIXES: Final = frozenset({".csv", ".tsv"})
DATA_REF_META_FILES: Final = frozenset({"README.md", "SOURCES.yaml"})

PLACEHOLDER_MARKERS: Final = ("EXAMPLE", "example", "REDACTED", "<", "${", "xxxx", "XXXX")
"""Values containing any of these are placeholders (all test fixtures use EXAMPLE)."""

_SECRET_SHAPES: Final = {
    "huggingface-token": re.compile(r"hf_[A-Za-z0-9]{30,}"),
    "aws-access-key-id": re.compile(r"(?:AKIA|ASIA)[0-9A-Z]{16}"),
    "private-key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"),
    "github-token": re.compile(r"ghp_[A-Za-z0-9]{36}|github_pat_[A-Za-z0-9_]{50,}"),
    "anthropic-key": re.compile(r"sk-ant-[A-Za-z0-9_-]{20,}"),
    # key=value / key: "value" with a sensitive key name (FRED_API_KEY=, apiKey=,
    # aws_secret_access_key: ..., Authorization: Bearer ...) and a secret-looking value:
    # >= 16 chars of token characters, mixing letters and digits.
    "sensitive-assignment": re.compile(
        rf"(?i)(?<![A-Za-z0-9])(?:{SENSITIVE_KEY_PATTERN})[\"']?[ \t]*[=:][ \t]*[\"']?"
        r"(?:bearer\s+|basic\s+)?(?P<value>[A-Za-z0-9_\-+/=]{16,})"
    ),
}

_ENV_FILE_GLOBS: Final = (".env", ".env.*", "*.env", "*.env.*", ".envrc")


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
    return any(suffix.lower() in DATA_SUFFIXES for suffix in path.suffixes)


def _is_env_file(path: Path) -> bool:
    name = path.name
    if name == ".env.example":
        return False
    return name.startswith(".env") or name == ".envrc" or name.endswith(".env") or ".env." in name


def _is_placeholder(value: str) -> bool:
    return any(marker in value for marker in PLACEHOLDER_MARKERS) or len(set(value)) <= 2


def _local_secret_values() -> tuple[str, ...]:
    """Credential values from this machine: the environment at import time plus any local
    (git-ignored) env files in the repo root. Used only for matching; never printed."""
    values = {os.environ.get(name, "").strip() for name in CREDENTIAL_ENV_VARS}
    for pattern in _ENV_FILE_GLOBS:
        for env_file in REPO.glob(pattern):
            if env_file.name == ".env.example" or not env_file.is_file():
                continue
            for line in env_file.read_text(encoding="utf-8", errors="replace").splitlines():
                key, sep, value = line.removeprefix("export ").partition("=")
                if sep and key.strip() in CREDENTIAL_ENV_VARS:
                    values.add(value.strip().strip("'\""))
    return tuple(sorted(v for v in values if len(v) >= 8))


# Captured at import, before the autouse fixture scrubs credentials from the environment.
_LOCAL_SECRET_VALUES: Final = _local_secret_values()


def find_secret_like_strings(text: str) -> list[tuple[int, str]]:
    """(line number, pattern kind) for every secret-looking string in ``text``."""
    hits: list[tuple[int, str]] = []
    for kind, pattern in _SECRET_SHAPES.items():
        for match in pattern.finditer(text):
            value = match.groupdict().get("value") or match.group(0)
            if _is_placeholder(value):
                continue
            if kind == "sensitive-assignment" and not (
                re.search(r"[A-Za-z]", value) and re.search(r"\d", value)
            ):
                continue
            hits.append((text.count("\n", 0, match.start()) + 1, kind))
    return hits


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
        if _is_data_file(p)
        and not _rel(p).startswith("data_ref/")
        and _rel(p) not in NON_DATA_ALLOWLIST
    ]
    assert not misplaced, f"data-like files outside data_ref/: {misplaced}"


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
        assert path.suffix.lower() in DATA_REF_TABLE_SUFFIXES, (
            f"unexpected file in data_ref/: {rel}"
        )
        assert rel in by_path, f"data_ref/{rel} has no source note in data_ref/SOURCES.yaml"
    for rel in by_path:
        assert (REPO / "data_ref" / rel).is_file(), f"SOURCES.yaml lists missing file {rel}"


def test_no_env_files_committed() -> None:
    env_files = [_rel(p) for p in committable_files() if _is_env_file(p)]
    assert not env_files, f"never commit env files: {env_files}"


@pytest.mark.parametrize(
    ("name", "is_env"),
    [
        (".env", True),
        (".env.local", True),
        ("dgx.env", True),
        ("prod.env.bak", True),
        (".envrc", True),
        (".env.example", False),
        ("environment.yml", False),
    ],
)
def test_env_file_detection(name: str, is_env: bool) -> None:
    assert _is_env_file(Path(name)) is is_env


def test_env_example_lists_every_credential_with_empty_values() -> None:
    lines = (REPO / ".env.example").read_text(encoding="utf-8").splitlines()
    assignments = dict(
        line.split("=", 1) for line in lines if line.strip() and not line.lstrip().startswith("#")
    )
    missing = [name for name in CREDENTIAL_ENV_VARS if name not in assignments]
    filled = [name for name in CREDENTIAL_ENV_VARS if assignments.get(name, "").strip()]
    assert not missing, f".env.example must list {missing}"
    assert not filled, f".env.example must not contain values for {filled}"  # names only
    assert "MJ_DATA_DIR" in assignments


def test_no_secrets_in_committable_files() -> None:
    offenders: list[str] = []
    for path in committable_files():
        text = path.read_bytes().decode("utf-8", errors="replace")  # binary files too
        offenders.extend(
            f"{_rel(path)}:{line}: {kind}" for line, kind in find_secret_like_strings(text)
        )
        for value in _LOCAL_SECRET_VALUES:
            if value in text:
                offenders.append(f"{_rel(path)}: contains a credential value from your env/.env")
    assert not offenders, f"secret-like strings found (values not shown): {offenders}"


def _fake(*parts: str) -> str:
    """Assemble secret-shaped test strings at runtime, so this file never contains them."""
    return "".join(parts)


@pytest.mark.parametrize(
    "line",
    [
        _fake(
            "FRED = 'https://api.stlouisfed.org/fred/series/observations?",
            "api_key=",
            "0123456789abcdef" * 2,
            "'",
        ),
        _fake("MASSIVE_API_KEY=", "Qw3rTy7uIoP9aSdF", "2gHjK4lZxCvBnM1q"),
        _fake("aws_secret_access_key: '", "wJalrXUtnFEMI7K7MDENG", "bPxRfiCYa1b2c3d4e5f'"),
        _fake("headers = {'Authorization': 'Bearer ", "abcDEF123456", "ghiJKL789'}"),
    ],
)
def test_the_scanner_catches_this_projects_key_formats(line: str) -> None:
    assert find_secret_like_strings(line), line


@pytest.mark.parametrize(
    "line",
    [
        "api_key=EXAMPLE0123456789abcdef",
        "password=settings.credentials.require",
        "token: Final = 'mjepa-harness'",
        "FRED_API_KEY=",
        "apiKey=${MASSIVE_API_KEY}",
        "MASSIVE_API_KEY=\nMASSIVE_S3_ACCESS_KEY_ID=",  # empty value: next line is not a value
    ],
)
def test_the_scanner_ignores_placeholders_and_code(line: str) -> None:
    assert not find_secret_like_strings(line), line


_IGNORED = [
    ".env",
    ".env.local",
    "dgx.env",
    ".envrc",
    "data/raw/x.csv",
    "prices.parquet",
    "catalog/mjepa.duckdb",
    "shard.00000.mds.zstd",
    "day_aggs/2020-03-02.csv.gz",
    ".venv/bin/python",
]
_VISIBLE = [".env.example", "data_ref/calendars/fomc.csv", "configs/endpoint.yaml", "uv.lock"]


@pytest.fixture
def gitignore_only_repo(tmp_path: Path) -> Path:
    """A fresh repo holding only the committed .gitignore (no global/local excludes)."""
    git = _git()
    repo = tmp_path / "ignore-probe"
    repo.mkdir()
    subprocess.run([git, "init", "-q", str(repo)], check=True, timeout=30)
    shutil.copy(REPO / ".gitignore", repo / ".gitignore")
    return repo


def _check_ignore(repo: Path, path: str) -> int:
    return subprocess.run(
        [
            _git(),
            "-C",
            str(repo),
            "-c",
            "core.excludesFile=" + os.devnull,
            "check-ignore",
            "-q",
            "--no-index",
            path,
        ],
        check=False,
        timeout=30,
    ).returncode


@pytest.mark.parametrize("path", _IGNORED)
def test_committed_gitignore_covers_secret_and_data_paths(
    gitignore_only_repo: Path, path: str
) -> None:
    assert _check_ignore(gitignore_only_repo, path) == 0, f"{path} is not git-ignored"


@pytest.mark.parametrize("path", _VISIBLE)
def test_committed_gitignore_keeps_committed_files_visible(
    gitignore_only_repo: Path, path: str
) -> None:
    assert _check_ignore(gitignore_only_repo, path) == 1, f"{path} must not be git-ignored"
