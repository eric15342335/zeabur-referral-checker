"""Rich result presentation."""

from rich.console import Console
from rich.table import Table

from referral_checker.models import RunSummary, Status


def result_table(summary: RunSummary) -> Table:
    """Build a table for a validation summary."""
    table = Table(title=f"Referral results · {summary.elapsed_ms:.0f} ms")
    for column in ("Code", "Status", "Discount", "Reason", "Latency", "Attempts"):
        table.add_column(column)
    styles = {Status.VALID: "green", Status.INVALID: "yellow", Status.ERROR: "red"}
    for result in summary.results:
        style = styles[result.status]
        table.add_row(
            result.code,
            f"[{style}]{result.status.value}[/{style}]",
            "—" if result.discount_percent is None else f"{result.discount_percent}%",
            result.reason or "—",
            f"{result.latency_ms:.0f} ms",
            str(result.attempts),
        )
    table.caption = (
        f"valid={summary.valid_count} · invalid={summary.invalid_count} "
        f"· errors={summary.error_count}"
    )
    return table


def print_summary(summary: RunSummary, console: Console | None = None) -> None:
    """Print a validation summary."""
    (console or Console()).print(result_table(summary))
