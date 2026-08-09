"""Command-line interface."""

# Lazy UI/API imports are intentional to keep CLI startup lightweight.
# pylint: disable=import-outside-toplevel

import asyncio
import sys
from pathlib import Path
from typing import Annotated

import typer
from loguru import logger
from pydantic import ValidationError
from rich.console import Console
from rich.progress import Progress

from referral_checker.exceptions import AuthenticationError
from referral_checker.io import export_summary, parse_codes
from referral_checker.models import RunSummary
from referral_checker.presentation import print_summary
from referral_checker.service import ProgressCallback
from referral_checker.settings import Settings, load_settings

app = typer.Typer(
    add_completion=True,
    no_args_is_help=True,
    rich_markup_mode="markdown",
    help="Validate Zeabur referral codes concurrently.",
)
console = Console()


async def validate_referral_codes(
    codes: list[str],
    settings: Settings | None = None,
    on_progress: ProgressCallback | None = None,
) -> RunSummary:
    """Load and run the GraphQL validation workflow."""
    from referral_checker.api import validate_referral_codes as validate_codes

    return await validate_codes(codes, settings, on_progress)


def _run_tui(codes: list[str]) -> None:
    from referral_checker.tui import ReferralTui

    ReferralTui(codes).run()


def _run_gui(native: bool, host: str, port: int) -> None:
    from referral_checker.gui import run_gui

    run_gui(native, host, port)


def _configure_logging(verbose: bool) -> None:
    logger.remove()
    logger.add(sys.stderr, level="DEBUG" if verbose else "INFO", diagnose=False)


def _settings_or_error(**overrides: object) -> Settings:
    """Load settings and present a missing cookie as a CLI usage error."""
    try:
        return load_settings(**overrides)
    except ValidationError as error:
        raise typer.BadParameter(
            "REFCHECK_COOKIE must be set to a non-empty Cookie header value.",
            param_hint="REFCHECK_COOKIE",
        ) from error


@app.command(help="Validate referral codes from a Python list or delimited text.")
def check(
    codes: Annotated[
        str,
        typer.Argument(
            help='Python list, JSON list, or delimited codes, e.g. `["A", "B"]`.'
        ),
    ],
    concurrency: Annotated[int, typer.Option(min=1, max=64)] = 8,
    rate: Annotated[float, typer.Option(min=0.1, max=50)] = 4.0,
    output: Annotated[
        Path | None, typer.Option(help="Optional .json or .csv export.")
    ] = None,
    verbose: Annotated[bool, typer.Option("--verbose", "-v")] = False,
) -> None:
    """Validate referral codes."""
    _configure_logging(verbose)
    try:
        parsed = parse_codes(codes)
    except ValueError as error:
        raise typer.BadParameter(str(error), param_hint="codes") from error
    settings = _settings_or_error(concurrency=concurrency, requests_per_second=rate)

    async def _run() -> None:
        with Progress(console=console) as progress:
            task = progress.add_task("Validating", total=len(parsed))

            def _update(_result: object, _current: int, _total: int) -> None:
                progress.advance(task)

            summary = await validate_referral_codes(parsed, settings, _update)
        print_summary(summary, console)
        if output is not None:
            console.print(f"Exported: {export_summary(summary, output)}")
        if summary.error_count:
            raise typer.Exit(code=2)
        if not summary.valid_count:
            raise typer.Exit(code=1)

    try:
        asyncio.run(_run())
    except AuthenticationError as error:
        console.print(f"[red]{error}[/red]")
        raise typer.Exit(code=2) from error


@app.command(help="Launch the terminal interface.")
def tui(codes: Annotated[str, typer.Argument()] = "[]") -> None:
    """Launch the terminal interface."""
    try:
        parsed = parse_codes(codes)
    except ValueError as error:
        raise typer.BadParameter(str(error), param_hint="codes") from error
    _settings_or_error()
    _run_tui(parsed)


@app.command(help="Launch the browser or native graphical interface.")
def gui(
    native: Annotated[
        bool, typer.Option(help="Open as a native window when supported.")
    ] = False,
    host: Annotated[
        str, typer.Option(help="Bind address for browser mode.")
    ] = "127.0.0.1",
    port: Annotated[int, typer.Option(min=1, max=65535)] = 8080,
) -> None:
    """Launch the graphical interface."""
    _settings_or_error()
    _run_gui(native, host, port)


if __name__ == "__main__":
    app()
