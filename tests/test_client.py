from collections.abc import Mapping
from typing import Any

import pytest
from gql import GraphQLRequest
from gql.transport.exceptions import (
    TransportError,
    TransportQueryError,
    TransportServerError,
)
from tenacity.wait import wait_base, wait_none

from referral_checker import client
from referral_checker.client import GraphQLReferralValidator
from referral_checker.exceptions import AuthenticationError
from referral_checker.models import Status
from referral_checker.settings import load_settings

ENDPOINT = "https://api-bunny.zeabur.com/graphql"
COOKIE = "session=test"
type Outcome = Mapping[str, Any] | BaseException


class FakeExecutor:
    def __init__(self, outcomes: list[Outcome]) -> None:
        self.outcomes = iter(outcomes)
        self.requests: list[GraphQLRequest] = []

    async def __call__(self, request: GraphQLRequest) -> Mapping[str, Any]:
        self.requests.append(request)
        outcome = next(self.outcomes)
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome


@pytest.mark.asyncio
async def test_graphql_contract_and_response_mapping() -> None:
    executor = FakeExecutor(
        [
            {
                "validateReferralCode": {
                    "valid": True,
                    "discountPercent": 10,
                    "reason": "",
                    "__typename": "ValidateReferralCodeResult",
                }
            }
        ]
    )
    settings = load_settings(
        endpoint=ENDPOINT, cookie=COOKIE, retries=1, requests_per_second=50
    )

    async with GraphQLReferralValidator(settings, executor) as validator:
        result = await validator.validate("ABC")

    payload = executor.requests[0].payload
    assert payload["operationName"] == "ValidateReferralCode"
    assert payload["variables"] == {"code": "ABC", "orderType": "RENT_SERVER"}
    assert "validateReferralCode" in payload["query"]
    assert result.status is Status.VALID
    assert result.discount_percent == 10


@pytest.mark.asyncio
async def test_transport_failure_is_retried_and_returned_as_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def no_wait(**_: object) -> wait_base:
        return wait_none()

    monkeypatch.setattr(client, "wait_exponential_jitter", no_wait)
    executor = FakeExecutor(
        [TransportError("unavailable"), TransportError("unavailable")]
    )
    settings = load_settings(
        endpoint=ENDPOINT, cookie=COOKIE, retries=2, requests_per_second=50
    )

    async with GraphQLReferralValidator(settings, executor) as validator:
        result = await validator.validate("ABC")

    assert len(executor.requests) == 2
    assert result.status is Status.ERROR
    assert result.attempts == 2
    assert "TransportError" in result.reason


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "error",
    [
        TransportServerError("Unauthorized", code=401),
        TransportQueryError(
            "Unauthenticated",
            errors=[{"extensions": {"code": "UNAUTHENTICATED"}}],
        ),
    ],
)
async def test_authentication_failure_is_not_retried(error: TransportError) -> None:
    executor = FakeExecutor([error])
    settings = load_settings(
        endpoint=ENDPOINT, cookie=COOKIE, retries=2, requests_per_second=50
    )

    async with GraphQLReferralValidator(settings, executor) as validator:
        with pytest.raises(AuthenticationError, match="refresh REFCHECK_COOKIE"):
            await validator.validate("ABC")

    assert len(executor.requests) == 1
