import csv
from pathlib import Path

import orjson
import pytest

from referral_checker.io import export_summary, parse_codes
from referral_checker.models import ReferralResult, RunSummary, Status


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ('["A", "B"]', ["A", "B"]),
        ("[' A ', 'B', 'A']", ["A", "B"]),
        ("A,B", ["A", "B"]),
        ("A\nB", ["A", "B"]),
    ],
)
def test_parse_codes(raw: str, expected: list[str]) -> None:
    assert parse_codes(raw) == expected


@pytest.mark.parametrize("raw", ["42", '"ABC"', "('A', 'B')", "['A', 2]"])
def test_parse_codes_rejects_invalid_structures(raw: str) -> None:
    with pytest.raises(ValueError):
        parse_codes(raw)


def test_exported_json_and_csv_contain_results(tmp_path: Path) -> None:
    summary = RunSummary.from_results(
        [
            ReferralResult(
                code="A", status=Status.VALID, discount_percent=10, latency_ms=1
            )
        ],
        elapsed_ms=2,
    )
    json_path = export_summary(summary, tmp_path / "results.json")
    csv_path = export_summary(summary, tmp_path / "results.csv")

    assert orjson.loads(json_path.read_bytes())["valid_count"] == 1
    with csv_path.open(newline="", encoding="utf-8") as handle:
        row = next(csv.DictReader(handle))
    assert row["code"] == "A"
    assert row["status"] == "valid"
    assert row["discount_percent"] == "10"


def test_export_rejects_unknown_format(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="suffix"):
        export_summary(RunSummary.from_results([], elapsed_ms=0), tmp_path / "out.txt")
