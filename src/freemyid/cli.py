"""`freemyid` command line. OWNER: orchestrator. Thin layer: all logic lives in modules."""
from __future__ import annotations

import logging
import os
import sys
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Annotated, NoReturn, TypeVar

import typer
from rich.console import Console
from rich.table import Table

from . import cli_json as cj
from . import config as cfgmod
from . import logging_setup, paths
from .consent import consent_ok
from .models import Profile, RequestStatus

app = typer.Typer(help="Free My ID: remove your info from data brokers, and keep it removed.",
                  no_args_is_help=True)
profile_app = typer.Typer(help="Manage people (profiles).", no_args_is_help=True)
schedule_app = typer.Typer(help="Install/remove the background re-check job.",
                           no_args_is_help=True)
registry_app = typer.Typer(help="Broker registry.", no_args_is_help=True)
todo_app = typer.Typer(help="Things that need a human.", no_args_is_help=True)
outbox_app = typer.Typer(help="Emails waiting for your approval.", no_args_is_help=True)
config_app = typer.Typer(help="Settings.", no_args_is_help=True)
secrets_app = typer.Typer(help="Where Free My ID keeps its encryption key and passwords.",
                          no_args_is_help=True)
for name, sub in (("profile", profile_app), ("schedule", schedule_app),
                  ("registry", registry_app), ("todo", todo_app), ("outbox", outbox_app),
                  ("config", config_app), ("secrets", secrets_app)):
    app.add_typer(sub, name=name)

con = Console()
err = Console(stderr=True)
log = logging.getLogger("freemyid.cli")

#: Set by a command running with --json: human messages then go to stderr so stdout is
#: exactly one JSON document (docs/CLI.md).
_json_mode = False

JsonOpt = Annotated[bool, typer.Option("--json", help="Machine-readable output (docs/CLI.md)")]


def _ui() -> Console:
    return err if _json_mode else con


def _set_json(on: bool) -> None:
    global _json_mode
    _json_mode = on


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
        _ui().print(f"[red]No {what} matches {key!r}.[/]")
    else:
        _ui().print(f"[red]{key!r} matches {len(match)} {what}s; use more of the id:[/]")
        for x in match:
            _ui().print(f"  {ident(x)[:12]}  {describe(x)}")
    raise typer.Exit(cj.EXIT_USAGE)


def _one_profile(store, key: str) -> Profile:
    return _pick_one(store.list_profiles(), key, "profile", lambda p: p.id,
                     lambda p: p.label, alias=lambda p: p.label)


def _require_consent(store, p: Profile) -> Profile:
    good, why = consent_ok(p, store)
    if not good:
        con.print(f"[red]{p.label}: {why}[/]")
        raise typer.Exit(1)
    return p


def _select(store, profile: str | None, skipped: list[dict] | None = None) -> list[Profile]:
    ps = [_one_profile(store, profile)] if profile else store.list_profiles()
    ok = []
    for p in ps:
        good, why = consent_ok(p, store)
        if good:
            ok.append(p)
        else:
            _ui().print(f"[yellow]Skipping {p.label}: {why}[/]")
            if skipped is not None:
                skipped.append(cj.skipped_entry(p, why))
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
        con.print(f"[yellow]Could not make the Free My ID data folder private: {e}[/]")


@app.callback()
def _main(verbose: Annotated[bool, typer.Option("--verbose", "-v")] = False) -> None:
    _set_json(False)
    _harden_home()
    logging_setup.setup(verbose)


# --------------------------------------------------------------------------- top level


@app.command()
def setup(prefill: Annotated[Path | None,
                             typer.Option(help="Family bundle (.freemyid-profile)")] = None,
          web: Annotated[bool | None, typer.Option(
              help="Open the web wizard (else terminal prompts; --prefill implies terminal)")] = None,
          from_file: Annotated[Path | None, typer.Option(
              "--from", help="Set up from a YAML file, no wizard (docs/CLI.md)")] = None,
          yes: Annotated[bool, typer.Option(
              "--yes", help="With --from: confirm without asking")] = False,
          check: Annotated[bool, typer.Option(
              "--check", help="With --from: validate and show the plan; save nothing")] = False,
          update: Annotated[bool, typer.Option(
              "--update", help="With --from: replace the person with the same label")] = False):
    """Walk through setup for a person (opens the local web wizard by default)."""
    if from_file is not None:
        _setup_from(from_file, yes=yes, check=check, update=update)
        return
    if web and prefill is not None:
        con.print("A family setup file can't be opened with --web. Open the wizard and use "
                  "its Import screen (/wizard/import), or drop --web to answer in the terminal.")
        raise typer.Exit(2)
    if web is None:
        web = prefill is None
    if web:
        from .wizard.server import serve
        serve(cfgmod.load().wizard_port, open_browser=True)
    else:
        from .wizard.flows import setup_cli
        p = setup_cli(_store(), prefill=prefill)
        con.print(f"[green]Saved profile {p.label} ({p.id[:8]})[/]")


