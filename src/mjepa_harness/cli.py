"""``mjepa``: the harness command-line interface.

Output for humans goes to stdout; logs go to stderr. Everything the CLI prints that
could echo user or remote input (error messages, table cells) passes through the
redactor and is markup-escaped. Typer's pretty tracebacks are disabled because they
print local variables (which can hold credentials); unexpected errors are logged by
:func:`main` through the redacting logging setup instead.
"""

import importlib
import logging
import os
import platform
import sys
from pathlib import Path
from typing import Annotated, Final

import typer
import yaml
from rich.console import Console
from rich.markup import escape
from rich.table import Table
from rich.text import Text

from mjepa_harness import __version__
from mjepa_harness.config import ConfigError, HarnessConfig, fingerprint, load_harness_config
from mjepa_harness.log import configure_logging, redact
from mjepa_harness.paths import DataLayout, UnsafeDataDirError, check_data_dir_safe, find_repo_root
from mjepa_harness.provenance import code_version
from mjepa_harness.settings import CREDENTIAL_PURPOSE, Settings

logger = logging.getLogger(__name__)

CONFIG_NAMES: Final = ("sources", "universe", "splits", "events", "endpoint")

app = typer.Typer(
    name="mjepa",
    help="Point-in-time research harness for the market-jepa paper.",
    no_args_is_help=True,
    add_completion=False,
    pretty_exceptions_enable=False,
)
config_app = typer.Typer(help="Inspect and validate the YAML configs.", no_args_is_help=True)
app.add_typer(config_app, name="config")


def _console() -> Console:
    return Console(highlight=False)


def _settings(ctx: typer.Context) -> Settings:
    settings = ctx.find_root().obj
    if not isinstance(settings, Settings):  # pragma: no cover - set by the root callback
        raise RuntimeError("settings not initialised")
    return settings


def _version_callback(value: bool) -> None:
    if value:
        _console().print(f"mjepa-harness {__version__} ({code_version()})")
        raise typer.Exit


@app.callback()
def _root(
    ctx: typer.Context,
    data_dir: Annotated[
        Path | None,
        typer.Option(
            "--data-dir",
            help="Data root. Default: $MJ_DATA_DIR, else ~/data/market-jepa.",
            show_default=False,
        ),
    ] = None,
    config_dir: Annotated[
        Path | None,
        typer.Option(
            "--config-dir",
            help="YAML config directory. Default: $MJ_CONFIG_DIR, else the repo's configs/.",
            show_default=False,
        ),
    ] = None,
    log_level: Annotated[
        str | None,
        typer.Option(
            "--log-level", help="DEBUG, INFO, WARNING or ERROR. Default: $MJ_LOG_LEVEL or INFO."
        ),
    ] = None,
    log_format: Annotated[
        str | None,
        typer.Option("--log-format", help="text or json. Default: $MJ_LOG_FORMAT or text."),
    ] = None,
    version: Annotated[
        bool,
        typer.Option(
            "--version", callback=_version_callback, is_eager=True, help="Show version and exit."
        ),
    ] = False,
) -> None:
    """Point-in-time research harness for the market-jepa paper."""
    try:
        settings = Settings.from_env(
            data_dir=data_dir, config_dir=config_dir, log_level=log_level, log_format=log_format
        )
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc
    configure_logging(
        settings.log_level, settings.log_format, secrets=settings.credentials.secret_values()
    )
    ctx.obj = settings


def _load_configs_or_exit(settings: Settings) -> HarnessConfig:
    try:
        return load_harness_config(settings.config_dir)
    except ConfigError as exc:
        _console().print(f"[bold red]config error:[/] {escape(redact(str(exc)))}")
        raise typer.Exit(code=1) from exc


def _repo_roots() -> list[Path]:
    roots = {find_repo_root(Path(__file__).resolve().parent), find_repo_root(Path.cwd())}
    return sorted(root for root in roots if root is not None)


