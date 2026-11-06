"""`vanish` command line. OWNER: orchestrator. Thin layer: all logic lives in modules."""
from __future__ import annotations

import logging
import os
import sys
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Annotated, TypeVar

import typer
from rich.console import Console
from rich.table import Table

from . import config as cfgmod
from . import logging_setup, paths
from .consent import consent_ok
from .models import Profile, RequestStatus

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
log = logging.getLogger("vanish.cli")


def _store():
    from .storage import Store
    return Store()


def _registry():
    from .registry import load_registry
    return load_registry()


T = TypeVar("T")


def _pick_one(items: Sequence[T], key: str, what: str, ident: Callable[[T], str],
              describe: Callable[[T], str],
              alias: Callable[[T], str] | None = None) -> T:
    """Exactly one item whose id starts with `key` (or whose alias equals it).

    A full id match wins. Otherwise zero or several matches list the candidates and exit
    with code 2, so a short prefix never acts on the wrong record (SEC-12).
    """
    if not key:
        raise typer.BadParameter(f"empty {what} id")
    exact = [x for x in items if ident(x) == key]
    if len(exact) == 1:
        return exact[0]
    k = key.lower()
    match = [x for x in items if ident(x).startswith(key)
             or (alias is not None and alias(x).lower() == k)]
    if len(match) == 1:
        return match[0]
    if not match:
        con.print(f"[red]No {what} matches {key!r}.[/]")
    else:
        con.print(f"[red]{key!r} matches {len(match)} {what}s; use more of the id:[/]")
        for x in match:
            con.print(f"  {ident(x)[:12]}  {describe(x)}")
    raise typer.Exit(2)


def _one_profile(store, key: str) -> Profile:
    return _pick_one(store.list_profiles(), key, "profile", lambda p: p.id,
                     lambda p: p.label, alias=lambda p: p.label)


def _require_consent(store, p: Profile) -> Profile:
    good, why = consent_ok(p, store)
    if not good:
        con.print(f"[red]{p.label}: {why}[/]")
        raise typer.Exit(1)
    return p


def _select(store, profile: str | None) -> list[Profile]:
    ps = [_one_profile(store, profile)] if profile else store.list_profiles()
    ok = []
    for p in ps:
        good, why = consent_ok(p, store)
        if good:
            ok.append(p)
        else:
            con.print(f"[yellow]Skipping {p.label}: {why}[/]")
    return ok


def _harden_home() -> None:
    """Private files by default (SEC-14): umask 077 and a 0700 data directory."""
    os.umask(0o077)
    if sys.platform == "win32":
        return
    try:
        h = paths.home()
        if h.stat().st_mode & 0o077:
            h.chmod(0o700)
    except OSError as e:
        con.print(f"[yellow]Could not make the Vanish data folder private: {e}[/]")


@app.callback()
def _main(verbose: Annotated[bool, typer.Option("--verbose", "-v")] = False) -> None:
    _harden_home()
    logging_setup.setup(verbose)


# --------------------------------------------------------------------------- top level


@app.command()
def setup(prefill: Annotated[Path | None,
                             typer.Option(help="Family bundle (.vanish-profile)")] = None,
          web: Annotated[bool, typer.Option(
              help="Open the web wizard (else terminal prompts)")] = True):
    """Walk through setup for a person (opens the local web wizard by default)."""
    if web:
        from .wizard.server import serve
        serve(cfgmod.load().wizard_port, open_browser=True)
    else:
        from .wizard.flows import setup_cli
        p = setup_cli(_store(), prefill=prefill)
        con.print(f"[green]Saved profile {p.label} ({p.id[:8]})[/]")


@app.command("app")
def app_window(no_window: Annotated[bool, typer.Option(
        "--no-window", help="Use the web browser instead of an app window")] = False):
    """Open Vanish in its own window (wizard on first launch, dashboard after)."""
    from .wizard.desktop import main as desktop_main
    raise typer.Exit(desktop_main(window=not no_window))


@app.command()
def dashboard():
    """Open the local dashboard (status, evidence, to-dos, approvals)."""
    from .wizard.server import serve
    serve(cfgmod.load().wizard_port, open_browser=True)


def _do_run(profile, broker, scan_only, dry_run, scheduled):
    from .engine.runner import run as engine_run
    cfg = cfgmod.load()
    if scheduled and not cfg.real_submissions_enabled:
        dry_run = True   # practice mode: the daily task still runs, just as a dry run (SEC-22)
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
def scan(profile: Annotated[str | None, typer.Option("--profile", "-p")] = None,
         broker: Annotated[list[str] | None, typer.Option("--broker", "-b")] = None):
    """Search brokers for listings. Never submits anything."""
    _do_run(profile, broker or [], scan_only=True, dry_run=True, scheduled=False)


