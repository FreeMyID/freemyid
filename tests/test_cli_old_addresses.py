"""`freemyid exposure --old-addresses`: off by default (the config flag still decides), on
when given. Fake people only, offline (nothing is fetched)."""
from __future__ import annotations

from typer.testing import CliRunner

from tests.conftest import make_profile


def _invoke(store, monkeypatch, *extra):
    from freemyid import cli
    from freemyid.engine import exposure as ex
    from freemyid.engine._dev import fixture_registry
    p = make_profile()
    store.save_profile(p)
    monkeypatch.setattr(cli, "_registry", fixture_registry)
    seen = []
    real = ex.scan_exposure

    def spy(*a, **k):
        seen.append(k.get("old_addresses"))
        return real(*a, **k)

    monkeypatch.setattr(ex, "scan_exposure", spy)
    res = CliRunner().invoke(cli.app, ["exposure", "--offline", "--profile", p.id, *extra])
    assert res.exit_code == 0, res.output
    return seen


def test_old_addresses_off_by_default_leaves_it_to_config(store, monkeypatch):
    assert _invoke(store, monkeypatch) == [None]


def test_old_addresses_flag_turns_it_on(store, monkeypatch):
    assert _invoke(store, monkeypatch, "--old-addresses") == [True]


def test_old_addresses_is_in_the_help():
    from freemyid import cli
    res = CliRunner().invoke(cli.app, ["exposure", "--help"])
    assert "--old-addresses" in res.stdout and "off by default" in " ".join(res.stdout.split())
