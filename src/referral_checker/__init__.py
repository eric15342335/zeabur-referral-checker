"""Public package API."""

from importlib import import_module
from typing import TYPE_CHECKING, cast

from referral_checker.models import ReferralResult, RunSummary
from referral_checker.settings import Settings

if TYPE_CHECKING:
    from referral_checker.api import validate_referral_codes

__all__ = ["ReferralResult", "RunSummary", "Settings", "validate_referral_codes"]


def __getattr__(name: str) -> object:
    if name == "validate_referral_codes":
        module = import_module("referral_checker.api")
        return cast(object, getattr(module, name))
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
