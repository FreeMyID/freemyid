"""tools/export_coverage.py: the public coverage list. Synthetic brokers only (*.example.test)."""
from __future__ import annotations

import importlib.util
import random
import re
import sys
from datetime import date

import pytest
import yaml

from tests.conftest import ROOT, make_profile

_spec = importlib.util.spec_from_file_location("export_coverage", ROOT / "tools" / "export_coverage.py")
assert _spec is not None and _spec.loader is not None
ec = importlib.util.module_from_spec(_spec)
sys.modules["export_coverage"] = ec
_spec.loader.exec_module(ec)

# Every private value in the fixtures carries this marker, so one search proves nothing leaked.
SECRET = "LEAK-MARKER"


@pytest.fixture(autouse=True)
def fake_sites_are_main_sites(monkeypatch):
    """Fixture brokers live at <name>.example.test: treat example.test like co.uk, so that is a main site."""
    monkeypatch.setattr(ec, "TWO_LABEL_SUFFIXES", ec.TWO_LABEL_SUFFIXES | {"example.test"})


def broker(bid: str, **over) -> dict:
    """A registry entry with every kind of private field filled in."""
    b = {
        "id": bid, "name": f"{bid.title()} Search", "url": f"https://www.{bid}.example.test/",
        "category": "people_search", "domains": [f"{bid}.example.test", f"optout.{bid}.example.test"],
        "method": "web_form",
        "opt_out_url": f"https://optout.{bid}.example.test/remove/{SECRET}",
        "opt_out_email": f"{SECRET}@privacy.{bid}.example.test",
        "search_url_pattern": f"https://{bid}.example.test/find/{{first}}-{{last}}/{SECRET}",
        "phone": f"555-0100 {SECRET}",
        "postal": {"name": f"{SECRET} Privacy Dept", "street": "1 Fake St", "city": "Springfield",
                   "state": "IL", "zip": "62704"},
        "required_fields": ["full_name", "email"],
        "steps": [f"Open the form and click {SECRET}."],
        "form": [{"action": "goto", "url": f"https://optout.{bid}.example.test/{SECRET}"},
                 {"action": "human", "selector": f"#captcha-{SECRET}"}],
        "success_text": [f"{SECRET} request received"],
        "safe_checkboxes": [f"input#agree-{SECRET}"],
        "legal_basis_notes": f"{SECRET} legal note",
        "verification_notes": f"{SECRET} verification note",
        "source_urls": [f"https://www.{bid}.example.test/privacy/{SECRET}"],
        "search_access_note": f"{SECRET} access note",
        "verification_status": "unverified", "priority": 50,
    }
    b.update(over)
    return b


def registry(*brokers: dict) -> dict:
    return {"version": "2026.11.06", "updated": date(2026, 11, 6), "brokers": list(brokers)}


def rows_by_site(reg: dict) -> dict[str, dict]:
    return {r["site"]: r for r in ec.build_rows(reg)}


def one(**over) -> dict:
    return ec.build_rows(registry(broker("alpha", **over)))[0]


# ---------------------------------------------------------------- the allowlist

def test_only_allowlisted_fields_are_exported():
    reg = registry(broker("alpha"), broker("beta", covered_by="alpha", parent_company="Fake Holdings LLC"),
                   broker("gamma", verification_status="verified", last_verified=date(2026, 11, 3)))
    text = ec.render(reg)
    data = yaml.safe_load(text)
    assert set(data) == {"format", "updated", "counts", "sites"}
    for row in data["sites"]:
        assert set(row) <= set(ec.FIELDS)
        assert set(ec.REQUIRED) <= set(row)
    assert SECRET not in text


def test_a_new_private_field_does_not_leak():
    reg = registry(broker("alpha", brand_new_private_field=f"{SECRET} added next year",
                          another={"nested": [f"{SECRET} deep"]}))
    reg["new_top_level_field"] = f"{SECRET} top"
    text = ec.render(reg)
    assert SECRET not in text
    assert "brand_new_private_field" not in text and "new_top_level_field" not in text


