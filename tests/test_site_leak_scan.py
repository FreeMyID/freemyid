"""tools/site_check.py leak scan with the public coverage list. Synthetic sites only (*.example.test).

Hostnames in brokers/coverage.public.yaml may appear on the website, as bare hostnames. Every other
private-registry hostname, every private opt-out URL and email address, and a coverage hostname
with a path or as an email domain must still be reported.
"""
from __future__ import annotations

import hashlib
import importlib.util
import sys

import pytest

from tests.conftest import ROOT

_spec = importlib.util.spec_from_file_location("site_check_leaks", ROOT / "tools" / "site_check.py")
assert _spec is not None and _spec.loader is not None
sc = importlib.util.module_from_spec(_spec)
sys.modules["site_check_leaks"] = sc
_spec.loader.exec_module(sc)

LISTED = "listed-site.example.test"          # in the coverage list: public
HIDDEN = "hidden-site.example.test"          # private registry only
LISTED_OPTOUT = "optout.listed-site.example.test"   # a listed site's private opt-out host


def sha(host: str) -> str:
    return hashlib.sha256(host.encode()).hexdigest()


HASHES = {sha(LISTED), sha(HIDDEN), sha(LISTED_OPTOUT)}
PUBLIC = {LISTED}


def kinds(text: str, public=frozenset(PUBLIC)) -> list[str]:
    return [kind for kind, _ in sc.host_leaks(text, HASHES, public)]


# ---------------------------------------------------------------- allowed

@pytest.mark.parametrize("text", [
    f"<li><b>Listed Site</b> <span>{LISTED}</span> Email</li>",
    f"We cover {LISTED}.",
    f"We cover www.{LISTED}, and more.",
    f"({LISTED})",
    f'<a href="https://{LISTED}/">Listed Site</a>',
    f"{LISTED.upper()}",
    "nothing-private.example.test and plain words",
])
def test_a_coverage_host_may_be_named(text):
    assert kinds(text) == []


# ---------------------------------------------------------------- still flagged

def test_a_private_host_outside_the_coverage_list_is_flagged():
    assert kinds(f"<li>{HIDDEN}</li>") == ["private"]
    assert kinds(f"www.{HIDDEN}") == ["private"]


def test_without_a_coverage_list_every_private_host_is_flagged():
    assert kinds(f"<li>{LISTED}</li>", public=frozenset()) == ["private"]
    assert sc.hashed_host_leaks(f"<li>{LISTED}</li>", HASHES) == [sha(LISTED)[:12]]


def test_a_listed_sites_other_hosts_stay_private():
    assert kinds(f"Write to {LISTED_OPTOUT} to opt out") == ["private"]


@pytest.mark.parametrize("text", [
    f"https://{LISTED}/optout",
    f"https://www.{LISTED}/privacy/remove-me?x=1",
    f'<a href="//{LISTED}/opt-out/">remove</a>',
    f"{LISTED}/optout",
    f"https://{LISTED}?optout=1",
    f"privacy@{LISTED}",
    f'<a href="mailto:privacy@{LISTED}">email</a>',
])
def test_a_coverage_host_with_a_path_or_as_an_email_domain_is_flagged(text):
    assert kinds(text) == ["path"]


def test_reports_never_contain_the_hostname():
    for _, digest in sc.host_leaks(f"{HIDDEN} privacy@{LISTED}", HASHES, PUBLIC):
        assert len(digest) == 12 and digest not in (HIDDEN, LISTED)
    assert sc.hashed_host_leaks(f"{HIDDEN} privacy@{LISTED}", HASHES, PUBLIC) == sorted(
        {sha(HIDDEN)[:12], sha(LISTED)[:12]})


def test_the_ok_list_still_wins():
    host = next(iter(sc.PUBLIC_OK_HOSTS))
    assert sc.host_leaks(f"https://{host}/opt-out", {sha(host)}) == []


# ---------------------------------------------------------------- the coverage file reader

