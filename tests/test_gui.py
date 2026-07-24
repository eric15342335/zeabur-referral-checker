from collections.abc import Awaitable

import pytest
from nicegui.client import Client
from nicegui.elements.button import Button
from nicegui.elements.table import Table
from nicegui.elements.textarea import Textarea
from nicegui.page import page

from referral_checker import gui
from referral_checker.models import ReferralResult, RunSummary, Status
from referral_checker.service import ProgressCallback
from referral_checker.settings import Settings


@pytest.mark.asyncio
async def test_gui_populates_the_table_from_progress(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_validate(
        codes: list[str],
        settings: Settings | None = None,
        on_progress: ProgressCallback | None = None,
    ) -> RunSummary:
        del settings
        results = [
            ReferralResult(
                code=code,
                status=Status.VALID,
                discount_percent=10,
                latency_ms=1,
            )
            for code in codes
        ]
        for current, result in enumerate(results, start=1):
            if on_progress is not None:
                outcome = on_progress(result, current, len(results))
                if isinstance(outcome, Awaitable):
                    await outcome
        return RunSummary.from_results(results, elapsed_ms=1)

    monkeypatch.setattr(gui, "validate_referral_codes", fake_validate)
    with Client(page("/")) as client:
        gui._build_gui()
        textarea = next(
            element
            for element in client.elements.values()
            if isinstance(element, Textarea)
        )
        table = next(
            element
            for element in client.elements.values()
            if isinstance(element, Table)
        )
        button = next(
            element
            for element in client.elements.values()
            if isinstance(element, Button)
        )
        textarea.value = '["CODE1", "CODE2"]'
        handler = next(iter(button._event_listeners.values())).handler
        assert handler is not None
        outcome = handler()
        if isinstance(outcome, Awaitable):
            await outcome

    assert [row["code"] for row in table.rows] == ["CODE1", "CODE2"]