def test_no_contact_data_urls_ids_or_days_in_the_output():
    text = ec.render(registry(broker("alpha", verification_status="verified",
                                     last_verified=date(2026, 11, 3)),
                              broker("beta", last_verified="2026-10-28")))
    body = "\n".join(ln for ln in text.splitlines() if not ln.startswith("#"))
    assert "@" not in body and "http" not in body and "/" not in body
    assert "optout." not in body and "privacy." not in body          # only the main site's hostname
    assert not re.search(r"\d{4}-\d{2}-\d{2}", body)                 # the month, never the day
    assert '"2026-11"' in body and '"2026-10"' in body
    assert "id:" not in body and "priority" not in body


@pytest.mark.parametrize("bad", ["Sales Team privacy@fake.example.test",
                                 "See https://fake.example.test/optout", "www.fake.example.test"])
def test_a_name_that_looks_like_contact_data_is_refused(bad):
    with pytest.raises(ec.ExportError):
        ec.render(registry(broker("alpha", name=bad)))
    with pytest.raises(ec.ExportError):       # a family name is checked the same way
        ec.render(registry(broker("alpha", name=bad), broker("beta", covered_by="alpha")))
    assert bad not in ec.render(registry(broker("alpha", parent_company=bad)))   # never exported at all


def test_bad_registry_values_are_refused():
    for over in ({"category": "made_up"}, {"url": "not a url"}, {"covered_by": "nobody"},
                 {"last_verified": "soon"}, {"name": "  "}, {"name": "N" * 200}):
        with pytest.raises(ec.ExportError):
            ec.render(registry(broker("alpha", **over)))
    with pytest.raises(ec.ExportError):
        ec.render(registry(broker("alpha"), broker("alpha")))
    with pytest.raises(ec.ExportError):
        ec.render({"brokers": []})


# ---------------------------------------------------------------- names, sites, family

def test_display_name_and_site_host():
    row = one(name="Alpha  People,\n Inc. (parent of Beta; call 555-0100)",
              url="https://WWW.Alpha.Example.Test/people/search?x=1")
    assert row["name"] == "Alpha People"
    assert row["site"] == "alpha.example.test"
    assert ec.display_name("Gamma. Inc") == "Gamma" and ec.display_name("Delta Inc.") == "Delta"
    assert ec.display_name("Incline Data") == "Incline Data"
    assert ec.display_name("Z9, Inc") == "Z9, Inc"          # a real short name keeps its suffix
    assert ec.display_name("Z9 Data, Inc.") == "Z9 Data"


@pytest.mark.parametrize("bad", ["No", "X", "Z9", "formerly Fake Contact", "Formerly FakeCo (now Other)"])
def test_a_name_that_is_too_short_or_starts_with_formerly_is_refused(bad):
    with pytest.raises(ec.ExportError):
        ec.render(registry(broker("alpha", name=bad)))
    with pytest.raises(ec.ExportError):       # the same rule for a family name
        ec.render(registry(broker("alpha", name=bad), broker("beta", covered_by="alpha")))


def test_a_name_that_is_an_internal_id_is_refused():
    with pytest.raises(ec.ExportError):
        ec.render(registry(broker("alpha", name="optoutpage_fakebroker")))


@pytest.mark.parametrize("url", [
    "https://optout.fake.example.test/", "https://fakeoptout.example.test/", "https://opt-out.fake.example.test/x",
    "https://unsubscribe.fake.example.test/", "https://suppression.fake.example.test/",
    "https://donotsell.fake.example.test/", "https://privacy.fake.example.test/", "https://dsar.fake.example.test/",
])
def test_a_site_that_is_a_removal_address_is_refused(url):
    with pytest.raises(ec.ExportError):
        ec.render(registry(broker("alpha", url=url)))
    host = url.split("/")[2]
    # ...unless the public sample registry already names that hostname (an official tool, say)
    assert ec.build_rows(registry(broker("alpha", url=url)), frozenset({host}))[0]["site"] == host


def test_ordinary_hostnames_are_not_mistaken_for_removal_addresses():
    for host in ("privacyfirst.example.test", "www.outlook.example.test", "topdata.example.test",
                 "co-op.example.test"):
        assert one(url=f"https://{host}/")["site"] == host.removeprefix("www.")


