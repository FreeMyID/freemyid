"""tools/import_registries.py: synthetic fixtures only (fake companies, example.test domains)."""
from __future__ import annotations

import importlib.util
import io
import sys

import pytest
import yaml

from freemyid.models import Broker
from tests.conftest import ROOT

_spec = importlib.util.spec_from_file_location("import_registries",
                                               ROOT / "tools" / "import_registries.py")
assert _spec and _spec.loader
ir = importlib.util.module_from_spec(_spec)
sys.modules["import_registries"] = ir
_spec.loader.exec_module(ir)

CA_CSV = (
    "Broker ID,Data broker name:,\"Doing Business As (DBA), if applicable:\","
    "Data broker primary website:,Data broker primary contact email address:,"
    "Data broker's primary website that contains details on how consumers can exercise their rights\n"
    '1,Acme Fake Data Inc.,,www.acmefake-example.test,privacy@acmefake-example.test,'
    "https://www.acmefake-example.test/privacy/requests\n"
    '2,Bogus Lists LLC,BogusFinder,https://bogus-example.test,jane.smith@bogus-example.test,'
    "https://bogus-example.test/optout\n"
    '3,Offsite Corp,,offsite-example.test,privacy@elsewhere-example.test,\n'
    '4,Curated Twin Inc,,curatedtwin-example.test,privacy@curatedtwin-example.test,\n'
    '5,Nocontact Co,,nocontact-example.test,,http://nocontact-example.test/plain-http\n'
    '6,Multi Site Ltd,,multi1-example.test; multi2-example.test,dpo@multi2-example.test,\n'
)
VT_TSV = (
    "Business Name\tWebsite\tPrivacy Request URL\tEmail\tRegistration Date\n"
    "ACME FAKE DATA, INC\twww.acmefake-example.test\t\t\t03/01/2025\n"
    "Vermont Only LLC\tvtonly-example.test\thttps://vtonly-example.test/do-not-sell\t\t01/15/2026\n"
    "Webless Partners\t\t\t\t2025\n"
)
TX_CSV = ("Name,DBA,Web Site,Contact Email\n"
          "Texan Fake LLC,Lone Star Lookup;LSL,texan-example.test,legal@texan-example.test\n"
          "Bogusfinder,,bogus-example.test,\n")
OR_CSV = ("Entity Name,Trade Name,Internet Address,Privacy URL\n"
          "Oregon Fake Co,,orfake-example.test,https://orfake-example.test/privacy-choices\n")

CURATED_YAML = """version: test
brokers:
- id: curated_twin
  name: Curated Twin Inc
  url: https://curatedtwin-example.test/
  category: data_broker
  domains: [curatedtwin-example.test]
  method: web_form
  opt_out_url: https://curatedtwin-example.test/optout
  priority: 90
  legal_basis_notes: hand written
"""


@pytest.fixture
def setup(tmp_path):
    reg = tmp_path / "registry.yaml"
    reg.write_text(CURATED_YAML)
    files = {}
    for key, name, body in (("ca", "ca_x.csv", CA_CSV), ("vt", "vt_x.tsv", VT_TSV),
                            ("tx", "tx_x.csv", TX_CSV), ("or", "or_x.csv", OR_CSV)):
        p = tmp_path / name
        p.write_text(body)
        files[key] = p
    return reg, files


def _run(files, reg, write=False, only=None):
    inputs = {k: v for k, v in files.items() if only is None or k in only}
    return ir.run(inputs, reg, write, out=io.StringIO())


def test_parse_ca_columns():
    recs, rows = ir.parse_ca(CA_CSV)
    assert rows == 6 and len(recs) == 6
    a = recs[0]
    assert (a.name, a.website, a.email) == ("Acme Fake Data Inc.", "www.acmefake-example.test",
                                            "privacy@acmefake-example.test")
    assert a.privacy_url.endswith("/privacy/requests")
    assert recs[1].dbas == ["BogusFinder"]


def test_parse_vt_tsv_year_and_blank_website():
    recs, rows = ir.parse_vt(VT_TSV)
    assert rows == 3
    assert recs[1].name == "Vermont Only LLC" and recs[1].year == 2026
    assert recs[1].privacy_url.endswith("/do-not-sell")
    assert recs[2].website == "" and recs[2].year == 2025


def test_parse_tx_dbas_split():
    recs, _ = ir.parse_tx(TX_CSV)
    assert recs[0].dbas == ["Lone Star Lookup", "LSL"]
    assert recs[0].email == "legal@texan-example.test"


def test_parse_or_privacy_url():
    recs, _ = ir.parse_or(OR_CSV)
    assert recs[0].privacy_url == "https://orfake-example.test/privacy-choices"
    assert recs[0].website == "orfake-example.test"


def test_role_mailbox_rule(setup):
    reg, files = setup
    r = _run(files, reg, only={"ca"})
    names = {e["name"] for e in r["entries"]}
    assert "Acme Fake Data Inc" in names
    assert not any(e.get("opt_out_email", "").startswith("jane.smith") for e in r["entries"])
    # its https privacy page still qualifies, so it is not skipped, just not emailed
    assert next(e for e in r["entries"] if "bogus" in e["url"])["method"] == "web_form"


def test_email_must_be_on_own_domain(setup):
    reg, files = setup
    r = _run(files, reg, only={"ca"})
    assert r["stats"]["ca"].skipped.get("off_domain") == 1
    assert all(e.get("opt_out_email", "x@" + e["domains"][0]).split("@")[1] in e["domains"]
               for e in r["entries"])


