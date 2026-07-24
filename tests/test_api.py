from typing import Self

import pytest

from referral_checker import api
from referral_checker.exceptions import AuthenticationError
from referral_checker.models import ReferralResult
from referral_checker.settings import load_settings


@pytest.mark.asyncio
async def test_api_unwraps_batch_authentication_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class AuthenticationFailingValidator:
        def __init__(self, _: object) -> None:
            pass

        async def __aenter__(self) -> Self:
            return self

        async def __aexit__(self, *_: object) -> None:
            pass

        async def validate(self, _: str) -> ReferralResult:
            raise AuthenticationError("cookie rejected")

    monkeypatch.setattr(api, "GraphQLReferralValidator", AuthenticationFailingValidator)

    with pytest.raises(AuthenticationError, match="cookie rejected"):
        await api.validate_referral_codes(
            ["CODE"], settings=load_settings(cookie="session=test")
        )