@pytest.mark.parametrize("host", ["portal.fake.example.test", "consumers.fake.example.test",
                                  "apps.forms.fake.example.test"])
def test_a_site_on_a_subdomain_is_refused_until_confirmed(monkeypatch, host):
    with pytest.raises(ec.ExportError, match="subdomain"):
        ec.render(registry(broker("alpha", url=f"https://{host}/")))
    assert ec.build_rows(registry(broker("alpha", url=f"https://{host}/")), frozenset({host}))[0]["site"] == host
    monkeypatch.setattr(ec, "MAIN_SITE_SUBDOMAINS", frozenset({host}))
    assert one(url=f"https://{host}/")["site"] == host


def test_registrable_names_are_not_subdomains(monkeypatch):
    monkeypatch.setattr(ec, "TWO_LABEL_SUFFIXES", frozenset({"co.uk"}))
    assert ec.site_host("https://www.fakebroker.co.uk/", "x") == "fakebroker.co.uk"
    assert ec.site_host("https://fakebroker.test/", "x") == "fakebroker.test"
    with pytest.raises(ec.ExportError):
        ec.site_host("https://forms.fakebroker.co.uk/", "x")
    with pytest.raises(ec.ExportError):
        ec.site_host("https://fakebroker.example.test/", "x")       # example.test is not on the real list


def test_refusals_stop_the_export_and_name_every_entry():
    reg = registry(broker("alpha"), broker("beta", name="No"), broker("gamma", url="https://optout.gamma.example.test/"),
                   broker("delta", covered_by="beta"), broker("epsilon", category="made_up"))
    with pytest.raises(ec.ExportError) as err:
        ec.render(reg)
    message = str(err.value)
    assert message.startswith("4 entries refused")
    for bid in ("beta", "gamma", "delta", "epsilon"):
        assert f"\n  {bid}" in message
    assert SECRET not in message


def test_hold_back_leaves_refused_entries_out_and_reports_them():
    reg = registry(broker("alpha"), broker("beta", name="No"), broker("gamma", url="https://optout.gamma.example.test/"),
                   broker("delta", covered_by="beta"), broker("zeta", enabled=False))
    held: list[str] = []
    text = ec.render(reg, hold_back=True, held=held)
    data = yaml.safe_load(text)
    assert [r["site"] for r in data["sites"]] == ["alpha.example.test"]
    assert data["counts"] == {"listed": 1, "verified": 0, "not_verified": 1, "not_available": 1}
    assert sorted(m.split(":")[0].split(" ")[0] for m in held) == ["beta", "delta", "gamma"]
    for hidden in ("beta", "gamma", "delta", "optout"):
        assert hidden not in text
    with pytest.raises(ec.ExportError):               # nothing left to list
        ec.render(registry(broker("beta", name="No")), hold_back=True)


def test_sample_hosts_reads_the_public_sample(tmp_path):
    f = tmp_path / "registry.sample.yaml"
    f.write_text(yaml.safe_dump({"brokers": [{"id": "a", "url": "https://WWW.Privacy.Fake.Example.Test/tool"},
                                             {"id": "b"}]}), encoding="utf-8")
    assert ec.sample_hosts(f) == frozenset({"privacy.fake.example.test"})
    assert ec.sample_hosts(tmp_path / "missing.yaml") == frozenset()
    assert len(ec.sample_hosts()) > 20                      # the real public sample


def test_short_real_names_pass():
    for name in ("Z9, Inc", "IDX", "M+R", "Formal Data"):
        assert one(name=name)["name"] == name


def test_family_is_the_covered_by_parent_and_parent_company_is_never_exported():
    owner = f"{SECRET} Holdings LLC"
    reg = registry(
        broker("alpha", name="Alpha Suppression Center (Beta, Gamma)"),
        broker("beta", covered_by="alpha", parent_company=owner),
        broker("gamma", parent_company=owner, ca_registered=True),
        broker("delta", name="Alpha Suppression Center", covered_by="alpha"),
        broker("epsilon"),
    )
    rows = rows_by_site(reg)
    assert rows["beta.example.test"]["family"] == "Alpha Suppression Center"
    assert "family" not in rows["gamma.example.test"]      # an owner name is not a recorded filing fact
    assert "family" not in rows["delta.example.test"]      # its own name
    assert "family" not in rows["epsilon.example.test"]
    assert SECRET not in ec.render(reg) and "owner" not in ec.render(reg)


