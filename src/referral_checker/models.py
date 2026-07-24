"""Validated result models."""

from collections.abc import Sequence
from datetime import UTC, datetime
from enum import StrEnum
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, computed_field


class Status(StrEnum):
    """Validation outcome."""

    VALID = "valid"
    INVALID = "invalid"
    ERROR = "error"


class ReferralResult(BaseModel):
    """Result for one referral code."""

    model_config = ConfigDict(frozen=True)

    code: str
    status: Status
    discount_percent: int | None = Field(default=None, ge=0, le=100)
    reason: str = ""
    latency_ms: float = Field(ge=0)
    attempts: int = Field(default=1, ge=1)
    checked_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @computed_field  # type: ignore[prop-decorator]
    @property
    def valid(self) -> bool:
        """Return whether the code is valid."""
        return self.status is Status.VALID


class RunSummary(BaseModel):
    """Results and aggregate counts for one run."""

    model_config = ConfigDict(frozen=True)

    results: tuple[ReferralResult, ...]
    elapsed_ms: float = Field(ge=0)

    @classmethod
    def from_results(cls, results: Sequence[ReferralResult], elapsed_ms: float) -> Self:
        """Create a summary while preserving result order."""
        return cls(results=tuple(results), elapsed_ms=elapsed_ms)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def valid_count(self) -> int:
        """Return the number of valid codes."""
        return sum(result.status is Status.VALID for result in self.results)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def invalid_count(self) -> int:
        """Return the number of invalid codes."""
        return sum(result.status is Status.INVALID for result in self.results)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def error_count(self) -> int:
        """Return the number of failed checks."""
        return sum(result.status is Status.ERROR for result in self.results)
