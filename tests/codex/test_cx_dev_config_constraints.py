"""Keep documented developer config constraints aligned with the public schema."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PAGE = ROOT / "web/src/pages/developers/config/index.astro"
SCHEMA = ROOT / "schema/setup-config.schema.json"


def test_documented_config_constraints_match_schema() -> None:
    page = PAGE.read_text(encoding="utf-8")
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    definitions = schema["$defs"]

    # Each entry names the schema source and the exact page wording that carries
    # the corresponding claim. Keep this mapping explicit and intentionally small.
    claims = {
        "address_count": (
            definitions["SetupPerson"]["properties"]["addresses"],
            "one to four addresses",
            lambda node: "one to four addresses" if (node["minItems"], node["maxItems"]) == (1, 4) else "",
        ),
        "consent_basis": (
            definitions["SetupConsent"]["properties"]["basis"],
            "self</code>, <code>guardian_of_minor</code>, or <code>authorized_agent",
            lambda node: (
                "</code>, <code>".join(node["enum"][:-1])
                + "</code>, or <code>"
                + node["enum"][-1]
            ),
        ),
        "mailbox_providers": (
            definitions["SetupMailbox"]["properties"]["provider"],
            "gmail</code>, <code>yahoo</code>, <code>icloud</code>, <code>proton_bridge</code>, or <code>other",
            lambda node: (
                "</code>, <code>".join(node["enum"][:-1])
                + "</code>, or <code>"
                + node["enum"][-1]
            ),
        ),
        "email_mode": (
            schema["properties"]["email_mode"],
            "Choose <code>approve_each</code> or <code>auto</code>. The default is <code>approve_each</code>.",
            lambda node: (
                f"Choose <code>{node['enum'][0]}</code> or <code>{node['enum'][1]}</code>. "
                f"The default is <code>{node['default']}</code>."
            ),
        ),
        "schedule_weekday": (
            definitions["SetupSchedule"]["properties"]["weekday"],
            "weekday</code> (0 Monday through 6 Sunday)",
            lambda node: f"weekday</code> ({node['minimum']} Monday through {node['maximum']} Sunday)",
        ),
        "schedule_hour": (
            definitions["SetupSchedule"]["properties"]["hour"],
            "hour</code> (0–23)",
            lambda node: f"hour</code> ({node['minimum']}–{node['maximum']})",
        ),
    }
    for name, (source, expected_page_text, render_claim) in claims.items():
        assert source is not None, name
        assert expected_page_text in page, name
        assert render_claim(source) in page, name

    addresses = definitions["SetupPerson"]["properties"]["addresses"]
    assert addresses["minItems"] == 1
    assert addresses["maxItems"] == 4

    assert "A mailbox is optional." in page
    assert schema["properties"]["mailbox"]["default"] is None

    permission_schema = definitions["SetupPermissions"]["properties"]
    permission_defaults = schema["properties"]["permissions"]["default"]
    permission_page = (
        "Optional choices: <code>allow_id_upload</code>, <code>allow_account_creation</code>, "
        "and <code>allow_phone_disclosure</code>. Each defaults to <code>false</code>."
    )
    assert permission_page in page
    assert set(permission_defaults) == set(permission_schema)
    assert all(value is False for value in permission_defaults.values())
    assert all(node["default"] is False for node in permission_schema.values())

    schedule = schema["properties"]["schedule"]["default"]
    schedule_schema = definitions["SetupSchedule"]["properties"]
    schedule_page = (
        "Defaults are weekly recheck on Sunday at 10, without installing a job."
    )
    assert schedule_page in page
    assert schedule["weekly_recheck"] is schedule_schema["weekly_recheck"]["default"] is True
    assert schedule["weekday"] == schedule_schema["weekday"]["default"] == 6
    assert schedule["hour"] == schedule_schema["hour"]["default"] == 10
    assert schedule["install_job"] is schedule_schema["install_job"]["default"] is False
