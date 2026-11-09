"""Guard the human-readable exposure result labels and manual-check details."""
from __future__ import annotations

from collections.abc import Callable
from types import SimpleNamespace
from typing import Any

import pytest
from typer import Typer
from typer.testing import CliRunner

from freemyid.exposure_models import ExposureEntry, ExposureListing, ExposureResult
from freemyid.models import MatchLevel

PROFILE_ID = "a" * 32


def _result(not_found_names: tuple[str, ...] = ("West Example", "East Example")) -> ExposureResult:
    """Build a result using only clearly synthetic site names and .example URLs."""
    entries = [
        ExposureEntry(
            broker_id="north_fake",
            broker_name="North Fake Search",
            status="found",
            match_level=MatchLevel.CONFIRMED,
            listings=[ExposureListing(
                url="https://north.example/listing/fake-marker",
                match_level=MatchLevel.CONFIRMED,
            )],
        ),
        ExposureEntry(
            broker_id="south_fake",
            broker_name="South Fake Search",
            status="found",
            match_level=MatchLevel.POSSIBLE,
            listings=[ExposureListing(
                url="https://south.example/listing/fake-marker",
                match_level=MatchLevel.POSSIBLE,
            )],
        ),
        ExposureEntry(
            broker_id="manual_fake",
            broker_name="Manual Fake Search",
            status="check_by_hand",
            reason="bot_blocked",
            check_url="https://manual.example/search/fake-marker",
        ),
        *[
            ExposureEntry(
                broker_id=f"not_found_{index}",
                broker_name=name,
                status="not_found",
            )
            for index, name in enumerate(not_found_names)
        ],
    ]
    return ExposureResult(profile_id=PROFILE_ID, score=28, practice_mode=True, entries=entries)


@pytest.fixture
def exposure_cli(monkeypatch: pytest.MonkeyPatch) -> tuple[CliRunner, Typer, Callable[..., Any]]:
    """Run the CLI without opening local files, a store, a keyring, or the network."""
    from freemyid import cli
    from freemyid.engine import exposure as exposure_module

    profile = SimpleNamespace(id=PROFILE_ID, label="Pat Testperson")
    fake_store = object()
    fake_registry = object()
    calls: list[dict[str, Any]] = []

    def scan(_store: object, profile_id: str, **kwargs: Any) -> ExposureResult:
        calls.append({"profile_id": profile_id, **kwargs})
        return _result()

    monkeypatch.setattr(cli, "_harden_home", lambda: None)
    monkeypatch.setattr(cli.logging_setup, "setup", lambda _verbose: None)
    monkeypatch.setattr(cli, "_open_store_or_fail", lambda: fake_store)
    monkeypatch.setattr(cli, "_select", lambda _store, _profile, _skipped: [profile])
    monkeypatch.setattr(cli, "_registry", lambda: fake_registry)
    monkeypatch.setattr(cli, "_search_engine_footer", lambda _store, _profiles: None)
    monkeypatch.setattr(exposure_module, "scan_exposure", scan)
    monkeypatch.setattr(
        exposure_module,
        "exposure_trend",
        lambda _store, _profile_id: SimpleNamespace(points=[]),
    )
    return CliRunner(), cli.app, lambda: calls


def test_exposure_text_reports_match_levels_urls_and_hand_check_reason(exposure_cli) -> None:
    runner, app, calls = exposure_cli

    result = runner.invoke(app, ["exposure", "--offline", "--profile", PROFILE_ID])

    assert result.exit_code == 0, result.output
    lines = [line.strip() for line in result.stdout.splitlines()]
    assert "Found North Fake Search: 1 listing(s) that is you" in lines
    assert "https://north.example/listing/fake-marker" in lines
    assert "Found South Fake Search: 1 listing(s) that may be you" in lines
    assert "https://south.example/listing/fake-marker" in lines
    assert "Please check these yourself (open the link, look for your name):" in lines
    assert "Manual Fake Search: This site blocks automatic checks." in lines
    assert "https://manual.example/search/fake-marker" in lines
    assert len(calls()) == 1
    call = calls()[0]
    assert call["registry"] is not None
    assert {key: value for key, value in call.items() if key != "registry"} == {
        "profile_id": PROFILE_ID,
        "offline": True,
        "refresh": False,
        "use_browser": False,
        "old_addresses": None,
    }


@pytest.mark.parametrize(
    ("names", "expected"),
    [
        (("West Example",), "Not found on 1 site(s): West Example"),
        (("West Example", "East Example"), "Not found on 2 site(s): West Example, East Example"),
    ],
)
def test_exposure_text_counts_not_found_sites(
    exposure_cli, monkeypatch: pytest.MonkeyPatch,
    names: tuple[str, ...], expected: str,
) -> None:
    from freemyid.engine import exposure as exposure_module

    runner, app, _calls = exposure_cli
    monkeypatch.setattr(exposure_module, "scan_exposure", lambda *_args, **_kwargs: _result(names))

    result = runner.invoke(app, ["exposure", "--offline", "--profile", PROFILE_ID])

    assert result.exit_code == 0, result.output
    lines = [line.strip() for line in result.stdout.splitlines()]
    assert expected in lines
