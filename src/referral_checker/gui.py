"""NiceGUI interface."""

from nicegui import ui
from pydantic import ValidationError

from referral_checker.api import validate_referral_codes
from referral_checker.exceptions import AuthenticationError
from referral_checker.io import parse_codes
from referral_checker.models import ReferralResult


def _build_gui() -> None:
    """Build the graphical interface."""
    rows: list[dict[str, object]] = []
    columns = [
        {"name": name, "label": name.title(), "field": name, "sortable": True}
        for name in ("code", "status", "discount", "reason", "latency", "attempts")
    ]
    ui.label("Zeabur Referral Checker").classes("text-2xl font-bold")
    codes = ui.textarea(
        "Referral codes",
        placeholder='["CODE1", "CODE2"] or one per line',
    ).classes("w-full")
    progress = ui.linear_progress(value=0).props("instant-feedback")
    table = ui.table(columns=columns, rows=rows, row_key="code").classes("w-full")
    status = ui.label("Ready")
    button = ui.button("Validate")

    async def _check() -> None:
        try:
            parsed = parse_codes(codes.value or "")
        except ValueError as error:
            ui.notify(str(error), type="negative")
            return
        table.rows.clear()
        table.update()
        progress.value = 0
        button.disable()

        def _update(result: ReferralResult, current: int, total: int) -> None:
            table.rows.append(
                {
                    "code": result.code,
                    "status": result.status.value,
                    "discount": result.discount_percent,
                    "reason": result.reason,
                    "latency": round(result.latency_ms, 1),
                    "attempts": result.attempts,
                }
            )
            table.update()
            progress.value = current / total if total else 1

        try:
            summary = await validate_referral_codes(parsed, on_progress=_update)
            status.text = (
                f"{summary.valid_count} valid · {summary.invalid_count} invalid · "
                f"{summary.error_count} errors"
            )
        except AuthenticationError as error:
            status.text = str(error)
            ui.notify(str(error), type="negative")
        except ValidationError:
            message = "Set REFCHECK_COOKIE to a non-empty Cookie header value."
            status.text = message
            ui.notify(message, type="negative")
        finally:
            button.enable()

    button.on("click", _check)


def run_gui(native: bool = False, host: str = "127.0.0.1", port: int = 8080) -> None:
    """Run the browser or native graphical interface."""
    ui.run(
        root=_build_gui,
        title="Zeabur Referral Checker",
        native=native,
        reload=False,
        host=host,
        port=port,
    )