@app.command()
def doctor(offline: Annotated[bool, typer.Option(
               "--offline", help="Skip the mail server reachability check")] = False,
           as_json: JsonOpt = False):
    """Check this computer is ready: Python, data folder, secrets, browser, schedule, mail."""
    from . import doctor as dmod
    checks = dmod.run_checks(network=not offline)
    if as_json:
        cj.emit(dmod.doc(checks))
    else:
        style = {"ok": "green", "warn": "yellow", "fail": "red"}
        for c in checks:
            con.print(f"[{style[c.status]}]{c.status.upper():4}[/] {c.title}: ", end="")
            con.print(c.detail, markup=False, highlight=False, soft_wrap=True)
            if c.fix and c.status != "ok":
                con.print("     fix: ", end="")
                con.print(c.fix, markup=False, highlight=False, soft_wrap=True)
    if any(c.status == "fail" for c in checks):
        raise typer.Exit(cj.EXIT_ERROR)


def _setup_from(path: Path, *, yes: bool, check: bool, update: bool) -> None:
    """Non-interactive setup from a versioned YAML file (setup_config.py)."""
    from . import setup_config as sc
    from .wizard.draft import SaveError, save_draft
    try:
        cfg = sc.load(path)
        d = sc.to_draft(cfg, path.resolve().parent)
    except sc.SetupFileError as e:
        err.print(f"freemyid: {path.name} has {len(e.problems)} problem(s):", markup=False)
        for line in e.problems:
            err.print(f"  - {line}", markup=False, highlight=False, soft_wrap=True)
        raise typer.Exit(cj.EXIT_USAGE) from None
    for line in sc.plan_lines(cfg):
        con.print(line, markup=False, highlight=False, soft_wrap=True)
    if check:
        con.print("Check only: the file is valid; nothing was saved.")
        return
    store = _open_store_or_fail()
    prior = sc.find_existing(store, d.label or d.first)
    if prior is not None and not update:
        _fail(cj.EXIT_USAGE, f"someone called {prior.label!r} is already set up; use --update "
              "to replace them, or change person.label")
    if prior is not None:
        d.id, d.editing = prior.id, True
    if not yes:
        try:
            ok = typer.confirm("Save this person and give this permission?", default=False)
        except typer.Abort:
            ok = False
        if not ok:
            _fail(cj.EXIT_USAGE, "not confirmed; nothing saved (add --yes to confirm "
                  "without a prompt)")
    try:
        prof = save_draft(store, d)
    except SaveError as e:
        _fail(cj.EXIT_ERROR, str(e))
    con.print(f"[green]Saved {prof.label} ({prof.id[:8]}).[/] Next: `freemyid run --dry-run`.")
    if cfg.schedule.install_job and cfg.schedule.weekly_recheck:
        from . import scheduler
        con.print(scheduler.install())


@app.command("app")
def app_window(no_window: Annotated[bool, typer.Option(
        "--no-window", help="Use the web browser instead of an app window")] = False):
    """Open Free My ID in its own window (wizard on first launch, dashboard after)."""
    from .wizard.desktop import main as desktop_main
    raise typer.Exit(desktop_main(window=not no_window))


@app.command()
def dashboard():
    """Open the local dashboard (status, evidence, to-dos, approvals)."""
    from .wizard.server import serve
    serve(cfgmod.load().wizard_port, open_browser=True)


def _fail(code: int, reason: str) -> NoReturn:
    """Stop with `code` and a one-line reason (stderr; also a JSON document with --json)."""
    if _json_mode:
        cj.emit(cj.failure_doc(code, reason))
    err.print(f"freemyid: {reason}", markup=False, highlight=False, soft_wrap=True)
    raise typer.Exit(code)


def _open_store_or_fail():
    from .crypto import KeyUnavailable
    try:
        return _store()
    except KeyUnavailable as e:
        _fail(cj.EXIT_NOT_CONFIGURED,
              f"not configured: the encryption key is unavailable ({e}); "
              "run `freemyid doctor` for the fix")


def _do_run(profile, broker, scan_only, dry_run, scheduled, headless: bool = False,
            as_json: bool = False):
    """Shared body of `scan` and `run`.

    Headless (cron/systemd/Docker): never prompts, never opens a window, and fails closed
    with exit 4 (not configured) or 3 (needs a person) plus a one-line reason. After a
    headless run the exit code says how it went (docs/CLI.md).
    """
    from .engine.runner import run as engine_run
    _set_json(as_json)
    cfg = cfgmod.load()
    if scheduled and not cfg.real_submissions_enabled:
        dry_run = True   # practice mode: the daily task still runs, just as a dry run (SEC-22)
    if not scan_only and not dry_run and not cfg.real_submissions_enabled:
        if headless or as_json:
            _fail(cj.EXIT_NOT_CONFIGURED if headless else cj.EXIT_USAGE,
                  "real submissions are not enabled (practice mode); use --dry-run, or run "
                  "`freemyid config enable-submissions` once")
        con.print("[red]Real submissions are not enabled yet.[/] Run a dry run first, then "
                  "`freemyid config enable-submissions`.")
        raise typer.Exit(2)
    if headless and not paths.db_path().exists():
        _fail(cj.EXIT_NOT_CONFIGURED, "not configured: nobody is set up yet; run "
              "`freemyid setup` or `freemyid setup --from config.yaml`")
    store = _open_store_or_fail()
    skipped: list[dict] = []
    people = _select(store, profile, skipped)
    if headless and not people:
        if not skipped:
            _fail(cj.EXIT_NOT_CONFIGURED, "not configured: nobody is set up yet; run "
                  "`freemyid setup` or `freemyid setup --from config.yaml`")
        _fail(cj.EXIT_NEEDS_HUMAN, f"needs a person: no profile has valid permission "
              f"({len(skipped)} skipped); open Free My ID to give permission")
    from .engine import search_session as ss
    if scheduled and people and not headless and ss.background_supported():
        # WO-612: home browser first, off-screen, never raises, so the runner finds today's
        # reads (practice mode too). Windows task only until WO-616 checks macOS/Linux, and
        # never with --headless (cron/launchd/systemd/Docker): SEC-WO612-2.
        ss.run_for_profiles(store, [p.id for p in people], mode="background",
                            registry=_registry(), cfg=cfg)
    rep = engine_run(store, _registry(), people, scan_only=scan_only,
                     dry_run=dry_run, interactive=not (scheduled or headless),
                     broker_ids=broker or None, only_due=scheduled)
    code = cj.EXIT_OK
    if headless:
        if rep.needs_human:
            code = cj.EXIT_NEEDS_HUMAN
        elif rep.errors:
            code = cj.EXIT_ERROR
    if as_json:
        cj.emit(cj.run_doc(rep, scan_only=scan_only, headless=headless, exit_code=code,
                           skipped=skipped))
    else:
        for line in rep.summary_lines():
            con.print(line)
    if scheduled and not dry_run:
        # BL-IN-25: the app is often closed, so the monthly PII-free summary also fires after a
        # scheduled run. Never let a notification problem change the run's result.
        try:
            from . import notify
            notify.maybe_monthly_progress(store)
        except Exception:  # a toast must never fail the run
            log.debug("monthly summary toast skipped", exc_info=True)
    if code:
        raise typer.Exit(code)