@pytest.mark.parametrize("over, registered", [
    ({}, None),
    ({"ca_registered": True}, "CA"),
    ({"vt_registered": True}, "VT"),
    ({"ca_registered": True, "vt_registered": True}, "CA,VT"),
    ({"ca_registered": False, "vt_registered": None}, None),
    ({"ca_registered": "yes"}, None),                       # only a real true counts
])
def test_registered_lists_the_state_registries(over, registered):
    assert one(**over).get("registered") == registered


# ---------------------------------------------------------------- route and status

FILL = [{"action": "goto", "url": "https://optout.alpha.example.test/"},
        {"action": "fill", "selector": "#name", "value": "{full_name}"}, {"action": "submit", "selector": "#go"}]


@pytest.mark.parametrize("over, route", [
    ({"method": "web_form", "opt_out_email": None}, "assisted"),
    ({"method": "web_form"}, "assisted"),                               # an address but no email method
    ({"method": "web_form", "alt_methods": ["email"]}, "email"),
    ({"method": "email"}, "email"),
    ({"method": "email", "opt_out_email": None}, "assisted"),
    ({"method": "phone", "alt_methods": ["email"]}, "email"),
    ({"method": "phone", "opt_out_email": None}, "by_hand"),
    ({"method": "postal", "opt_out_email": None}, "by_hand"),
    ({"method": "account_required", "opt_out_email": None}, "by_hand"),
    ({"form": FILL, "verification_status": "verified"}, "automatic"),
    ({"form": FILL}, "assisted"),                                       # form not verified
    ({"form": FILL, "verification_status": "verified", "has_captcha": True}, "assisted"),
    ({"form": [*FILL, {"action": "human"}], "verification_status": "verified"}, "assisted"),
    ({"form": FILL, "verification_status": "verified", "needs_id_upload": True}, "assisted"),
    ({"form": FILL, "verification_status": "verified", "required_fields": ["phone"]}, "assisted"),
    ({"form": FILL, "verification_status": "verified", "method": "email"}, "automatic"),
    ({"form": FILL, "method": "email"}, "email"),
])
def test_route(over, route):
    assert one(**over)["route"] == route


def test_a_covered_site_gets_its_parents_route():
    reg = registry(broker("alpha", method="email"), broker("beta", covered_by="alpha", opt_out_email=None))
    assert rows_by_site(reg)["beta.example.test"]["route"] == "email"


@pytest.mark.parametrize("over, status, checked", [
    ({"verification_status": "verified", "last_verified": date(2026, 11, 3)}, "verified", "2026-11"),
    ({"verification_status": "verified"}, "not_verified", None),        # no check date: not verified
    ({"verification_status": "unverified"}, "not_verified", None),
    ({"verification_status": "unverified", "last_verified": date(2026, 10, 2)}, "not_verified", "2026-10"),
])
def test_status_and_checked_month(over, status, checked):
    row = one(**over)
    assert row["status"] == status
    assert row.get("checked") == checked


def test_sites_that_are_not_available_are_counted_and_never_named():
    reg = registry(
        broker("alpha"),
        broker("brokenone", name="Broken One People", verification_status="broken", last_verified=date(2026, 11, 3)),
        broker("offone", name="Switched Off Data", enabled=False, verification_status="verified",
               last_verified=date(2026, 11, 3)),
        broker("childone", name="Child Of Off", covered_by="offone", verification_status="verified",
               last_verified=date(2026, 11, 3)),
        broker("no", name="No", enabled=False),            # a bad name on an unlisted site does not block the export
    )
    rows, not_available, refused = ec.build(reg)
    assert [r["site"] for r in rows] == ["alpha.example.test"] and not_available == 4 and refused == []
    text = ec.render(reg)
    data = yaml.safe_load(text)
    assert data["counts"] == {"listed": 1, "verified": 0, "not_verified": 1, "not_available": 4}
    assert all(r["status"] in ("verified", "not_verified") for r in data["sites"])
    for hidden in ("Broken One", "Switched Off", "Child Of Off", "brokenone", "offone", "childone",
                   '"not_available"', "broken"):
        assert hidden not in text, hidden


