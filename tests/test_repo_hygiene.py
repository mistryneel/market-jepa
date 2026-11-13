"""Rule 1, enforced: no data or secrets in git.

Two modes:
* **Working tree** (plain ``pytest``, CI). Every file git would commit is checked:
  tracked files plus untracked, non-ignored ones, listed with the developer's own git
  configuration so global excludes count.
* **Staged** (``scripts/hooks/pre-commit``). The hook exports the index, i.e. exactly
  what is being committed, into a temporary directory and sets ``MJEPA_HYGIENE_ROOT``.
  Every file there is checked.

Failure messages name files, lines and pattern kinds, never secret values.
"""

from __future__ import annotations

import contextlib
import json
import os
import re
import shutil
import subprocess
from collections.abc import Mapping
from datetime import date
from pathlib import Path
from typing import Any, Final

import pytest
import yaml

from mjepa_harness.log import SENSITIVE_KEY_PATTERN
from mjepa_harness.settings import CREDENTIAL_ENV_VARS

REPO: Final = Path(__file__).resolve().parents[1]
_STAGED_ROOT: Final = os.environ.get("MJEPA_HYGIENE_ROOT", "").strip()
ROOT: Final = Path(_STAGED_ROOT).resolve() if _STAGED_ROOT else REPO
"""What is scanned: the repository, or the exported index in staged (hook) mode."""

# The developer's own git configuration, captured at import before the autouse fixture
# makes git hermetic: "would git commit this?" depends on their global excludes.
_DEV_GIT_ENV: Final = {
    name: os.environ.get(name)
    for name in ("GIT_CONFIG_GLOBAL", "GIT_CONFIG_NOSYSTEM", "XDG_CONFIG_HOME", "HOME")
}

MAX_FILE_BYTES: Final = 1_000_000  # "under 1 MB"
DATA_SUFFIXES: Final = frozenset(
    {
        ".csv", ".tsv", ".parquet", ".feather", ".arrow", ".ipc", ".duckdb", ".db",
        ".sqlite", ".mds", ".zst", ".zstd", ".gz", ".zip", ".tar", ".h5", ".hdf5",
        ".npy", ".npz", ".pkl", ".pickle", ".xlsx", ".xls",
        # Raw payload formats the sources return (APIs, EDGAR, calendars) and notebooks,
        # whose outputs can hold data.
        ".json", ".jsonl", ".ndjson", ".xml", ".html", ".htm", ".txt", ".idx", ".sgml",
        ".dat", ".ipynb",
    }
)  # fmt: skip
TOOL_CONFIG_DIRS: Final = (".claude/", ".github/", ".devcontainer/", ".vscode/")
"""Tool configuration (e.g. settings.json) is not data; it is still scanned for secrets."""
NON_DATA_ALLOWLIST: Final = frozenset[str]()
"""Other repo-relative paths with a data-like suffix that are deliberately committed."""
DATA_REF_TABLE_SUFFIXES: Final = frozenset({".csv", ".tsv"})
DATA_REF_META_FILES: Final = frozenset({"README.md", "SOURCES.yaml"})

PLACEHOLDER_MARKERS: Final = ("EXAMPLE", "example", "REDACTED", "<", "${", "xxxx", "XXXX")
"""Values containing any of these are placeholders (all test fixtures use EXAMPLE)."""