_SESSION_REASONS = {
    "no_consent": "skipped: permission to search is not given",
    "no_display": "skipped: no screen to open a browser window on",
    "busy": "skipped: another search window is already open",
    "error": "could not finish this time; the next run tries again",
}


def _attended_scan(profile: str | None) -> None:
    """`scan --attended` (WO-612): one visible window of the person's own browser; the
    wizard's "Look for me now" button calls the same engine entry point."""
    from .engine import search_session as ss
    store = _open_store_or_fail()
    people = _select(store, profile)
    if not people:
        con.print("Nobody with permission to search is set up yet.")
        raise typer.Exit(cj.EXIT_NEEDS_HUMAN)
    out = ss.run_for_profiles(store, [p.id for p in people], mode="attended",
                              registry=_registry())
    for p in people:
        res = out.get(p.id, "error")
        if isinstance(res, str):
            con.print(f"{p.label}: {_SESSION_REASONS.get(res, res)}")
            continue
        read = res.count(ss.Outcome.READ, ss.Outcome.SELF_CLEARED,
                         ss.Outcome.READ_AFTER_CHALLENGE, ss.Outcome.CACHED)
        by_hand = res.count(ss.Outcome.TIMED_OUT, ss.Outcome.SKIPPED, ss.Outcome.HAND_CHECK)
        line = f"{p.label}: checked {read} site{'s' if read != 1 else ''}"
        if by_hand:
            line += f"; {by_hand} to check yourself (see `freemyid todo`)"
        con.print(line)


@app.command()
def scan(profile: Annotated[str | None, typer.Option("--profile", "-p")] = None,
         broker: Annotated[list[str] | None, typer.Option("--broker", "-b")] = None,
         headless: Annotated[bool, typer.Option(
             "--headless", help="No prompts or windows; fail closed (cron/Docker)")] = False,
         attended: Annotated[bool, typer.Option(
             "--attended", help="Open your browser and look for you now; a site may ask you "
                                "to tick a box.")] = False,
         as_json: JsonOpt = False):
    """Search brokers for listings. Never submits anything."""
    if attended:
        if headless or as_json or broker:
            _fail(cj.EXIT_USAGE, "--attended cannot be combined with --headless, --json or "
                  "--broker")
        _attended_scan(profile)
        return
    _do_run(profile, broker or [], scan_only=True, dry_run=True, scheduled=False,
            headless=headless, as_json=as_json)


@app.command()
def run(profile: Annotated[str | None, typer.Option("--profile", "-p")] = None,
        broker: Annotated[list[str] | None, typer.Option("--broker", "-b")] = None,
        dry_run: Annotated[bool, typer.Option(
            "--dry-run", help="Search + report, submit nothing")] = False,
        headless: Annotated[bool, typer.Option(
            "--headless", help="No prompts or windows; fail closed (cron/systemd/Docker)")
        ] = False,
        as_json: JsonOpt = False,
        scheduled: Annotated[bool, typer.Option("--scheduled", hidden=True)] = False):
    """Scan, submit opt-outs, check verifications and escalate ignored requests."""
    _do_run(profile, broker or [], scan_only=False, dry_run=dry_run, scheduled=scheduled,
            headless=headless, as_json=as_json)


@app.command()
def fill(broker: Annotated[str, typer.Argument(help="Broker id")],
         profile: Annotated[str | None, typer.Option("--profile", "-p")] = None,
         timeout: Annotated[int, typer.Option("--timeout", min=30, max=3600)] = 600):
    """Open the broker's form in a visible window and fill it in; you tick the box and Submit."""
    from .engine.fill_for_me import fill_for_me_sync
    store = _store()
    people = _select(store, profile)
    if len(people) != 1:
        con.print("[red]Choose one person with --profile.[/]")
        raise typer.Exit(2)
    res = fill_for_me_sync(store, people[0].id, broker, timeout_s=timeout)
    con.print(f"{res.status}: {res.reason}")
    if res.filled:
        con.print("Filled: " + ", ".join(res.filled))
    raise typer.Exit(0 if res.ok else 1)