def test_updated_is_the_newest_month_in_the_export():
    newer = registry(broker("alpha", verification_status="verified", last_verified=date(2026, 12, 2)))
    assert yaml.safe_load(ec.render(newer))["updated"] == "2026-12"     # newer than the registry's own date
    assert yaml.safe_load(ec.render(registry(broker("alpha"))))["updated"] == "2026-11"
    no_date = registry(broker("alpha"))
    del no_date["updated"]
    with pytest.raises(ec.ExportError):
        ec.render(no_date)


def test_routes_agree_with_the_engine_on_the_public_sample():
    """route_of is a copy of tiers.tier_for for the default permissions. Keep the two in step."""
    from freemyid.engine.tiers import tier_for
    from freemyid.models import MailboxConfig, Tier
    from freemyid.registry import load_registry

    sample = ROOT / "brokers" / "registry.sample.yaml"
    reg = load_registry(sample)
    raw = {b["id"]: b for b in yaml.safe_load(sample.read_text(encoding="utf-8"))["brokers"]}
    profile = make_profile(mailbox=MailboxConfig(
        address="removals@example.test", imap_host="imap.example.test",
        smtp_host="smtp.example.test", username="removals@example.test"))
    same_tier = {"automatic": Tier.AUTOMATIC, "email": Tier.EMAIL, "assisted": Tier.ASSISTED,
                 "by_hand": Tier.ASSISTED}
    assert len(reg.brokers) > 20
    for b in reg.brokers:
        target = raw[b.covered_by] if b.covered_by else raw[b.id]
        assert same_tier[ec.route_of(target)] == tier_for(b, profile, registry=reg), b.id


# ---------------------------------------------------------------- counts, order, determinism

def many() -> dict:
    out = []
    for i in range(40):
        over: dict = {"name": f"{'zyxwvutsrq'[i % 10]}{i:02d} Fake Data", "category": ec.CATEGORIES[i % 7]}
        if i % 3 == 0:
            over.update(verification_status="verified", last_verified=date(2026, 11, 1 + i % 20))
        if i % 11 == 0:
            over.update(verification_status="broken")
        if i % 13 == 5:
            over.update(enabled=False)
        if i % 4 == 1:
            over.update(method="email")
        out.append(broker(f"site{i:02d}", **over))
    return registry(*out)


def test_counts_match_the_rows_and_the_registry():
    reg = many()
    data = yaml.safe_load(ec.render(reg))
    sites, counts = data["sites"], data["counts"]
    assert list(counts) == list(ec.COUNT_KEYS)
    assert counts["listed"] == len(sites) == counts["verified"] + counts["not_verified"]
    for status in ec.STATUSES:
        assert counts[status] == sum(1 for r in sites if r["status"] == status) > 0
    gone = [b for b in reg["brokers"] if b.get("enabled") is False or b["verification_status"] == "broken"]
    assert counts["not_available"] == len(gone) > 0
    assert counts["listed"] + counts["not_available"] == len(reg["brokers"])   # every entry is counted once
    assert data["updated"] == "2026-11" and data["format"] == ec.FORMAT


def test_output_is_sorted_and_deterministic():
    reg = many()
    first = ec.render(reg)
    assert first == ec.render(reg)
    shuffled = many()
    random.Random(7).shuffle(shuffled["brokers"])
    shuffled["brokers"] = [dict(reversed(list(b.items()))) for b in shuffled["brokers"]]
    assert ec.render(shuffled) == first
    names = [r["name"] for r in yaml.safe_load(first)["sites"]]
    assert names == sorted(names, key=str.casefold)
    assert first.endswith("\n") and "\r" not in first and "\t" not in first


