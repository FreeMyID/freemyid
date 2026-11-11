"""Human checklist rendering with synthetic data and no store or checklist loading."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from typer.testing import CliRunner

from freemyid import checklist_state, cli
from freemyid.models import Checklist


@pytest.mark.parametrize("done", [False, True], ids=["unfinished", "finished"])
@pytest.mark.parametrize("optional", [False, True], ids=["minimal", "optional-sections"])
def test_checklist_show_text(
    monkeypatch: pytest.MonkeyPatch, done: bool, optional: bool,
) -> None:
    item = Checklist(
        id="fake_checklist",
        title="Fake checklist [bold]notice[/bold]",
        why="Practice [read the notice] first.",
        url="https://example.invalid/fake-checklist",
        cost="Free sample",
        time_needed="Two sample minutes",
        steps=["Read [bold]sample[/bold].", "Keep the fake receipt."],
        how_to_undo="Reopen the fake example.",
        source_urls=["https://example.invalid/fake-source"],
        date_checked="2026-11-07",
        verification="partial",
        need_on_hand=["Fake [bold]reference[/bold]"] if optional else [],
        status_note="Sample [bold]note[/bold]" if optional else None,
    )
    store = object()
    profile = SimpleNamespace(id="fake-profile")

    def context(
        selected: str | None, cid: str | None = None,
    ) -> tuple[None, Checklist, object, SimpleNamespace]:
        assert selected is None
        assert cid == item.id
        return None, item, store, profile

    def ticks(actual_store: object, profile_id: str) -> dict[str, SimpleNamespace]:
        assert actual_store is store
        assert profile_id == profile.id
        return {item.id: SimpleNamespace(
            done=True, at=datetime(2026, 11, 8, 12, tzinfo=UTC),
        )} if done else {}

    monkeypatch.setattr(cli, "_checklist_context", context)
    monkeypatch.setattr(checklist_state, "ticks", ticks)
    result = CliRunner().invoke(cli.app, ["checklist", "show", item.id])
    assert result.exit_code == 0, result.output
    output = result.stdout
    status = "done on 2026-11-08" if done else "not done yet"
    for text in (
        item.title, f"Status: {status}", f"Why: {item.why}", f"Cost: {item.cost}",
        f"Time: {item.time_needed}", f"Website: {item.url}",
        f"How to undo: {item.how_to_undo}",
        f"Checked 2026-11-07. When finished: freemyid checklist done {item.id}",
    ):
        assert text in output
    positions = [output.index("Steps:")]
    for number, step in enumerate(item.steps, 1):
        line = f"{number}. {step}"
        assert output.count(line) == 1
        positions.append(output.index(line))
    assert positions == sorted(positions)
    if optional:
        assert "Have these ready:" in output
        assert f"- {item.need_on_hand[0]}" in output
        assert f"Note: {item.status_note}" in output
    else:
        assert "Have these ready:" not in output
        assert "Note:" not in output
