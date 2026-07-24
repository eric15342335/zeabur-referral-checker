import pytest
from pydantic import ValidationError

from referral_checker.settings import load_settings


def test_cookie_is_required(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("REFCHECK_COOKIE", raising=False)

    with pytest.raises(ValidationError, match="cookie"):
        load_settings(_env_file=None)


@pytest.mark.parametrize("cookie", ["", "   "])
def test_cookie_must_not_be_blank(monkeypatch: pytest.MonkeyPatch, cookie: str) -> None:
    monkeypatch.delenv("REFCHECK_COOKIE", raising=False)

    with pytest.raises(ValidationError, match="non-empty Cookie header value"):
        load_settings(_env_file=None, cookie=cookie)