@app.command()
def doctor(ctx: typer.Context) -> None:
    """Check Python, platform, libraries, configs, data directory and credentials.

    Credentials are reported as set/missing only; values are never printed.
    """
    settings = _settings(ctx)
    console = _console()
    table = Table(title="mjepa doctor", show_header=True, header_style="bold")
    table.add_column("check")
    table.add_column("status")
    table.add_column("detail", overflow="fold")
    failures = 0

    def add(check: str, status: str, detail: str) -> None:
        nonlocal failures
        if status == "FAIL":
            failures += 1
        table.add_row(check, status, Text(redact(detail)))

    add("mjepa-harness", "info", f"{__version__} ({code_version()})")
    py_ok = sys.version_info[:2] == (3, 12)
    add("python", "ok" if py_ok else "FAIL", f"{platform.python_version()} at {sys.executable}")
    add("platform", "info", f"{platform.system()} {platform.machine()}")
    for module_name in ("polars", "pyarrow", "duckdb"):
        try:
            module = importlib.import_module(module_name)
            add(module_name, "ok", str(getattr(module, "__version__", "?")))
        except ImportError as exc:  # pragma: no cover - dependency missing
            add(module_name, "FAIL", str(exc))

    try:
        cfg = load_harness_config(settings.config_dir)
        add("configs", "ok", f"{settings.config_dir} (5 files valid and consistent)")
        endpoint = cfg.endpoint
        add(
            "endpoint",
            "ok" if endpoint.status == "locked" else "warn",
            f"{endpoint.id} v{endpoint.version} status={endpoint.status} {fingerprint(endpoint)}",
        )
    except ConfigError as exc:
        add("configs", "FAIL", str(exc))

    data_dir = settings.data_dir
    try:
        for root in _repo_roots():
            check_data_dir_safe(data_dir, root)
        if data_dir.exists():
            writable = os.access(data_dir, os.W_OK)
            add(
                "data dir",
                "ok" if writable else "FAIL",
                f"{data_dir} (exists, writable={writable})",
            )
        else:
            add("data dir", "ok", f"{data_dir} (will be created on first fetch)")
    except UnsafeDataDirError as exc:
        add("data dir", "FAIL", str(exc))

    for name, present in settings.credentials.presence().items():
        detail = "set" if present else f"missing (needed for {CREDENTIAL_PURPOSE[name]})"
        add(f"env {name}", "ok" if present else "warn", detail)

    console.print(table)
    if failures:
        console.print(f"{failures} check(s) failed")
        raise typer.Exit(code=1)


@app.command()
def paths(ctx: typer.Context) -> None:
    """Show the data-directory layout (creates nothing)."""
    settings = _settings(ctx)
    table = Table(title=f"data layout (MJ_DATA_DIR={settings.data_dir})", header_style="bold")
    table.add_column("area")
    table.add_column("path", overflow="fold")
    table.add_column("exists")
    for area, path in DataLayout(settings.data_dir).describe().items():
        table.add_row(area, str(path), "yes" if path.exists() else "no")
    _console().print(table)


@config_app.command("validate")
def config_validate(ctx: typer.Context) -> None:
    """Validate all five configs and their cross-file consistency."""
    settings = _settings(ctx)
    cfg = _load_configs_or_exit(settings)
    table = Table(title=f"configs OK ({settings.config_dir})", header_style="bold")
    table.add_column("config")
    table.add_column("fingerprint")
    for name, digest in cfg.fingerprints().items():
        table.add_row(f"{name}.yaml", digest)
    _console().print(table)


@config_app.command("show")
def config_show(
    ctx: typer.Context,
    name: Annotated[
        str | None,
        typer.Argument(help="One of sources, universe, splits, events, endpoint. Default: all."),
    ] = None,
) -> None:
    """Print the validated configs as YAML (they contain no secrets)."""
    settings = _settings(ctx)
    if name is not None and name not in CONFIG_NAMES:
        raise typer.BadParameter(f"unknown config {name!r}; choose from {', '.join(CONFIG_NAMES)}")
    cfg = _load_configs_or_exit(settings)
    console = _console()
    for key, model in cfg.models().items():
        if name is not None and key != name:
            continue
        console.rule(f"{key}.yaml  {fingerprint(model)}")
        dumped = yaml.safe_dump(model.model_dump(mode="json"), sort_keys=False, allow_unicode=True)
        console.print(redact(dumped), markup=False, end="")


def main() -> None:
    """Console-script entry point."""
    # Install redaction before parsing arguments so that even early failures are logged
    # without secrets (credentials come from the environment); the root callback then
    # re-configures logging with the CLI options.
    configure_logging()
    try:
        app()
    except Exception:
        logger.exception("mjepa failed with an unexpected error")
        raise SystemExit(1) from None


if __name__ == "__main__":  # pragma: no cover
    main()