@app.command()
def status(profile: Annotated[str | None, typer.Option("--profile", "-p")] = None,
           as_json: JsonOpt = False):
    """Per-broker status for each person."""
    _set_json(as_json)
    store, reg = _open_store_or_fail(), _registry()
    names = {b.id: b.name for b in reg.brokers}
    skipped: list[dict] = []
    people = _select(store, profile, skipped)
    if as_json:
        cj.emit(cj.status_doc([(p, store.list_statuses(p.id), len(store.list_todos(p.id)))
                               for p in people], names, skipped))
        return
    for p in people:
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
            con.print(f"[yellow]{len(todos)} item(s) need you: `freemyid todo list`[/]")
    con.print("[dim]'removed' means removed from that broker, not from the whole internet. "
              "Listings often reappear; Free My ID keeps checking.[/]")


@app.command()
def exposure(profile: Annotated[str | None, typer.Option("--profile", "-p")] = None,
             offline: Annotated[bool, typer.Option(
                 "--offline", help="Fetch nothing; use what earlier runs found")] = False,
             refresh: Annotated[bool, typer.Option(
                 "--refresh", help="Check every site again, even if checked today")] = False,
             old_addresses: Annotated[bool, typer.Option(
                 "--old-addresses",
                 help="Also search each site once at your previous address (off by default; "
                      "at most one extra page per site)")] = False,
             headless: Annotated[bool, typer.Option(
                 "--headless", help="No prompts or windows; fail closed (cron/Docker)")
             ] = False,
             as_json: JsonOpt = False):
    """Find me first: which people-search sites show you, with a 0-100 exposure score.

    Reads only (never submits), so it also runs in practice mode. Sites that block
    automatic checks are listed with the link to open yourself (docs/EXPOSURE.md)."""
    from rich.markup import escape

    from .engine import exposure as ex
    _set_json(as_json)
    if headless and not paths.db_path().exists():
        _fail(cj.EXIT_NOT_CONFIGURED, "not configured: nobody is set up yet; run "
              "`freemyid setup` or `freemyid setup --from config.yaml`")
    store = _open_store_or_fail()
    skipped: list[dict] = []
    people = _select(store, profile, skipped)
    if not people:
        if not skipped:
            _fail(cj.EXIT_NOT_CONFIGURED, "not configured: nobody is set up yet; run "
                  "`freemyid setup` or `freemyid setup --from config.yaml`")
        _fail(cj.EXIT_NEEDS_HUMAN, f"needs a person: no profile has valid permission "
              f"({len(skipped)} skipped); open Free My ID to give permission")
    reg = _registry()
    rows = []
    for p in people:
        try:
            rows.append((p, ex.scan_exposure(store, p.id, registry=reg, offline=offline,
                                             refresh=refresh, use_browser=not offline,
                                             old_addresses=True if old_addresses else None)))
        except ex.ExposureRefused as refused:
            skipped.append(cj.skipped_entry(p, refused.reason))
    trends = {p.id: ex.exposure_trend(store, p.id) for p, _ in rows}
    if as_json:
        cj.emit(cj.exposure_doc(rows, offline=offline, headless=headless,
                                exit_code=cj.EXIT_OK, skipped=skipped, trends=trends))
        return
    from .exposure_models import DROP_NOTE, HAND_REASONS
    for p, r in rows:
        con.print(f"[bold]{escape(p.label)}[/]: exposure score [bold]{r.score}[/] / 100"
                  + (" (practice mode)" if r.practice_mode else ""))
        con.print("\n".join(ex.score_text_lines(r)), markup=False)
        if len(trends[p.id].points) >= 2:
            con.print(f"  {trends[p.id].note}", markup=False)
        if r.first_checklist:
            con.print(f"  [bold]First:[/] {escape(DROP_NOTE)} See: freemyid checklist show "
                      f"{r.first_checklist}")
        for ln in r.explanation:
            sign = f"+{ln.points}" if ln.points > 0 else str(ln.points) if ln.points else "  "
            con.print(f"  {sign:>4}  {escape(ln.text)}")
        for e in r.by_status("found"):
            lvl = "is you" if e.match_level and e.match_level.value == "confirmed" \
                else "may be you"
            con.print(f"  [red]Found[/] {escape(e.broker_name)}: {len(e.listings)} listing(s) "
                      f"that {lvl}")
            for li in e.listings:
                con.print(f"      {li.url}", markup=False, highlight=False, soft_wrap=True)
        hand = r.by_status("check_by_hand")
        if hand:
            con.print("  [yellow]Please check these yourself[/] (open the link, look for "
                      "your name):")
            for e in hand:
                why = HAND_REASONS.get(e.reason or "", "")
                con.print(f"    {escape(e.broker_name)}: {escape(why)}")
                if e.check_url:
                    con.print(f"      {e.check_url}", markup=False, highlight=False,
                              soft_wrap=True)
        clean = r.by_status("not_found")
        if clean:
            con.print(f"  [green]Not found[/] on {len(clean)} site(s): "
                      + escape(", ".join(e.broker_name for e in clean)))
    _search_engine_footer(store, [p for p, _r in rows])


