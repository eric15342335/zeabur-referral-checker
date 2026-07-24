"""Public validation workflow."""

from referral_checker.client import GraphQLReferralValidator
from referral_checker.exceptions import AuthenticationError
from referral_checker.models import RunSummary
from referral_checker.service import ProgressCallback, normalize_codes, run_validation
from referral_checker.settings import Settings, load_settings


async def validate_referral_codes(
    codes: list[str],
    settings: Settings | None = None,
    on_progress: ProgressCallback | None = None,
) -> RunSummary:
    """Validate referral codes through the configured GraphQL endpoint."""
    resolved = settings or load_settings()
    normalized = normalize_codes(codes)
    if not normalized:
        return RunSummary.from_results([], elapsed_ms=0)
    try:
        async with GraphQLReferralValidator(resolved) as validator:
            return await run_validation(
                normalized, validator, resolved.concurrency, on_progress
            )
    except* AuthenticationError as errors:
        raise errors.exceptions[0] from errors