_VALUE: Final = r"(?P<value>[A-Za-z0-9_\-+/=.~]{16,})"
_CRED_NAMES: Final = "|".join(CREDENTIAL_ENV_VARS)
_SECRET_SHAPES: Final = {
    "huggingface-token": re.compile(r"hf_[A-Za-z0-9]{30,}"),
    "aws-access-key-id": re.compile(r"(?:AKIA|ASIA)[0-9A-Z]{16}"),
    "private-key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"),
    "github-token": re.compile(r"ghp_[A-Za-z0-9]{36}|github_pat_[A-Za-z0-9_]{50,}"),
    "anthropic-key": re.compile(r"sk-ant-[A-Za-z0-9_-]{20,}"),
    # key=value, key: value, "key": "value", "key": ["value"], YAML list items.
    "sensitive-assignment": re.compile(
        rf"(?i)(?<![A-Za-z0-9])(?:{SENSITIVE_KEY_PATTERN})[\"']?[ \t]*[=:][ \t]*"
        r"(?:\[[ \t]*|\r?\n[ \t]*-[ \t]+)?[\"']?(?:bearer[ \t]+|basic[ \t]+)?" + _VALUE
    ),
    "bearer-token": re.compile(r"(?i)\bbearer[ \t]+" + _VALUE),
    "environ-assignment": re.compile(
        rf"(?:environ\[\s*|setdefault\(\s*|putenv\(\s*)[\"'](?:{_CRED_NAMES})[\"']"
        r"\s*\]?\s*[,=]\s*[\"']" + _VALUE
    ),
    "sql-secret": re.compile(r"(?i)\b(?:KEY_ID|SECRET|SESSION_TOKEN)\s+'" + _VALUE),
    "url-userinfo": re.compile(r"[a-z][a-z0-9+.-]*://[^/\s:@'\"]+:(?P<value>[^/\s@'\"]{8,})@"),
}
_ENV_FILE_GLOBS: Final = (".env", ".env.*", "*.env", "*.env.*", ".envrc")


def _git_binary() -> str:
    git = shutil.which("git")
    if git is None:
        pytest.skip("git not available")
    return git


def _dev_git_env() -> dict[str, str]:
    env = dict(os.environ)
    for name, value in _DEV_GIT_ENV.items():
        if value is None:
            env.pop(name, None)
        else:
            env[name] = value
    return env


def committable_files() -> list[Path]:
    """Files that would be committed (working-tree mode) or are being committed (staged)."""
    if _STAGED_ROOT:
        return sorted(p for p in ROOT.rglob("*") if p.is_file())
    if not (REPO / ".git").exists():
        pytest.skip("not a git checkout")
    result = subprocess.run(
        [
            _git_binary(), "-C", str(REPO),
            "ls-files", "-z", "--cached", "--others", "--exclude-standard",
        ],
        capture_output=True,
        check=True,
        timeout=60,
        env=_dev_git_env(),
    )  # fmt: skip
    rels = sorted({p for p in result.stdout.decode().split("\0") if p})
    return [REPO / rel for rel in rels if (REPO / rel).is_file()]


def _rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def _is_data_file(path: Path) -> bool:
    return any(suffix.lower() in DATA_SUFFIXES for suffix in path.suffixes)


def _is_env_file(path: Path) -> bool:
    name = path.name
    if name == ".env.example":
        return False
    return name.startswith(".env") or name == ".envrc" or name.endswith(".env") or ".env." in name


def _is_placeholder(value: str) -> bool:
    return (
        any(marker in value for marker in PLACEHOLDER_MARKERS)
        or value in CREDENTIAL_ENV_VARS  # a variable *name*, e.g. in a settings mapping
        or len(set(value)) <= 2
    )


def local_secret_values(roots: list[Path], env: Mapping[str, str]) -> tuple[str, ...]:
    """Credential values on this machine: ``env`` plus every (git-ignored) env file under
    ``roots``, searched recursively. Used only for matching; never printed."""
    values = {env.get(name, "").strip() for name in CREDENTIAL_ENV_VARS}
    for root in roots:
        for pattern in _ENV_FILE_GLOBS:
            for env_file in root.rglob(pattern):
                if not env_file.is_file() or not _is_env_file(env_file):
                    continue
                if ".venv" in env_file.parts or ".git" in env_file.parts:
                    continue
                for line in env_file.read_text(encoding="utf-8", errors="replace").splitlines():
                    key, sep, value = line.removeprefix("export ").partition("=")
                    if sep and key.strip() in CREDENTIAL_ENV_VARS:
                        values.add(value.strip().strip("'\""))
    return tuple(sorted(v for v in values if len(v) >= 8))