def _search_engine_footer(store, people: list[Profile]) -> None:
    """'Google and Bing: N steps to do.' per person with N > 0 (never fails exposure)."""
    from .engine import search_engines as se
    for p in people:
        try:
            n = se.pending(se.guided_steps(store, p.id))
        except Exception as e:  # noqa: BLE001  a hint line must not break the report
            log.warning("search-engine steps unavailable: %s", type(e).__name__)
            continue
        if n <= 0:
            continue
        who = f"{p.label}: " if len(people) > 1 else ""
        cmd = f"freemyid search-engines -p {p.id[:12]}" if len(people) > 1 \
            else "freemyid search-engines"
        con.print(f"{who}Google and Bing: {n} step{'s' if n != 1 else ''} to do. "
                  f"Run {cmd}.", markup=False, highlight=False)


@app.command()
def report(profile: Annotated[str | None, typer.Option("--profile", "-p")] = None,
           fmt: Annotated[str, typer.Option("--format", help="html | pdf")] = "html",
           as_json: JsonOpt = False):
    """Export a report (HTML or PDF)."""
    from .wizard.report import build_report
    _set_json(as_json)
    if fmt not in ("html", "pdf"):
        raise typer.BadParameter("--format must be html or pdf")
    store, reg = _open_store_or_fail(), _registry()
    skipped: list[dict] = []
    rows = []
    for p in _select(store, profile, skipped):
        out = build_report(store, reg, p.id, fmt)
        rows.append((p, fmt, str(out)))
        if not as_json:
            con.print(f"Wrote {out}")
    if as_json:
        cj.emit(cj.reports_doc(rows, skipped))


# --------------------------------------------------------------------------- profiles


@profile_app.command("add")
def profile_add(prefill: Annotated[Path | None, typer.Option()] = None):
    setup(prefill=prefill, web=prefill is None)


@profile_app.command("list")
def profile_list(as_json: JsonOpt = False):
    """Everyone set up on this computer."""
    _set_json(as_json)
    store = _open_store_or_fail()
    if as_json:
        cj.emit(cj.profiles_doc([(p, consent_ok(p, store)[0]) for p in store.list_profiles()]))
        return
    t = Table()
    for c in ("ID", "Label", "State", "Consent", "Mailbox"):
        t.add_column(c)
    for p in store.list_profiles():
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
    """Delete everything Free My ID saved on this computer.
    People, evidence, mailbox passwords, the encryption key and the background task go. Used by the Windows uninstaller."""
    import shutil

    from . import crypto
    target = paths.home()
    if not paths.is_safe_wipe_target(target):
        con.print(f"[red]Refusing to wipe {target}:[/] it doesn't look like a Free My ID data folder.")
        raise typer.Exit(2)
    # Only the main folder's key can be shared with older extra folders (WO-605 review F5),
    # so only wiping the main folder warns about other folders. Text: _wipe_question below.
    if not yes and not typer.confirm(_wipe_question(target)):
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
    # Close our own log files first: Windows refuses to delete a file that is still open.
    for lg in (logging.getLogger(), logging.getLogger("freemyid")):
        for h in list(lg.handlers):
            if isinstance(h, logging.FileHandler):
                h.close()
                lg.removeHandler(h)
    for name in paths.OWNED_ENTRIES:   # only what Free My ID created; never rmtree the folder itself
        e = target / name
        if e.is_dir() and not e.is_symlink():
            shutil.rmtree(e, ignore_errors=True)
        elif e.exists() or e.is_symlink():
            e.unlink(missing_ok=True)
    try:
        target.rmdir()                  # only succeeds if nothing else is left in it
    except OSError:
        pass
    con.print("All Free My ID data deleted.")


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
def schedule_status(as_json: JsonOpt = False):
    from . import scheduler
    detail = scheduler.status()
    if as_json:
        try:
            plat: str | None = scheduler.platform_name()
        except RuntimeError:
            plat = None
        cj.emit(cj.schedule_doc(plat, detail))
        return
    con.print(detail)


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


@registry_app.command("source")
def registry_source_cmd(plain: Annotated[bool, typer.Option("--plain")] = False,
                        as_json: JsonOpt = False):
    """Which broker list is in use: update, family, full or sample."""
    from .registry import load_registry, load_warnings, registry_source
    reg = load_registry()
    if as_json:
        cj.emit(cj.registry_source_doc(reg, registry_source(), load_warnings))
        return
    if plain:
        print(registry_source())
        return
    con.print(f"{registry_source()}: {len(reg.brokers)} brokers (version {reg.version})")
    for w in load_warnings:
        con.print(f"[yellow]warning:[/] {w}")


@registry_app.command("show")
def registry_show(as_json: JsonOpt = False):
    """Every broker in the registry in use, highest priority first."""
    if as_json:
        from .registry import load_warnings, registry_source
        reg = _registry()
        cj.emit(cj.registry_doc(reg, registry_source(), load_warnings))
        return
    t = Table()
    for c in ("ID", "Name", "Method", "Verified", "Captcha", "Covered by"):
        t.add_column(c)
    for b in sorted(_registry().brokers, key=lambda b: -b.priority):
        t.add_row(b.id, b.name, b.method.value, b.verification_status.value,
                  "yes" if b.has_captcha else "", b.covered_by or "")
    con.print(t)


# --------------------------------------------------------------------------- todos / outbox


@todo_app.command("list")
def todo_list(profile: Annotated[str | None, typer.Option("--profile", "-p")] = None,
              as_json: JsonOpt = False):
    """Open to-dos (things that need a person)."""
    _set_json(as_json)
    store = _open_store_or_fail()
    skipped: list[dict] = []
    rows = [(p, t) for p in _select(store, profile, skipped) for t in store.list_todos(p.id)]
    if as_json:
        cj.emit(cj.todos_doc(rows, skipped))
        return
    for p, t in rows:
        con.print(f"[{t.id[:8]}] {p.label} · {t.kind.value} · {t.title}", markup=False)


