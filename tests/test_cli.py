from collections.abc import Awaitable, Callable

import pytest
from typer.testing import CliRunner

from referral_checker import cli
from referral_checker.models import ReferralResult, RunSummary, Status
from referral_checker.settings import Settings

runner = CliRunner()
type ProgressCallback = Callable[[ReferralResult, int, int], Awaitable[None] | None]


def summary(status: Status) -> RunSummary:
    return RunSummary.from_results(
        [ReferralResult(code="CODE", status=status, latency_ms=1)], elapsed_ms=2
    )


@pytest.mark.parametrize(
    ("status", "expected_exit"),
    [(Status.VALID, 0), (Status.INVALID, 1), (Status.ERROR, 2)],
)
def test_check_exit_contract(
    monkeypatch: pytest.MonkeyPatch, status: Status, expected_exit: int
) -> None:
    monkeypatch.setenv("REFCHECK_COOKIE", "test-cookie")

    async def fake_validate(
        codes: list[str],
        settings: Settings | None,
        on_progress: ProgressCallback | None,
    ) -> RunSummary:
        assert codes == ["CODE"]
        assert settings is not None
        result = summary(status)
        if on_progress is not None:
            outcome = on_progress(result.results[0], 1, 1)
            if outcome is not None:
                await outcome
        return result

    monkeypatch.setattr(cli, "validate_referral_codes", fake_validate)
    result = runner.invoke(cli.app, ["check", '["CODE"]'])
    assert result.exit_code == expected_exit
    assert "CODE" in result.stdout


def test_check_rejects_scalar_input() -> None:
    result = runner.invoke(cli.app, ["check", "42"])
    assert result.exit_code == 2
    assert "input must be a Python list" in result.output
