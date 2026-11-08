"""SEC-114: until the BL-IN-08 engine handles every path, no import path may set
Profile.removal_scope. A setup file is rejected; a profile bundle drops the field. Fake
people only."""
from __future__ import annotations

import json

import pytest
import yaml

from tests.test_cli_setup_from import _base, _write


@pytest.mark.parametrize("where", ["top", "person", "permissions"])
def test_setup_file_cannot_set_removal_scope(tmp_path, where):
    from freemyid import setup_config
    data = _base()
    target = data if where == "top" else data.setdefault(where, {})
    target["removal_scope"] = "phone"
    if where == "permissions":
        target.pop("removal_scope")
        target["allow_email_disclosure"] = True
    with pytest.raises(setup_config.SetupFileError):
        setup_config.load(_write(tmp_path, data))


def test_setup_example_still_loads(tmp_path):
    from freemyid import setup_config
    assert setup_config.load(_write(tmp_path, _base())).person.name


def test_bundle_import_drops_removal_scope():
    from freemyid.crypto import export_with_passphrase
    from freemyid.wizard import flows
    blob = export_with_passphrase(json.dumps({
        "freemyid_bundle": flows.BUNDLE_VERSION,
        "profile": {"label": "Test", "removal_scope": "phone", "phones": ["217-555-0142"],
                    "permissions": {"allow_phone_disclosure": True,
                                    "allow_email_disclosure": True},
                    "name": {"first": "Test", "last": "Person"},
                    "addresses": [{"city": "Testville", "state": "NC",
                                   "current": True}]}}).encode(), "pw-test-1234")
    d = flows.load_bundle(blob, "pw-test-1234")
    assert not hasattr(d, "removal_scope") or d.removal_scope in (None, "full")
    assert not getattr(d, "allow_email_disclosure", False)
    assert "removal_scope" not in yaml.safe_dump(vars(d))