@todo_app.command("done")
def todo_done(todo_id: str):
    store = _store()
    t = _pick_one(store.list_todos(), todo_id, "open to-do", lambda t: t.id,
                  lambda t: f"{t.kind.value} · {t.title}")
    store.complete_todo(t.id)
    con.print("Marked done.")


@outbox_app.command("list")
def outbox_list(as_json: JsonOpt = False):
    """Emails waiting for your approval."""
    _set_json(as_json)
    store = _open_store_or_fail()
    queued = store.list_requests(status=RequestStatus.QUEUED_FOR_APPROVAL)
    if as_json:
        cj.emit(cj.outbox_doc(queued))
        return
    for r in queued:
        con.print(f"[{r.id[:8]}] {r.broker_id} · {r.kind.value} · created {r.created_at:%Y-%m-%d}")


@outbox_app.command("approve")
def outbox_approve(request_id: str):
    from .engine.outbox import approve_and_send
    store = _store()
    r = _pick_one(store.list_requests(status=RequestStatus.QUEUED_FOR_APPROVAL), request_id,
                  "queued email", lambda r: r.id, lambda r: f"{r.broker_id} · {r.kind.value}")
    approve_and_send(store, r.id)
    con.print("Sent.")


# --------------------------------------------------------------------------- checklists

checklist_app = typer.Typer(help="Identity-safety checklists: credit freezes, opt-out lists "
                            "and more. Tick them off as you go.", no_args_is_help=True)
app.add_typer(checklist_app, name="checklist")
ChecklistProfileOpt = Annotated[str | None, typer.Option(
    "--profile", "-p", help="Whose list (needed only when more than one person is set up)")]


def _checklists_or_fail():
    from . import checklist_state as cs
    cf = cs.load_checklists()
    if cf is None:
        _fail(cj.EXIT_ERROR, "the checklists file is missing or invalid")
    return cf


def _checklist_profile(store, profile: str | None) -> Profile:
    if profile:
        return _one_profile(store, profile)
    ps = store.list_profiles()
    if len(ps) == 1:
        return ps[0]
    if not ps:
        _fail(cj.EXIT_NOT_CONFIGURED, "nobody is set up yet; run `freemyid setup` first")
    _ui().print("More than one person is set up. Pick one with --profile:", markup=False)
    for p in ps:
        _ui().print(f"  {p.id[:12]}  {p.label}", markup=False)
    if _json_mode:
        cj.emit(cj.failure_doc(cj.EXIT_USAGE, "more than one profile; use --profile"))
    raise typer.Exit(cj.EXIT_USAGE)


def _checklist_context(profile: str | None, cid: str | None = None):
    cf = _checklists_or_fail()
    item = None
    if cid is not None:
        item = _pick_one(cf.checklists, cid, "checklist", lambda c: c.id, lambda c: c.title)
    store = _open_store_or_fail()
    return cf, item, store, _checklist_profile(store, profile)


@checklist_app.command("list")
def checklist_list(profile: ChecklistProfileOpt = None, as_json: JsonOpt = False):
    """Every checklist, and which ones are done."""
    from . import checklist_state as cs
    _set_json(as_json)
    cf, _item, store, p = _checklist_context(profile)
    tk = cs.ticks(store, p.id)
    first = cs.first_checklist(p, cf)
    if as_json:
        cj.emit(cs.list_doc(cf, tk, p.id, first))
        return
    if first:
        con.print(f"You live in California: start with {first} (one free request to every "
                  f"registered data broker). See it with: freemyid checklist show {first}\n",
                  markup=False)
    done = 0
    for c in cs.ordered(cf, first):
        t = tk.get(c.id)
        mark = "[x]" if t and t.done else "[ ]"
        done += bool(t and t.done)
        con.print(f"{mark} {c.id:<24} {c.title}  ({c.cost}; {c.time_needed})", markup=False)
    con.print(f"\n{p.label}: {done} of {len(cf.checklists)} done. "
              "See one with: freemyid checklist show ID", markup=False)


@checklist_app.command("show")
def checklist_show(checklist_id: Annotated[str, typer.Argument(help="Checklist id")],
                   profile: ChecklistProfileOpt = None, as_json: JsonOpt = False):
    """The steps for one checklist."""
    from . import checklist_state as cs
    _set_json(as_json)
    _cf, c, store, p = _checklist_context(profile, checklist_id)
    assert c is not None
    t = cs.ticks(store, p.id).get(c.id)
    if as_json:
        cj.emit(cs.show_doc(c, t, p.id))
        return
    status = f"done on {t.at.date().isoformat()}" if t and t.done else "not done yet"
    out = [c.title, "", f"Status: {status}", f"Why: {c.why}", f"Cost: {c.cost}", f"Time: {c.time_needed}", f"Website: {c.url}"]
    if c.need_on_hand:
        out += ["", "Have these ready:", *[f"  - {x}" for x in c.need_on_hand]]
    out += ["", "Steps:", *[f"  {i}. {s}" for i, s in enumerate(c.steps, 1)]]
    out += ["", f"How to undo: {c.how_to_undo}"]
    if c.status_note:
        out += ["", f"Note: {c.status_note}"]
    out += ["", (f"Checked {c.date_checked.isoformat()}. When finished: "
                 f"freemyid checklist done {c.id}")]
    for line in out:
        con.print(line, markup=False, highlight=False)


