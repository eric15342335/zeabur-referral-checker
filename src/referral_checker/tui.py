"""Textual terminal interface."""

from typing import ClassVar

from pydantic import ValidationError
from textual import work
from textual.app import App, ComposeResult
from textual.binding import BindingType
from textual.containers import Horizontal, Vertical
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Header,
    Input,
    ProgressBar,
    Static,
)

from referral_checker.api import validate_referral_codes
from referral_checker.exceptions import AuthenticationError
from referral_checker.io import parse_codes
from referral_checker.models import ReferralResult


class ReferralTui(App[None]):
    """Interactive terminal interface."""

    CSS = """
    Screen { layout: vertical; }
    #controls { height: auto; }
    #codes { width: 1fr; }
    #status { height: 3; padding: 1; }
    DataTable { height: 1fr; }
    """
    BINDINGS: ClassVar[list[BindingType]] = [
        ("q", "quit", "Quit"),
        ("r", "run_checks", "Run"),
    ]

    def __init__(self, initial_codes: list[str] | None = None) -> None:
        super().__init__()
        self.initial_codes = initial_codes or []

    def compose(self) -> ComposeResult:
        """Compose the interface."""
        yield Header()
        with Vertical():
            with Horizontal(id="controls"):
                yield Input(
                    value=repr(self.initial_codes),
                    placeholder='["CODE1", "CODE2"]',
                    id="codes",
                )
                yield Button("Run", id="run", variant="primary")
                yield Button("Cancel", id="cancel", variant="warning")
            yield ProgressBar(id="progress", show_eta=True)
            yield Static("Ready", id="status")
            yield DataTable(id="results", zebra_stripes=True)
        yield Footer()

    def on_mount(self) -> None:
        """Initialize the results table."""
        self.query_one(DataTable).add_columns(
            "Code", "Status", "Discount", "Reason", "Latency", "Attempts"
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle run and cancel buttons."""
        if event.button.id == "run":
            self.action_run_checks()
        elif event.button.id == "cancel":
            self.workers.cancel_group(self, "validation")
            self.query_one("#status", Static).update("Cancelled")

    def action_run_checks(self) -> None:
        """Start a validation worker."""
        self.run_checks()

    @work(exclusive=True, group="validation")
    async def run_checks(self) -> None:
        """Run validation without blocking the interface."""
        try:
            codes = parse_codes(self.query_one("#codes", Input).value)
        except ValueError as error:
            self.notify(str(error), severity="error")
            return
        table = self.query_one("#results", DataTable)
        table.clear()
        progress = self.query_one("#progress", ProgressBar)
        progress.update(total=len(codes), progress=0)

        async def _update(result: ReferralResult, current: int, total: int) -> None:
            table.add_row(
                result.code,
                result.status.value,
                (
                    "—"
                    if result.discount_percent is None
                    else f"{result.discount_percent}%"
                ),
                result.reason or "—",
                f"{result.latency_ms:.0f} ms",
                str(result.attempts),
            )
            progress.update(total=total, progress=current)

        self.query_one("#status", Static).update(f"Checking {len(codes)} codes…")
        try:
            summary = await validate_referral_codes(codes, on_progress=_update)
        except AuthenticationError as error:
            self.query_one("#status", Static).update(str(error))
            self.notify(str(error), severity="error")
            return
        except ValidationError:
            message = "Set REFCHECK_COOKIE to a non-empty Cookie header value."
            self.query_one("#status", Static).update(message)
            self.notify(message, severity="error")
            return
        self.query_one("#status", Static).update(
            f"Done: {summary.valid_count} valid, {summary.invalid_count} invalid, "
            f"{summary.error_count} errors"
        )