def _env_file_roots() -> list[Path]:
    """This checkout plus the main worktree (where a developer's .env often lives)."""
    roots = [REPO]
    git = shutil.which("git")
    if git is not None and (REPO / ".git").exists():
        common = subprocess.run(
            [git, "-C", str(REPO), "rev-parse", "--path-format=absolute", "--git-common-dir"],
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
        if common.returncode == 0 and common.stdout.strip():
            main = Path(common.stdout.strip()).parent
            if main != REPO and main.is_dir():
                roots.append(main)
    return roots


# Captured at import, before the autouse fixture scrubs credentials from the environment.
_LOCAL_SECRET_VALUES: Final = local_secret_values(_env_file_roots(), os.environ)


def _string_leaves(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [leaf for item in value.values() for leaf in _string_leaves(item)]
    if isinstance(value, list):
        return [leaf for item in value for leaf in _string_leaves(item)]
    return []


def _scannable_text(path: Path) -> str:
    raw = path.read_bytes().decode("utf-8", errors="replace")  # binary files too
    if path.suffix.lower() == ".ipynb":
        # JSON escaping hides quoted assignments: also scan the decoded cell strings.
        with contextlib.suppress(ValueError, AttributeError):
            raw += "\n" + "".join(_string_leaves(json.loads(raw).get("cells", [])))
    return raw


def find_secret_like_strings(text: str) -> list[tuple[int, str]]:
    """(line number, pattern kind) for every secret-looking string in ``text``."""
    hits: list[tuple[int, str]] = []
    for kind, pattern in _SECRET_SHAPES.items():
        for match in pattern.finditer(text):
            value = match.groupdict().get("value") or match.group(0)
            if _is_placeholder(value):
                continue
            mixed = re.search(r"[A-Za-z]", value) and re.search(r"\d", value)
            if "value" in match.groupdict() and kind != "url-userinfo" and not mixed:
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
        and not _rel(p).startswith(("data_ref/", *TOOL_CONFIG_DIRS))
        and _rel(p) not in NON_DATA_ALLOWLIST
    ]
    assert not misplaced, f"data-like files outside data_ref/: {misplaced}"


def test_data_ref_tables_have_source_notes() -> None:
    sources_text = (ROOT / "data_ref" / "SOURCES.yaml").read_text(encoding="utf-8")
    sources: Any = yaml.safe_load(sources_text) or {}
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

    for path in committable_files():
        if not _rel(path).startswith("data_ref/"):
            continue
        rel = path.relative_to(ROOT / "data_ref").as_posix()
        if rel in DATA_REF_META_FILES:
            continue
        assert path.suffix.lower() in DATA_REF_TABLE_SUFFIXES, f"unexpected file: data_ref/{rel}"
        assert rel in by_path, f"data_ref/{rel} has no source note in data_ref/SOURCES.yaml"
    for rel in by_path:
        assert (ROOT / "data_ref" / rel).is_file(), f"SOURCES.yaml lists missing file {rel}"


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
    lines = (ROOT / ".env.example").read_text(encoding="utf-8").splitlines()
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
        text = _scannable_text(path)
        offenders.extend(
            f"{_rel(path)}:{line}: {kind}" for line, kind in find_secret_like_strings(text)
        )
        if any(value in text for value in _LOCAL_SECRET_VALUES):
            offenders.append(f"{_rel(path)}: contains a credential value from your env/.env")
    assert not offenders, f"secret-like strings found (values not shown): {offenders}"


def _fake(*parts: str) -> str:
    """Assemble secret-shaped test strings at runtime, so this file never contains them."""
    return "".join(parts)


_SECRET = _fake("Qw3rTy7uIoP9aSdF", "2gHjK4lZxCvBnM1q")
_FRED_URL = "FRED = 'https://api.stlouisfed.org/fred/series/observations?api_key="


@pytest.mark.parametrize(
    "line",
    [
        _fake(_FRED_URL, "0123456789abcdef" * 2, "'"),
        _fake("MASSIVE_API_KEY=", _SECRET),
        _fake("aws_secret_access_key: '", "wJalrXUtnFEMI7K7MDENG", "bPxRfiCYa1b2c3d4e5f'"),
        _fake("headers = {'Authorization': 'Bearer ", "abcDEF123456", "ghiJKL789'}"),
        _fake('os.environ["MASSIVE_API_KEY"] = "', _SECRET, '"'),
        _fake("os.environ.setdefault('FRED_API_KEY', '", _SECRET, "')"),
        _fake("CREATE SECRET s (TYPE s3, KEY_ID '", _SECRET, "', SECRET '", _SECRET, "')"),
        _fake("s3://AKIDEXAMPL3:", "wJalr8XUtnFEMI", "@flatfiles/us_stocks_sip"),
        _fake("authorization:\n  - Bearer ", "abcDEF123456", "ghiJKL789"),
        _fake('{"token": ["', _SECRET, '"]}'),
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
        '"apiKeyEnvVar": "MASSIVE_API_KEY"',  # a mapping to a variable *name*
        "https://huggingface.co/datasets/fin-ai-lab/Market-1T-1Hz-2019H2-2020-sparse",
    ],
)
def test_the_scanner_ignores_placeholders_and_code(line: str) -> None:
    assert not find_secret_like_strings(line), line


def test_local_env_files_are_found_recursively_and_matched(tmp_path: Path) -> None:
    planted = _fake("plantedvalue", "9876543210")
    from_env = _fake("envvalue", "1234567890")
    (tmp_path / "nested" / "deeper").mkdir(parents=True)
    (tmp_path / "nested" / "deeper" / "dgx.env").write_text(f"export FRED_API_KEY={planted}\n")
    found = local_secret_values([tmp_path], {"HF_TOKEN": from_env})
    assert planted in found
    assert from_env in found


def test_notebook_outputs_are_scanned(tmp_path: Path) -> None:
    notebook = tmp_path / "scratch.ipynb"
    output = {"text": [_fake('"apiKey": "', _SECRET, '"')]}
    notebook.write_text(json.dumps({"cells": [{"source": ["x = 1"], "outputs": [output]}]}))
    assert find_secret_like_strings(_scannable_text(notebook))


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
    git = _git_binary()
    repo = tmp_path / "ignore-probe"
    repo.mkdir()
    subprocess.run([git, "init", "-q", str(repo)], check=True, timeout=30)
    shutil.copy(ROOT / ".gitignore", repo / ".gitignore")
    return repo


def _check_ignore(repo: Path, path: str) -> int:
    return subprocess.run(
        [
            _git_binary(), "-C", str(repo), "-c", "core.excludesFile=" + os.devnull,
            "check-ignore", "-q", "--no-index", path,
        ],
        check=False,
        timeout=30,
    ).returncode  # fmt: skip


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


def test_hook_scans_what_is_staged_not_the_working_tree(tmp_path: Path, repo_root: Path) -> None:
    """The pre-commit hook must judge the index, not the working copy."""
    hook = (repo_root / "scripts" / "hooks" / "pre-commit").read_text(encoding="utf-8")
    assert "checkout-index" in hook
    assert "MJEPA_HYGIENE_ROOT" in hook
    git = _git_binary()
    repo = tmp_path / "staged"
    repo.mkdir()
    subprocess.run([git, "init", "-q", str(repo)], check=True, timeout=30)
    (repo / "pull.py").write_text(_fake("MASSIVE_API_KEY=", _SECRET, "\n"))
    subprocess.run([git, "-C", str(repo), "add", "pull.py"], check=True, timeout=30)
    (repo / "pull.py").write_text("MASSIVE_API_KEY=\n")  # the working copy looks clean
    export = tmp_path / "export"
    subprocess.run(
        [git, "-C", str(repo), "checkout-index", "-a", f"--prefix={export}/"],
        check=True,
        timeout=30,
    )
    assert find_secret_like_strings((export / "pull.py").read_text())
    assert not find_secret_like_strings((repo / "pull.py").read_text())
