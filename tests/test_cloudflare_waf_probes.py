"""The edge probe-block rule must catch scanner paths and never a real site path."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("waf", ROOT / "tools" / "cloudflare_waf_probes.py")
waf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(waf)  # type: ignore[union-attr]

PROBES = ["/.env", "/.git/config", "/.vscode/sftp.json", "/backup.sql", "/dump.sql.bak",
          "/terraform.tfstate", "/secrets.tfvars", "/wp-config.php.bak", "/wp-json/x",
          "/actuator/trace", "/config/database.yml", "/settings.py", "/config.ini",
          "/vendor/webmozart/assert/.composer-auth.json", "/application-secrets.properties"]
REAL = ["/", "/developers/config/", "/robots.txt", "/sitemap.xml", "/favicon.ico",
        "/assets/free-my-id-fridge-card.pdf", "/.well-known/security.txt",
        "/2b3da124d08af987b483dfb5ca217d9f.txt", "/_assets/Base.DYwvU12T.css"]


@pytest.mark.parametrize("path", PROBES)
def test_probe_paths_are_blocked(path: str) -> None:
    assert waf.is_probe(path)


@pytest.mark.parametrize("path", REAL)
def test_real_paths_are_not_blocked(path: str) -> None:
    assert not waf.is_probe(path)


def test_no_built_site_path_is_blocked() -> None:
    dist = ROOT / "web" / "dist"
    if not (dist / "index.html").is_file():
        pytest.skip("web/dist not built")
    paths = ["/" + p.relative_to(dist).as_posix() for p in dist.rglob("*") if p.is_file()]
    assert paths and not [p for p in paths if waf.is_probe(p)]


def test_expression_mirrors_the_python_lists() -> None:
    e = waf.expression()
    assert all(f'"{s}"' in e for s in (*waf.PREFIXES, *waf.SUFFIXES, waf.ALLOW_PREFIX))
    assert e.count("starts_with") == len(waf.PREFIXES) + 1
    assert e.count("ends_with") == len(waf.SUFFIXES)


# SEC-126: a failed ruleset read must never turn into "no rules" and PUT over the zone's rules
@pytest.mark.parametrize("argv", [["--apply"], ["--rollback", "unused.json"]])
def test_sec126_failed_read_never_writes(monkeypatch, argv) -> None:
    calls: list[str] = []

    def api(method, path, body=None):
        calls.append(method)
        if path.startswith("/zones?"):
            return {"success": True, "result": [{"id": "z1"}]}
        if method == "GET":
            return {"success": False, "errors": [{"message": "HTTP 500"}]}
        return {"success": True}

    monkeypatch.setattr(waf.cf, "api", api)
    assert waf.main(argv) == 1
    assert "PUT" not in calls
