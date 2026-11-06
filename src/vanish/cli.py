"""`vanish` command line. OWNER: orchestrator. Thin layer: all logic lives in modules."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from . import config as cfgmod
from . import logging_setup
from .models import ConsentBasis, Profile, RequestStatus

app = typer.Typer(help="Vanish: remove your info from data brokers, and keep it removed.",
                  no_args_is_help=True)
profile_app = typer.Typer(help="Manage people (profiles).", no_args_is_help=True)
schedule_app = typer.Typer(help="Install/remove the background re-check job.",
                           no_args_is_help=True)
registry_app = typer.Typer(help="Broker registry.", no_args_is_help=True)
todo_app = typer.Typer(help="Things that need a human.", no_args_is_help=True)
outbox_app = typer.Typer(help="Emails waiting for your approval.", no_args_is_help=True)
config_app = typer.Typer(help="Settings.", no_args_is_help=True)
for name, sub in (("profile", profile_app), ("schedule", schedule_app),
                  ("registry", registry_app), ("todo", todo_app), ("outbox", outbox_app),
                  ("config", config_app)):
    app.add_typer(sub, name=name)

con = Console()


def _store():
    from .storage import Store
    return Store()


def _registry():
    from .registry import load_registry
    return load_registry()


def consent_ok(p: Profile) -> tuple[bool, str]:
    """Hard consent gate (shared by CLI and runner)."""
    c = p.consent
    if not c.attested_by.strip():
        return False, "consent has no attesting name"
    if p.is_minor and c.basis not in (ConsentBasis.GUARDIAN_OF_MINOR,):
        return False, "minor profile requires parent/guardian consent"
    if c.basis == ConsentBasis.AUTHORIZED_AGENT and not c.authorization_doc:
        return False, "authorized agent needs the signed authorization attached"
    return True, ""


def _select(store, profile: Optional[str]) -> list[Profile]:
    ps = store.list_profiles()
    if profile:
        ps = [p for p in ps if p.id.startswith(profile) or p.label.lower() == profile.lower()]
        if not ps:
            raise typer.BadParameter(f"no profile matches {profile!r}")
    ok = []
    for p in ps:
        good, why = consent_ok(p)
        if good:
            ok.append(p)
        else:
            con.print(f"[yellow]Skipping {p.label}: {why}[/]")
    return ok


@app.callback()
def _main(verbose: bool = typer.Option(False, "--verbose", "-v")) -> None:
    logging_setup.setup(verbose)


# --------------------------------------------------------------------------- top level


@app.command()
def setup(prefill: Optional[Path] = typer.Option(None, help="Family bundle (.vanish-profile)"),
          web: bool = typer.Option(True, help="Open the web wizard (else terminal prompts)")):
    """Walk through setup for a person (opens the local web wizard by default)."""
    if web:
        from .wizard.server import serve
        serve(cfgmod.load().wizard_port, open_browser=True)
    else:
        from .wizard.flows import setup_cli
        p = setup_cli(_store(), prefill=prefill)
        con.print(f"[green]Saved profile {p.label} ({p.id[:8]})[/]")


@app.command()
def dashboard():
    """Open the local dashboard (status, evidence, to-dos, approvals)."""
    from .wizard.server import serve
    serve(cfgmod.load().wizard_port, open_browser=True)


def _do_run(profile, broker, scan_only, dry_run, scheduled):
    from .engine.runner import run as engine_run
    cfg = cfgmod.load()
    if not scan_only and not dry_run and not cfg.real_submissions_enabled:
        con.print("[red]Real submissions are not enabled yet.[/] Run a dry run first, then "
                  "`vanish config enable-submissions`.")
        raise typer.Exit(2)
    store = _store()
    rep = engine_run(store, _registry(), _select(store, profile), scan_only=scan_only,
                     dry_run=dry_run, interactive=not scheduled,
                     broker_ids=broker or None, only_due=scheduled)
    for line in rep.summary_lines():
        con.print(line)


@app.command()
def scan(profile: Optional[str] = typer.Option(None, "--profile", "-p"),
         broker: list[str] = typer.Option([], "--broker", "-b")):
    """Search brokers for listings. Never submits anything."""
    _do_run(profile, broker, scan_only=True, dry_run=True, scheduled=False)


@app.command()
def run(profile: Optional[str] = typer.Option(None, "--profile", "-p"),
        broker: list[str] = typer.Option([], "--broker", "-b"),
        dry_run: bool = typer.Option(False, "--dry-run", help="Search + report, submit nothing"),
        scheduled: bool = typer.Option(False, "--scheduled", hidden=True)):
    """Scan, submit opt-outs, check verifications and escalate ignored requests."""
    _do_run(profile, broker, scan_only=False, dry_run=dry_run, scheduled=scheduled)


@app.command()
def status(profile: Optional[str] = typer.Option(None, "--profile", "-p")):
    """Per-broker status for each person."""
    store, reg = _store(), _registry()
    names = {b.id: b.name for b in reg.brokers}
    for p in _select(store, profile):
        t = Table(title=f"{p.label}")
        for c in ("Broker", "State", "Updated", "Next check", "Escalation"):
            t.add_column(c)
        for st in sorted(store.list_statuses(p.id), key=lambda s: s.broker_id):
            t.add_row(names.get(st.broker_id, st.broker_id), st.state.value,
                      st.updated_at.strftime("%Y-%m-%d"),
                      st.next_check_at.strftime("%Y-%m-%d") if st.next_check_at else "-",
                      str(st.escalation_level))
        con.print(t)
        todos = store.list_todos(p.id)
        if todos:
            con.print(f"[yellow]{len(todos)} item(s) need you: `vanish todo list`[/]")
    con.print("[dim]'removed' means removed from that broker, not from the whole internet. "
              "Listings often reappear; Vanish keeps checking.[/]")


@app.command()
def report(profile: Optional[str] = typer.Option(None, "--profile", "-p"),
           fmt: str = typer.Option("html", "--format", help="html | pdf")):
    """Export a report (HTML or PDF)."""
    from .wizard.report import build_report
    store, reg = _store(), _registry()
    for p in _select(store, profile):
        con.print(f"Wrote {build_report(store, reg, p.id, fmt)}")


# --------------------------------------------------------------------------- profiles


@profile_app.command("add")
def profile_add(prefill: Optional[Path] = typer.Option(None)):
    setup(prefill=prefill, web=prefill is None)


@profile_app.command("list")
def profile_list():
    t = Table()
    for c in ("ID", "Label", "State", "Consent", "Mailbox"):
        t.add_column(c)
    for p in _store().list_profiles():
        t.add_row(p.id[:8], p.label, p.state_of_residence, p.consent.basis.value,
                  "yes" if p.mailbox else "no")
    con.print(t)


@profile_app.command("edit")
def profile_edit(profile: str):
    from .wizard.flows import edit_cli
    store = _store()
    p = _select(store, profile)[0]
    edit_cli(store, p.id)


@profile_app.command("remove")
def profile_remove(profile: str, yes: bool = typer.Option(False, "--yes")):
    """Delete a person and all their stored data from this computer."""
    store = _store()
    p = [x for x in store.list_profiles() if x.id.startswith(profile) or x.label == profile]
    if not p:
        raise typer.BadParameter("no such profile")
    if not yes and not typer.confirm(f"Permanently delete {p[0].label} and all evidence?"):
        raise typer.Exit()
    if p[0].mailbox:
        from .secrets import delete_mailbox_password
        delete_mailbox_password(p[0].id, p[0].mailbox)
    store.delete_profile(p[0].id)
    con.print("Deleted.")


@profile_app.command("export")
def profile_export(profile: str, dest: Path):
    """Create a passphrase-protected pre-filled profile for a family installer."""
    from .wizard.flows import export_family_bundle
    store = _store()
    p = _select(store, profile)[0]
    pw = typer.prompt("Passphrase (tell them by phone, not email)", hide_input=True,
                      confirmation_prompt=True)
    con.print(f"Wrote {export_family_bundle(store, p.id, dest, pw)}")


# --------------------------------------------------------------------------- schedule


@schedule_app.command("install")
def schedule_install():
    from . import scheduler
    con.print(scheduler.install())


@schedule_app.command("remove")
def schedule_remove():
    from . import scheduler
    con.print(scheduler.remove())


@schedule_app.command("status")
def schedule_status():
    from . import scheduler
    con.print(scheduler.status())


# --------------------------------------------------------------------------- registry


@registry_app.command("update")
def registry_update():
    from .registry import update_registry
    v, n = update_registry()
    con.print(f"Registry {v}: {n} brokers")


@registry_app.command("validate")
def registry_validate(path: Optional[Path] = typer.Argument(None)):
    from .registry import load_registry
    reg = load_registry(path)
    unver = sum(1 for b in reg.brokers if b.verification_status.value != "verified")
    con.print(f"OK: {len(reg.brokers)} brokers ({unver} unverified)")


@registry_app.command("show")
def registry_show():
    t = Table()
    for c in ("ID", "Name", "Method", "Verified", "Captcha", "Covered by"):
        t.add_column(c)
    for b in sorted(_registry().brokers, key=lambda b: -b.priority):
        t.add_row(b.id, b.name, b.method.value, b.verification_status.value,
                  "yes" if b.has_captcha else "", b.covered_by or "")
    con.print(t)


# --------------------------------------------------------------------------- todos / outbox


@todo_app.command("list")
def todo_list(profile: Optional[str] = typer.Option(None, "--profile", "-p")):
    store = _store()
    for p in _select(store, profile):
        for t in store.list_todos(p.id):
            con.print(f"[{t.id[:8]}] {p.label} · {t.kind.value} · {t.title}")


@todo_app.command("done")
def todo_done(todo_id: str):
    store = _store()
    match = [t for t in store.list_todos() if t.id.startswith(todo_id)]
    if not match:
        raise typer.BadParameter("no such open to-do")
    store.complete_todo(match[0].id)
    con.print("Marked done.")


@outbox_app.command("list")
def outbox_list():
    store = _store()
    for r in store.list_requests(status=RequestStatus.QUEUED_FOR_APPROVAL):
        con.print(f"[{r.id[:8]}] {r.broker_id} · {r.kind.value} · created {r.created_at:%Y-%m-%d}")


@outbox_app.command("approve")
def outbox_approve(request_id: str):
    from .engine.outbox import approve_and_send
    store = _store()
    match = [r for r in store.list_requests(status=RequestStatus.QUEUED_FOR_APPROVAL)
             if r.id.startswith(request_id)]
    if not match:
        raise typer.BadParameter("no such queued email")
    approve_and_send(store, match[0].id)
    con.print("Sent.")


# --------------------------------------------------------------------------- config


@config_app.command("set")
def config_set(key: str, value: str):
    cfg = cfgmod.load()
    if key not in type(cfg).model_fields or key == "real_submissions_enabled":
        raise typer.BadParameter(f"unknown or protected key {key}")
    field = type(cfg).model_fields[key]
    cur = getattr(cfg, key)
    if isinstance(cur, bool):
        val: object = value.lower() in ("1", "true", "yes")
    elif isinstance(cur, (int, float)):
        val = type(cur)(value)
    elif isinstance(cur, list):
        val = [v.strip() for v in value.split(",") if v.strip()]
    else:
        val = value or None
    del field
    cfgmod.save(cfg.model_copy(update={key: val}))
    con.print(f"{key} updated")


@config_app.command("enable-submissions")
def config_enable_submissions():
    """One-time explicit opt-in to real (non-dry-run) opt-out submissions."""
    con.print("Vanish will submit real opt-out requests to data brokers using the "
              "information in each profile (only what each broker already shows).")
    if typer.confirm("Enable real submissions?"):
        cfg = cfgmod.load()
        cfgmod.save(cfg.model_copy(update={"real_submissions_enabled": True}))
        con.print("[green]Enabled.[/]")


if __name__ == "__main__":
    app()
