"""Human-readable registry output keeps brokers in priority order."""
from __future__ import annotations

from datetime import date

from typer.testing import CliRunner

from freemyid import cli
from freemyid.models import Registry


def test_registry_show_table_orders_rows_by_descending_priority(
    monkeypatch,
) -> None:
    """Shuffled synthetic input is displayed from highest to lowest priority."""
    registry = Registry.model_validate(
        {
            "version": "test",
            "updated": date(2026, 1, 1),
            "brokers": [
                {
                    "id": "fake_low",
                    "name": "Fake Low Priority",
                    "url": "https://fake-low.example",
                    "opt_out_url": "https://fake-low.example/opt-out",
                    "category": "people_search",
                    "domains": ["fake-low.example"],
                    "method": "web_form",
                    "priority": 10,
                },
                {
                    "id": "fake_high",
                    "name": "Fake High Priority",
                    "url": "https://fake-high.example",
                    "opt_out_url": "https://fake-high.example/opt-out",
                    "category": "people_search",
                    "domains": ["fake-high.example"],
                    "method": "web_form",
                    "priority": 90,
                },
                {
                    "id": "fake_middle",
                    "name": "Fake Middle Priority",
                    "url": "https://fake-middle.example",
                    "opt_out_url": "https://fake-middle.example/opt-out",
                    "category": "people_search",
                    "domains": ["fake-middle.example"],
                    "method": "web_form",
                    "priority": 50,
                },
            ],
        }
    )
    monkeypatch.setattr(cli, "_registry", lambda: registry)

    result = CliRunner().invoke(cli.app, ["registry", "show"])

    assert result.exit_code == 0, result.output
    positions = [result.output.index(broker_id) for broker_id in (
        "fake_high",
        "fake_middle",
        "fake_low",
    )]
    assert all(result.output.count(broker_id) == 1 for broker_id in (
        "fake_high",
        "fake_middle",
        "fake_low",
    ))
    assert positions == sorted(positions)