def _checklist_tick(checklist_id: str, profile: str | None, as_json: bool, done: bool) -> None:
    from . import checklist_state as cs
    _set_json(as_json)
    cf, c, store, p = _checklist_context(profile, checklist_id)
    assert c is not None
    if not cs.set_done(store, p.id, c.id, done, cf):
        _fail(cj.EXIT_ERROR, f"could not record checklist {c.id}")
    if as_json:
        cj.emit(cs.show_doc(c, cs.ticks(store, p.id).get(c.id), p.id))
        return
    con.print(f"{'Done' if done else 'Not done'}: {c.title}", markup=False)


@checklist_app.command("done")
def checklist_done(checklist_id: Annotated[str, typer.Argument(help="Checklist id")],
                   profile: ChecklistProfileOpt = None, as_json: JsonOpt = False):
    """Mark a checklist as done."""
    _checklist_tick(checklist_id, profile, as_json, True)


@checklist_app.command("undo")
def checklist_undo(checklist_id: Annotated[str, typer.Argument(help="Checklist id")],
                   profile: ChecklistProfileOpt = None, as_json: JsonOpt = False):
    """Mark a checklist as not done again."""
    _checklist_tick(checklist_id, profile, as_json, False)


# ------------------------------------------------------------------------ search engines

_SE_ACTIONS = ("open", "done", "undo")


def _open_url(url: str) -> bool:
    import webbrowser
    return webbrowser.open(url)


@app.command("search-engines")
def search_engines(
        action: Annotated[str | None, typer.Argument(
            help="open ID | done ID | undo ID (leave out to list the steps)")] = None,
        step_id: Annotated[str | None, typer.Argument(
            help="Step id, e.g. google_results_about_you (or just google / bing)")] = None,
        profile: ChecklistProfileOpt = None, as_json: JsonOpt = False):
    """Google and Bing: guided steps to ask them to stop showing pages about you.

    Free My ID never searches Google or Bing. `open` opens their official page in your
    browser; `done` records that you did the steps there; `undo` takes that back."""
    from .engine import search_engines as se
    _set_json(as_json)
    if action is not None and action not in _SE_ACTIONS:
        _fail(cj.EXIT_USAGE, f"unknown action {action!r}; use open, done or undo")
    if action is not None and not step_id:
        _fail(cj.EXIT_USAGE, f"`{action}` needs a step id; see: freemyid search-engines")
    if action is None and step_id is not None:
        _fail(cj.EXIT_USAGE, "give an action before the step id: open, done or undo")
    cf = _checklists_or_fail()
    store = _open_store_or_fail()
    p = _checklist_profile(store, profile)
    steps = se.guided_steps(store, p.id, cf)
    if action is not None:
        assert step_id is not None
        g = _pick_one(steps, step_id, "search-engine step", lambda g: g.checklist.id,
                      lambda g: g.checklist.title, alias=lambda g: g.step.engine)
        cid = g.checklist.id
        if action == "open":
            if not se.open_step(store, p.id, cid, opener=_open_url, cf=cf):
                _fail(cj.EXIT_ERROR, f"could not open the page for {cid}")
            _ui().print(f"Opened {g.step.engine}'s page in your browser. If nothing opened, "
                        f"copy this address: {g.checklist.url}", markup=False,
                        highlight=False, soft_wrap=True)
        elif not se.mark_done(store, p.id, cid, action == "done", cf=cf):
            _fail(cj.EXIT_ERROR, f"could not record {cid}")
        else:
            _ui().print(f"{'Done' if action == 'done' else 'Not done'}: {g.checklist.title}",
                        markup=False)
        steps = se.guided_steps(store, p.id, cf)
    if as_json:
        cj.emit(se.doc(steps, p.id))
        return
    if action is not None:
        return
    if not steps:
        con.print("No Google or Bing steps are available right now.", markup=False)
        return
    con.print(se.INTRO + "\n", markup=False, highlight=False)
    for g in steps:
        when = (f" (done {g.done_at.date().isoformat()})" if g.status == "done" and g.done_at
                else f" (opened {g.opened_at.date().isoformat()})"
                if g.status == "opened" and g.opened_at else "")
        mark = "[x]" if g.status == "done" else "[ ]"
        con.print(f"{mark} {g.checklist.id:<26} {g.step.engine}: {g.checklist.title}",
                  markup=False, highlight=False)
        con.print(f"    {g.step.why_now}", markup=False, highlight=False)
        con.print(f"    {se.STATUS_TEXT[g.status]}{when}", markup=False, highlight=False)
        con.print(f"    {g.checklist.url}", markup=False, highlight=False, soft_wrap=True)
        for i, s in enumerate(g.checklist.steps, 1):
            con.print(f"      {i}. {s}", markup=False, highlight=False)
    con.print(f"\n{p.label}: {se.pending(steps)} of {len(steps)} to do. "
              "Open one with: freemyid search-engines open ID, then: "
              "freemyid search-engines done ID", markup=False, highlight=False)


# --------------------------------------------------------------------------- secrets


