"""Concurrent validation service."""

import asyncio
import inspect
import time
from collections.abc import Awaitable, Callable, Iterable, Sequence
from typing import Protocol

from loguru import logger

from referral_checker.models import ReferralResult, RunSummary

type ProgressCallback = Callable[[ReferralResult, int, int], Awaitable[None] | None]


class Validator(Protocol):  # pylint: disable=too-few-public-methods
    """Referral-code validator interface."""

    async def validate(self, code: str) -> ReferralResult:
        """Validate one code."""
        ...  # pylint: disable=unnecessary-ellipsis


def normalize_codes(codes: Iterable[str]) -> list[str]:
    """Trim, remove blanks, and deduplicate codes without reordering them."""
    return list(dict.fromkeys(code for raw in codes if (code := raw.strip())))


async def run_validation(
    codes: Sequence[str],
    validator: Validator,
    concurrency: int,
    on_progress: ProgressCallback | None = None,
) -> RunSummary:
    """Validate codes concurrently and preserve their input order."""
    started = time.perf_counter()
    semaphore = asyncio.Semaphore(concurrency)
    completed = 0
    ordered: list[ReferralResult | None] = [None] * len(codes)

    async def _validate_one(index: int, code: str) -> None:
        nonlocal completed
        async with semaphore:
            result = await validator.validate(code)
        ordered[index] = result
        completed += 1
        if on_progress is not None:
            outcome = on_progress(result, completed, len(codes))
            if inspect.isawaitable(outcome):
                await outcome

    async with asyncio.TaskGroup() as group:
        for index, code in enumerate(codes):
            group.create_task(_validate_one(index, code), name=f"referral:{code}")

    results: list[ReferralResult] = []
    for result in ordered:
        if result is None:
            raise RuntimeError("Validation task completed without a result")
        results.append(result)
    summary = RunSummary.from_results(
        results, elapsed_ms=(time.perf_counter() - started) * 1000
    )
    logger.info(
        "validated {} codes: {} valid, {} invalid, {} errors",
        len(results),
        summary.valid_count,
        summary.invalid_count,
        summary.error_count,
    )
    return summary
