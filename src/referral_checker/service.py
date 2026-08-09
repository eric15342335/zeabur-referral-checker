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
    stripped_codes = (code.strip() for code in codes)
    return list(dict.fromkeys(code for code in stripped_codes if code))


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

    async def _validate_one(code: str) -> ReferralResult:
        nonlocal completed
        async with semaphore:
            result = await validator.validate(code)
        completed += 1
        if on_progress is not None:
            outcome = on_progress(result, completed, len(codes))
            if inspect.isawaitable(outcome):
                await outcome
        return result

    async with asyncio.TaskGroup() as group:
        tasks = [
            group.create_task(_validate_one(code), name=f"referral:{code}")
            for code in codes
        ]

    results = [task.result() for task in tasks]
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