@secrets_app.command("status")
def secrets_status(as_json: JsonOpt = False):
    """Which backend holds the encryption key (keyring, passphrase or systemd-creds)."""
    from . import crypto, secret_backends
    _set_json(as_json)
    try:
        be = secret_backends.select()
    except (ValueError, crypto.KeyUnavailable) as e:
        _fail(cj.EXIT_NOT_CONFIGURED, f"no usable secrets backend: {e}")
    if as_json:
        cj.emit(cj.secrets_doc(be.name, secret_backends.configured_name(), be.usable(),
                               secret_backends.KeyringBackend().usable()))
        return
    con.print(be.name)


@secrets_app.command("migrate")
def secrets_migrate(
        to: Annotated[str, typer.Option("--to", help="passphrase | keyring | systemd-creds")],
        remove_keychain_key: Annotated[bool, typer.Option(
            "--remove-keychain-key",
            help="Also delete the key from the system keychain. Only if this is the ONLY Free "
                 "My ID folder on this computer: other folders that use the keychain share "
                 "that key and would lose their data.")] = False):
    """Move the encryption key (and saved mailbox passwords) to another backend."""
    from . import crypto, secret_backends
    try:
        if remove_keychain_key:
            err.print("Warning: removing the keychain key. Any other Free My ID folder on this "
                      "computer that uses the system keychain will no longer open.",
                      markup=False, highlight=False, soft_wrap=True)
            r = secret_backends.migrate(to, remove_keychain_key=True)
        else:
            r = secret_backends.migrate(to)
    except (ValueError, crypto.KeyUnavailable) as e:
        err.print(f"freemyid: {e}", markup=False, highlight=False, soft_wrap=True)
        raise typer.Exit(cj.EXIT_USAGE) from None
    if r.changed:
        con.print(f"Now using {r.to_backend} (was {r.from_backend}); "
                  f"{r.secrets_moved} saved password(s) moved.")
    elif not r.notice:
        con.print("Nothing to change.")
    if r.notice:
        con.print(r.notice, markup=False, highlight=False, soft_wrap=True)


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
    con.print("Free My ID will submit real opt-out requests to data brokers using the "
              "information in each profile (only what each broker already shows).")
    if typer.confirm("Enable real submissions?"):
        cfg = cfgmod.load()
        cfgmod.save(cfg.model_copy(update={"real_submissions_enabled": True}))
        con.print("[green]Enabled.[/]")


@app.command()
def monitor(registry: Annotated[Path | None, typer.Option(
                "--registry", help="Registry file (default: the installed registry)")] = None,
            previous: Annotated[Path | None, typer.Option(
                "--previous", help="Last week's monitor/1 JSON, to compare with")] = None,
            broker: Annotated[list[str] | None, typer.Option(
                "--broker", help="Only this broker id (repeatable)")] = None,
            browser: Annotated[bool, typer.Option(
                "--browser", help="Also load forms built by JavaScript in a headless "
                                  "browser (opens the page only)")] = False,
            as_json: JsonOpt = False):
    """For maintainers: check each broker's opt-out page and form against the registry.
    The page must still load and its form selectors still match (BL-IN-06, docs/MONITOR.md).

    Reads only: never fills in, clicks or submits anything, and needs no profile. A
    "prove you are human" page is reported as blocked, never worked around."""
    from . import monitor as mon
    from .registry import RegistryError, load_registry
    _set_json(as_json)
    try:
        reg = load_registry(registry) if registry else load_registry()
    except (RegistryError, OSError) as e:
        _fail(cj.EXIT_ERROR, f"registry could not be read: {str(e)[:160]}")
    prev = None
    if previous is not None:
        prev, why = mon.load_previous(previous)
        if prev is None:
            err.print(f"freemyid: --previous is not a monitor/1 file; not compared ({why})",
                      markup=False, highlight=False)
    loader, close = (None, None)
    if browser:
        from .netpolicy import NetPolicy
        loader, close = mon.browser_page_loader(NetPolicy(reg), cfgmod.load())
    try:
        doc = mon.run_monitor(reg, previous=prev, broker_ids=broker or None,
                              page_loader=loader)
    finally:
        if close is not None:
            close()
    if as_json:
        cj.emit(doc)
        return
    c = doc["counts"]
    con.print(f"{len(doc['brokers'])} broker page(s) checked: " + ", ".join(
        f"{n} {k.replace('_', ' ')}" for k, n in c.items() if n), markup=False)
    for b in doc["brokers"]:
        if b["health"] == "ok" and not b["changed"]:
            continue
        mark = " (changed since last week)" if b["changed"] else ""
        demote = "; 2+ bad weeks: suggest moving it to Assisted" if b["demote_suggested"] else ""
        con.print(f"  {b['broker_id']}: {b['health']}{mark}. {b['detail']}{demote}",
                  markup=False, highlight=False, soft_wrap=True)
    for key, label in (("new_brokers", "new since last week"),
                       ("removed_brokers", "in last week's file, not checked now")):
        if doc[key]:
            con.print(f"  {label}: " + ", ".join(doc[key]), markup=False, highlight=False,
                      soft_wrap=True)



def _wipe_question(target: Path) -> str:
    """The `wipe` confirm question, in plain words (WO-605 review F5). Kept at the end of the
    file so command line numbers in the CLI reference page don't move."""
    from . import crypto
    if crypto.is_default_home(target):
        return ("Delete ALL your Free My ID information from this computer? This can't be "
                "undone. If someone also set up an extra Free My ID folder on this computer "
                "(most people haven't), it may stop opening too.")
    return (f"Delete ALL Free My ID information in this folder ({target})? This can't be "
            "undone. Your main Free My ID folder and any other folders are not affected.")


if __name__ == "__main__":
    app()