def test_same_name_sorts_by_site():
    reg = registry(broker("bbb", name="Twin Data"), broker("aaa", name="Twin Data"))
    assert [r["site"] for r in ec.build_rows(reg)] == ["aaa.example.test", "bbb.example.test"]


# ---------------------------------------------------------------- command line

def test_cli_writes_checks_and_refuses(tmp_path, capsys):
    src, out = tmp_path / "registry.yaml", tmp_path / "coverage.public.yaml"
    src.write_text(yaml.safe_dump(many()), encoding="utf-8")
    assert ec.main([str(src), "-o", str(out)]) == 0
    assert out.read_text(encoding="utf-8") == ec.render(many())
    assert ec.main([str(src), "-o", str(out), "--check"]) == 0
    out.write_text(out.read_text(encoding="utf-8").replace("not_verified", "verified", 1), encoding="utf-8")
    assert ec.main([str(src), "-o", str(out), "--check"]) == 1
    assert ec.main([str(tmp_path / "missing.yaml"), "-o", str(out)]) == 2
    src.write_text(yaml.safe_dump(registry(broker("alpha"), broker("beta", name="a@b.example.test"))),
                   encoding="utf-8")
    before = out.read_text(encoding="utf-8")
    assert ec.main([str(src), "-o", str(out)]) == 2
    assert out.read_text(encoding="utf-8") == before                 # a refused export writes nothing
    err = capsys.readouterr().err
    assert "1 entry refused" in err and "beta" in err and SECRET not in err
    # --hold-back: the refused entry is left out and printed, the rest is written
    assert ec.main([str(src), "-o", str(out), "--hold-back"]) == 0
    assert [r["site"] for r in yaml.safe_load(out.read_text(encoding="utf-8"))["sites"]] == ["alpha.example.test"]
    err = capsys.readouterr().err
    assert "held back 1" in err and "beta" in err and SECRET not in err
    assert ec.main([str(src), "-o", str(out), "--hold-back", "--check"]) == 0
    assert ec.main([str(src), "-o", str(out), "--check"]) == 2       # the strict default still refuses


# ---------------------------------------------------------------- the committed file

def test_committed_coverage_file_is_well_formed():
    path = ROOT / "brokers" / "coverage.public.yaml"
    text = path.read_text(encoding="utf-8")
    data = yaml.safe_load(text)
    assert set(data) == {"format", "updated", "counts", "sites"} and data["format"] == ec.FORMAT
    sites = data["sites"]
    for row in sites:
        assert set(ec.REQUIRED) <= set(row) <= set(ec.FIELDS), row
        assert all(isinstance(v, str) and v for v in row.values()), row
        assert row["category"] in ec.CATEGORIES and row["route"] in ec.ROUTES
        assert row["status"] in ec.STATUSES
        assert re.fullmatch(r"[a-z0-9-]+(\.[a-z0-9-]+)+", row["site"]), row
        assert re.fullmatch(r"\d{4}-\d{2}", row.get("checked", "2026-11")), row
        assert row.get("registered", "CA") in ("CA", "VT", "CA,VT"), row
        for key in ("name", "family"):
            assert not re.search(r"@|://|www\.", row.get(key, "")), row
            assert len(row.get(key, "")) <= ec.MAX_NAME, row
            assert key not in row or len(row[key]) >= ec.MIN_NAME, row
            assert not row.get(key, "").casefold().startswith("formerly"), row
    assert data["counts"] == ec.count_rows(sites, data["counts"]["not_available"])
    assert data["updated"] >= max(r.get("checked", "") for r in sites)
    assert sites == sorted(sites, key=lambda r: (r["name"].casefold(), r["site"], r["name"]))
    body = "\n".join(ln for ln in text.splitlines() if not ln.startswith("#"))
    assert "@" not in body and "http" not in body and "/" not in body
    # The file is exactly what the exporter writes for these rows (no hand edits, no extra keys).
    lines = ["  - " + ec._flow([(k, r[k]) for k in ec.FIELDS if k in r]) for r in sites]
    assert text.split("sites:\n", 1)[1] == "\n".join(lines) + "\n"
