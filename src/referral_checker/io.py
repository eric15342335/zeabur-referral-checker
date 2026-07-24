"""Input parsing and result export."""

import ast
import csv
from pathlib import Path
from typing import Any

import orjson

from referral_checker.models import RunSummary
from referral_checker.service import normalize_codes

_CSV_FIELDS = (
    "code",
    "status",
    "discount_percent",
    "reason",
    "latency_ms",
    "attempts",
    "checked_at",
    "valid",
)


def parse_codes(raw: str) -> list[str]:
    """Parse a Python or JSON list, comma-separated text, or line-separated text."""
    try:
        value: Any = ast.literal_eval(raw)
    except (SyntaxError, ValueError):
        value = raw.replace(",", "\n").splitlines()
    if not isinstance(value, list):
        raise ValueError("input must be a Python list or delimited text")
    if not all(isinstance(item, str) for item in value):
        raise ValueError("every referral code must be a string")
    return normalize_codes(value)


def export_summary(summary: RunSummary, destination: Path) -> Path:
    """Export a validation summary as JSON or CSV."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.suffix.lower() == ".json":
        destination.write_bytes(
            orjson.dumps(summary.model_dump(mode="json"), option=orjson.OPT_INDENT_2)
        )
    elif destination.suffix.lower() == ".csv":
        rows = [result.model_dump(mode="json") for result in summary.results]
        with destination.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=_CSV_FIELDS)
            writer.writeheader()
            writer.writerows(rows)
    else:
        raise ValueError("output suffix must be .json or .csv")
    return destination
