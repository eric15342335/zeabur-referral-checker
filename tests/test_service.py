import asyncio

import pytest

from referral_checker.models import ReferralResult, Status
from referral_checker.service import normalize_codes, run_validation


class DeterministicValidator:
    def __init__(self) -> None:
        self.active = 0
        self.peak = 0

    async def validate(self, code: str) -> ReferralResult:
        self.active += 1
        self.peak = max(self.peak, self.active)
        await asyncio.sleep(0.01 if code != "slow" else 0.02)
        self.active -= 1
        valid = code.startswith("ok")
        return ReferralResult(
            code=code,
            status=Status.VALID if valid else Status.INVALID,
            discount_percent=10 if valid else None,
            latency_ms=10,
        )


def test_normalize_codes_preserves_order() -> None:
    assert normalize_codes([" A ", "", "B", "A"]) == ["A", "B"]


@pytest.mark.asyncio
async def test_validation_concurrency_order_and_progress() -> None:
    validator = DeterministicValidator()
    updates: list[tuple[str, int, int]] = []

    async def update(result: ReferralResult, current: int, total: int) -> None:
        updates.append((result.code, current, total))

    summary = await run_validation(
        ["slow", "ok-1", "bad"], validator, concurrency=2, on_progress=update
    )

    assert [result.code for result in summary.results] == ["slow", "ok-1", "bad"]
    assert validator.peak == 2
    assert sorted(current for _, current, _ in updates) == [1, 2, 3]
    assert all(total == 3 for _, _, total in updates)
    counts = (summary.valid_count, summary.invalid_count, summary.error_count)
    assert counts == (1, 2, 0)


@pytest.mark.asyncio
async def test_empty_validation_does_not_call_validator() -> None:
    summary = await run_validation([], DeterministicValidator(), concurrency=1)
    assert summary.results == ()
