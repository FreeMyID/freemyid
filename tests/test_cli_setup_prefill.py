"""CLI-A04: `setup --prefill` implies terminal prompts; `--web --prefill` is refused."""
from __future__ import annotations

from typer.testing import CliRunner

from freemyid.cli import app


def test_prefill_implies_terminal(freemyid_env, monkeypatch, tmp_path):
    seen = {}
    from freemyid.wizard import flows, server

    class P:
        label, id = "Pat", "abcdef123456"

    monkeypatch.setattr(flows, "setup_cli", lambda store, prefill=None: seen.update(p=prefill) or P())
    monkeypatch.setattr(server, "serve", lambda *a, **k: seen.update(web=True))
    f = tmp_path / "x.freemyid-profile"
    r = CliRunner().invoke(app, ["setup", "--prefill", str(f)])
    assert r.exit_code == 0, r.output
    assert seen == {"p": f}


def test_web_with_prefill_exits_2(freemyid_env, monkeypatch, tmp_path):
    from freemyid.wizard import server
    monkeypatch.setattr(server, "serve", lambda *a, **k: (_ for _ in ()).throw(AssertionError))
    r = CliRunner().invoke(app, ["setup", "--web", "--prefill", str(tmp_path / "x")])
    assert r.exit_code == 2
    assert "/wizard/import" in r.output


def test_plain_setup_still_opens_web(freemyid_env, monkeypatch):
    from freemyid.wizard import server
    seen = []
    monkeypatch.setattr(server, "serve", lambda *a, **k: seen.append(1))
    assert CliRunner().invoke(app, ["setup"]).exit_code == 0
    assert seen