def test_coverage_hosts_reads_only_site_values(tmp_path):
    f = tmp_path / "coverage.public.yaml"
    f.write_text(
        '# comment naming not-a-row.example.test\n'
        'sites:\n'
        f'  - {{name: "Listed Site", site: "{LISTED}", category: "people_search", route: "email", '
        'status: "verified", family: "Family Name.example.test"}\n'
        '  - {name: "Upper", site: "WWW.Upper-Site.Example.Test", category: "other", route: "assisted", '
        'status: "not_verified"}\n', encoding="utf-8")
    assert sc.coverage_hosts(f) == {LISTED, "upper-site.example.test"}
    assert sc.coverage_hosts(tmp_path / "missing.yaml") == set()


def test_committed_coverage_hosts_are_readable():
    hosts = sc.coverage_hosts()
    rows = (ROOT / "brokers" / "coverage.public.yaml").read_text(encoding="utf-8").count("\n  - {")
    assert len(hosts) == rows > 100                # one hostname per row, none lost by the stdlib reader


# ---------------------------------------------------------------- end to end on a small built site

PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Sites</title></head>
<body><h1>Sites we cover</h1><ul>{rows}</ul></body></html>"""


def leak_errors(monkeypatch, tmp_path, rows: str) -> list[str]:
    root = tmp_path / "repo"
    (root / "brokers").mkdir(parents=True, exist_ok=True)
    (root / "brokers" / "coverage.public.yaml").write_text(
        f'sites:\n  - {{name: "Listed Site", site: "{LISTED}", category: "people_search", '
        'route: "email", status: "verified"}\n', encoding="utf-8")
    # What the private files would hold: the full registry (opt-out URL and email) and the hash list.
    (root / "brokers" / "registry.sample.yaml").write_text("brokers: []\n", encoding="utf-8")
    (root / "brokers" / "registry.yaml").write_text(
        "brokers:\n"
        f"  - id: listed\n    url: https://{LISTED}/\n"
        f"    opt_out_url: https://{LISTED_OPTOUT}/remove-me\n"
        f"    opt_out_email: privacy@{LISTED}\n"
        f"  - id: hidden\n    url: https://{HIDDEN}/\n"
        f"    opt_out_url: https://{HIDDEN}/optout\n", encoding="utf-8")
    hashes = tmp_path / "hashes.txt"
    hashes.write_text("# hashes\n" + "\n".join(sorted(HASHES)) + "\n", encoding="utf-8")
    monkeypatch.setattr(sc, "ROOT", root)
    monkeypatch.setattr(sc, "COVERAGE", root / "brokers" / "coverage.public.yaml")
    monkeypatch.setattr(sc, "HOST_HASHES", hashes)
    monkeypatch.delenv("FMID_FULL_REGISTRY", raising=False)
    monkeypatch.delenv("FMID_HOST_HASHES", raising=False)
    site = tmp_path / "dist"
    (site / "brokers").mkdir(parents=True, exist_ok=True)
    (site / "brokers" / "index.html").write_text(PAGE.format(rows=rows), encoding="utf-8")
    errors = sc.check_site(site, "https://freemyid.example.test/", "/")
    return [e for e in errors if "private-only" in e or "full-registry-only" in e or "coverage-list" in e]


def test_check_site_allows_the_coverage_page(monkeypatch, tmp_path):
    assert leak_errors(monkeypatch, tmp_path, f"<li><b>Listed Site</b> {LISTED} Email</li>") == []


def test_check_site_flags_a_private_host(monkeypatch, tmp_path):
    errors = leak_errors(monkeypatch, tmp_path, f"<li>{LISTED}</li><li>{HIDDEN}</li>")
    assert len(errors) == 1 and "private-only broker hostname" in errors[0]
    assert HIDDEN not in errors[0] and sha(HIDDEN)[:12] in errors[0]


def test_check_site_flags_opt_out_urls_and_emails(monkeypatch, tmp_path):
    errors = leak_errors(monkeypatch, tmp_path,
                         f'<li><a href="https://{LISTED_OPTOUT}/remove-me">Listed Site</a></li>')
    assert any("full-registry-only value" in e for e in errors)          # the opt-out URL itself
    assert any("private-only broker hostname" in e for e in errors)      # and its host
    errors = leak_errors(monkeypatch, tmp_path, f"<li>privacy@{LISTED}</li>")
    assert any("full-registry-only value" in e for e in errors)
    assert any("coverage-list site" in e for e in errors)
    errors = leak_errors(monkeypatch, tmp_path, f"<li>{LISTED}/some/other/path</li>")
    assert len(errors) == 1 and "coverage-list site" in errors[0]


def test_private_inputs_can_come_from_another_checkout(monkeypatch, tmp_path):
    hashes = tmp_path / "elsewhere-hashes.txt"
    hashes.write_text(sha(HIDDEN) + "\n", encoding="utf-8")
    full = tmp_path / "elsewhere-registry.yaml"
    full.write_text(f"brokers:\n  - id: hidden\n    opt_out_url: https://{HIDDEN}/optout\n", encoding="utf-8")
    monkeypatch.setattr(sc, "HOST_HASHES", tmp_path / "not-here.txt")
    monkeypatch.setattr(sc, "ROOT", tmp_path / "no-private-files-here")
    assert sc.private_host_hashes() == set() and sc.full_registry_needles() == []
    (tmp_path / "no-private-files-here" / "brokers").mkdir(parents=True)
    (tmp_path / "no-private-files-here" / "brokers" / "registry.sample.yaml").write_text("brokers: []\n")
    monkeypatch.setenv("FMID_HOST_HASHES", str(hashes))
    monkeypatch.setenv("FMID_FULL_REGISTRY", str(full))
    assert sc.private_host_hashes() == {sha(HIDDEN)}
    assert sc.full_registry_needles() == [f"https://{HIDDEN}/optout"]


def test_site_data_loader_still_refuses_the_private_registry():
    """The website build reads the public sample and the coverage list, never the full registry."""
    site_ts = (ROOT / "web" / "src" / "lib" / "site.ts").read_text(encoding="utf-8")
    assert 'realpathSync(resolve(REPO, "brokers/registry.yaml"))' in site_ts
    assert "resolves to brokers/registry.yaml (private)" in site_ts
    assert 'endsWith(".sample.yaml")' in site_ts


# ---------------------------------------------------------------- copy rules and the coverage rows

def copy_errors(tmp_path, rel: str, body: str) -> list[str]:
    site = tmp_path / "dist"
    page = site / rel
    page.parent.mkdir(parents=True, exist_ok=True)
    page.write_text(PAGE.format(rows="") + body, encoding="utf-8")
    return [e for e in sc.content_rules(site) if "banned phrase" in e]


def test_a_company_name_in_the_coverage_rows_is_not_a_banned_claim(tmp_path):
    rows = ('<ul class="cov-list" role="list"><li><b>Five Star Rated</b> <span>five-star.example.test</span>'
            "<small>Not yet verified · By email</small></li></ul>")
    assert copy_errors(tmp_path, "brokers/index.html", rows) == []


def test_copy_around_the_coverage_rows_is_still_checked(tmp_path):
    rows = '<ul class="cov-list" role="list"><li><b>Fake Data</b> <span>fake.example.test</span></li></ul>'
    errors = copy_errors(tmp_path, "brokers/index.html", "<p>We guarantee every removal.</p>" + rows)
    assert len(errors) == 1 and "guarantee" in errors[0]
    errors = copy_errors(tmp_path, "brokers/index.html", rows + "<p>Rated five stars.</p>")
    assert len(errors) == 1 and "star rating" in errors[0]


def test_the_exception_is_only_for_the_coverage_page(tmp_path):
    rows = '<ul class="cov-list" role="list"><li><b>Five Star Rated</b></li></ul>'
    assert len(copy_errors(tmp_path, "guides/index.html", rows)) == 1