@app.command()
def run(profile: Annotated[str | None, typer.Option("--profile", "-p")] = None,
        broker: Annotated[list[str] | None, typer.Option("--broker", "-b")] = None,
        dry_run: Annotated[bool, typer.Option(
            "--dry-run", help="Search + report, submit nothing")] = False,
        scheduled: Annotated[bool, typer.Option("--scheduled", hidden=True)] = False):
    """Scan, submit opt-outs, check verifications and escalate ignored requests."""
    _do_run(profile, broker or [], scan_only=False, dry_run=dry_run, scheduled=scheduled)


@app.command()
def status(profile: Annotated[str | None, typer.Option("--profile", "-p")] = None):
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
def report(profile: Annotated[str | None, typer.Option("--profile", "-p")] = None,
           fmt: Annotated[str, typer.Option("--format", help="html | pdf")] = "html"):
    """Export a report (HTML or PDF)."""
    from .wizard.report import build_report
    store, reg = _store(), _registry()
    for p in _select(store, profile):
        con.print(f"Wrote {build_report(store, reg, p.id, fmt)}")


# --------------------------------------------------------------------------- profiles


@profile_app.command("add")
def profile_add(prefill: Annotated[Path | None, typer.Option()] = None):
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
    p = _require_consent(store, _one_profile(store, profile))
    edit_cli(store, p.id)


@profile_app.command("remove")
def profile_remove(profile: str, yes: Annotated[bool, typer.Option("--yes")] = False):
    """Delete a person and all their stored data from this computer."""
    store = _store()
    p = _one_profile(store, profile)
    if not yes and not typer.confirm(f"Permanently delete {p.label} ({p.id[:8]}) "
                                     "and all evidence?"):
        raise typer.Exit()
    if p.mailbox:
        from .secrets import delete_mailbox_password
        delete_mailbox_password(p.id, p.mailbox)
    store.delete_profile(p.id)
    con.print("Deleted.")


@app.command()
def wipe(yes: Annotated[bool, typer.Option("--yes")] = False):
    """Delete everything Vanish saved on this computer: people, evidence, mailbox passwords,
    the encryption key and the background task. Used by the Windows uninstaller."""
    import shutil

    from . import crypto
    target = paths.home()
    if not paths.is_safe_wipe_target(target):
        con.print(f"[red]Refusing to wipe {target}:[/] it doesn't look like a Vanish data folder.")
        raise typer.Exit(2)
    if not yes and not typer.confirm("Delete ALL Vanish data on this computer?"):
        raise typer.Exit()
    try:
        from .scheduler import remove as sched_remove
        sched_remove()
    except Exception:  # noqa: BLE001  best effort; the task may not exist
        log.warning("wipe: scheduler removal failed")
    if paths.db_path().exists():
        try:
            from .secrets import delete_mailbox_password
            store = _store()
            for p in store.list_profiles():
                if p.mailbox:
                    delete_mailbox_password(p.id, p.mailbox)
            store.close()
        except Exception:  # noqa: BLE001  key may already be gone; still delete files
            log.warning("wipe: could not read profiles to remove mailbox passwords")
    crypto.delete_key()
    for name in paths.OWNED_ENTRIES:   # only what Vanish created; never rmtree the folder itself
        e = target / name
        if e.is_dir() and not e.is_symlink():
            shutil.rmtree(e, ignore_errors=True)
        elif e.exists() or e.is_symlink():
            e.unlink(missing_ok=True)
    try:
        target.rmdir()                  # only succeeds if nothing else is left in it
    except OSError:
        pass
    con.print("All Vanish data deleted.")


@profile_app.command("export")
def profile_export(profile: str, dest: Path):
    """Create a passphrase-protected pre-filled profile for a family installer."""
    from .wizard.flows import export_family_bundle
    store = _store()
    p = _require_consent(store, _one_profile(store, profile))
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
def registry_validate(path: Annotated[Path | None, typer.Argument()] = None):
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
def todo_list(profile: Annotated[str | None, typer.Option("--profile", "-p")] = None):
    store = _store()
    for p in _select(store, profile):
        for t in store.list_todos(p.id):
            con.print(f"[{t.id[:8]}] {p.label} · {t.kind.value} · {t.title}")


@todo_app.command("done")
def todo_done(todo_id: str):
    store = _store()
    t = _pick_one(store.list_todos(), todo_id, "open to-do", lambda t: t.id,
                  lambda t: f"{t.kind.value} · {t.title}")
    store.complete_todo(t.id)
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
    r = _pick_one(store.list_requests(status=RequestStatus.QUEUED_FOR_APPROVAL), request_id,
                  "queued email", lambda r: r.id, lambda r: f"{r.broker_id} · {r.kind.value}")
    approve_and_send(store, r.id)
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