def test_https_only_and_web_form_fallback(setup):
    reg, files = setup
    r = _run(files, reg, only={"ca", "vt"})
    by = {e["name"]: e for e in r["entries"]}
    vt_only = by["Vermont Only LLC"]
    assert vt_only["method"] == "web_form" and vt_only["verification_status"] == "unverified"
    assert "opt_out_email" not in vt_only and vt_only["vt_registered"] is True
    # http-only page, no email -> unusable
    assert "Nocontact Co" not in by
    # personal mailbox but an https privacy page -> web_form
    assert by["BogusFinder"]["method"] == "web_form"
    assert all(str(e.get("opt_out_url", "https://")).startswith("https://") for e in by.values())


def test_curated_wins_and_is_never_touched(setup):
    reg, files = setup
    before = reg.read_text()
    r = _run(files, reg, write=True)
    assert all(e["name"] != "Curated Twin Inc" for e in r["entries"])
    assert r["stats"]["ca"].dup_curated == 1
    text = reg.read_text()
    assert text.startswith(before.rstrip("\n"))
    data = yaml.safe_load(text)["brokers"]
    assert data[0]["legal_basis_notes"] == "hand written" and data[0]["priority"] == 90


def test_cross_source_dedupe_by_domain_and_name_merges_citations(setup):
    reg, files = setup
    r = _run(files, reg)
    acme = [e for e in r["entries"] if e["name"].startswith("Acme")]
    assert len(acme) == 1
    assert acme[0]["source_urls"][:2] == [ir.SOURCES["ca"][1], ir.SOURCES["vt"][1]]
    assert "California CPPA" in acme[0]["legal_basis_notes"]
    assert "Vermont SOS 2025" in acme[0]["legal_basis_notes"]
    assert acme[0]["ca_registered"] and acme[0]["vt_registered"]
    # Bogus (CA, by DBA) and Bogusfinder (TX, by name + domain) are one broker
    bog = [e for e in r["entries"] if "bogus" in e["url"]]
    assert len(bog) == 1 and "Texas SOS" in bog[0]["legal_basis_notes"]
    st = r["stats"]
    assert st["vt"].dup_cross == 1 and st["tx"].dup_cross == 1 and st["ca"].new >= 1


def test_multi_site_cell_allows_email_on_any_listed_site(setup):
    reg, files = setup
    r = _run(files, reg, only={"ca"})
    multi = next(e for e in r["entries"] if e["name"] == "Multi Site Ltd")
    assert multi["opt_out_email"] == "dpo@multi2-example.test"
    assert multi["url"] == "https://multi1-example.test/"


def test_entries_validate_against_broker_model(setup):
    reg, files = setup
    r = _run(files, reg)
    assert r["entries"]
    for e in r["entries"]:
        Broker.model_validate(e)
    ids = [e["id"] for e in r["entries"]]
    assert len(ids) == len(set(ids)) and "curated_twin" not in ids


def test_dry_run_writes_nothing_and_reports_counts(setup):
    reg, files = setup
    before = reg.read_text()
    out = io.StringIO()
    ir.run(files, reg, False, out=out)
    assert reg.read_text() == before
    text = out.getvalue()
    assert "dry run" in text and "projected total" in text and "dup_curated" in text


def test_write_is_deterministic_and_rerunnable(setup):
    reg, files = setup
    _run(files, reg, write=True)
    first = reg.read_text()
    assert ir.BEGIN in first and ir.END in first
    _run(files, reg, write=True)
    assert reg.read_text() == first
    assert first.count(ir.BEGIN) == 1
    # input order / file location must not matter
    again = _run({k: files[k] for k in reversed(list(files))}, reg)
    assert [e["id"] for e in again["entries"]] == [
        b["id"] for b in yaml.safe_load(first)["brokers"][1:]]


def test_rerun_after_adoption_into_curated_does_not_duplicate(setup):
    reg, files = setup
    _run(files, reg, write=True)
    data = yaml.safe_load(reg.read_text())
    # A person moves the generated block into the curated section (drops the markers).
    reg.write_text(reg.read_text().replace(ir.BEGIN, "").replace(ir.END, ""))
    r = _run(files, reg)
    assert r["entries"] == [] and r["curated"] == len(data["brokers"])


def test_privacy_page_on_a_known_portal_vendor_is_usable_but_unknown_hosts_are_not():
    portal = "https://privacyportal.onetrust.com/webform/fake-tenant/fake-form"
    rows = [
        CA_CSV.splitlines()[0],
        f"7,Portal Fake Inc,,portalfake-example.test,,{portal}",
        "8,Thirdparty Fake LLC,,thirdparty-example.test,,https://forms-example.test/privacy",
        "9,Portal Root Inc,,portalroot-example.test,,https://privacyportal.onetrust.com/",
        "10,Portal Mail Inc,,portalmail-example.test,privacy@onetrust.com,",
    ]
    text = "\n".join(rows) + "\n"
    recs = {r.name: r for r in ir.parse_ca(text)[0]}
    email, url, _ = ir.usable_contact(recs["Portal Fake Inc"])
    assert email is None and url and url.startswith("https://privacyportal.onetrust.com/")
    assert ir.usable_contact(recs["Thirdparty Fake LLC"])[:2] == (None, None)
    assert ir.usable_contact(recs["Portal Root Inc"])[:2] == (None, None)   # bare portal root
    assert ir.usable_contact(recs["Portal Mail Inc"])[:2] == (None, None)   # emails never off-domain
    entry = ir._entry([recs["Portal Fake Inc"]], recs["Portal Fake Inc"], None, url)
    assert "privacyportal.onetrust.com" in entry["domains"]
    assert entry["method"] == "web_form"
