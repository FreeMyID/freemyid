"""Local web wizard + dashboard. FastAPI bound to 127.0.0.1 only.

Security model:
  * random per-launch token in the URL, exchanged once for an HttpOnly SameSite=Strict cookie;
  * Host header allow-list (defeats DNS rebinding), Origin check and per-session CSRF token
    on every POST;
  * strict CSP, no external assets of any kind, no analytics.
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import os
import secrets as pysecrets
import socket
import sys
import threading
import webbrowser
from collections.abc import Callable
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles

from .. import paths
from ..models import (
    Actor,
    Event,
    RequestStatus,
    TodoKind,
)
from . import dashboard as dash
from . import draft as dr
from . import ui

log = logging.getLogger(__name__)
STATIC_DIR = Path(__file__).resolve().parent / "static"
COOKIE = "freemyid_session"
CSP = ("default-src 'none'; img-src 'self'; style-src 'self'; script-src 'self'; "
       "connect-src 'self'; form-action 'self'; base-uri 'none'; frame-ancestors 'none'")
MSGS = {
    "created": "All set. Free My ID is starting its first check now.",
    "updated": "Changes saved.", "done": "Great, thank you. Marked as done.",
    "resolved": "Thank you. Free My ID will carry on.",
    "couldnt": "No problem. Free My ID will try again later or suggest another way.",
    "opened": "Opened in your web browser. Come back here when you are finished.",
    "openfail": "Could not open your browser. Try again.",
    "sent": "Email sent.", "cancelled": "Email cancelled.",
    "sendfail": "Could not send that email. Check the email settings and try again.",
    "noengine": "Sending is not switched on in this copy of Free My ID yet.",
    "attached": "Authorization attached.", "sched_on": "Automatic checking is on.",
    "sched_off": "Automatic checking is off.", "sched_fail": "Could not change that setting.",
    "saved": "Saved.", "real_on": "Real requests are on.", "real_off": "Practice mode is on.",
    "fill_done": "That one is done. Thank you.",
    "fill_busy": "Another form is already being filled in. Please finish that one first.",
    "fill_none": ("The form was not sent, so nothing changed. Your to-do is still on the "
                  "list. You can try again or use \"Open the site myself\"."),
    "no_practice": "Please let a practice check finish first, then look at the results.",
}


def _csrf_for(token: str) -> str:
    return hmac.new(token.encode(), b"freemyid-csrf", hashlib.sha256).hexdigest()


def _load_registry():
    try:
        from ..registry import load_registry
        return load_registry()
    except Exception:  # noqa: BLE001  dashboard still works without broker names
        log.warning("registry unavailable; showing broker ids")
        return None


def _consent_problem(p) -> str:
    from ..cli import consent_ok
    ok, why = consent_ok(p)
    return "" if ok else why


def _background_disabled() -> bool:
    """Never touch the system (scheduler, first run) under pytest or when told not to."""
    return bool(os.environ.get("PYTEST_CURRENT_TEST") or os.environ.get("FREEMYID_NO_BACKGROUND"))


def _default_finish(app: FastAPI, registry_loader: Callable[[], Any], profile,
                    schedule_on: bool) -> None:
    """After the wizard saves: install the scheduled job if asked, start the first run."""
    if _background_disabled():
        return
    if schedule_on:
        try:
            from .. import scheduler
            scheduler.install()
        except Exception as e:  # noqa: BLE001  never block finishing on this
            log.warning("scheduler install failed: %s", type(e).__name__)
    pid = profile.id

    def job() -> None:
        from .. import config as cfgmod
        from ..storage import Store
        app.state.running = True
        try:
            from ..engine.runner import run as engine_run
            reg = registry_loader()
            if reg is None:
                return
            st = Store()
            prof = st.get_profile(pid)
            if prof is None:
                return
            # Practice (dry) run until the user turns on real requests in Settings.
            engine_run(st, reg, [prof], scan_only=False,
                       dry_run=not cfgmod.load().real_submissions_enabled, scheduled=False)
        except ImportError:
            log.info("engine not installed; skipping first run")
        except Exception as e:  # noqa: BLE001
            log.warning("first run failed: %s", type(e).__name__)
        finally:
            app.state.running = False
    threading.Thread(target=job, name="freemyid-first-run", daemon=True).start()


def _open_in_browser(url: str) -> bool:
    return bool(webbrowser.open(url))


def create_app(store, token: str, allowed_hosts: set[str],
               registry_loader: Callable[[], Any] = _load_registry, *,
               open_url: Callable[[str], bool] = _open_in_browser,
               on_finish: Callable[[Any, bool], None] | None = None) -> FastAPI:
    """`open_url` opens a page in the user's default browser (server side, so it works from a
    pywebview window too). `on_finish(profile, schedule_on)` runs after the wizard saves."""
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    app.state.draft = None
    app.state.running = False
    app.state.on_focus = None      # desktop launcher: bring the window to the front
    app.state.fill = {"running": False, "tid": None, "result": None}
    fill_lock = threading.Lock()
    app.state.on_quit = None       # browser fallback: lets the user stop the program
    csrf_token = _csrf_for(token)

    def names() -> dict[str, str]:
        reg = registry_loader()
        return {b.id: b.name for b in reg.brokers} if reg else {}

    def redirect(url: str, msg: str = "") -> RedirectResponse:
        if msg:
            url += ("&" if "?" in url else "?") + "msg=" + msg
        return RedirectResponse(url, status_code=303)

    def flash(request: Request) -> str:
        return MSGS.get(request.query_params.get("msg", ""), "")

    def get_draft(new: bool = False) -> dr.Draft:
        if new or app.state.draft is None:
            app.state.draft = dr.Draft()
        return app.state.draft

    @app.middleware("http")
    async def guard(request: Request, call_next):
        host = (request.headers.get("host") or "").lower()
        if host not in allowed_hosts:
            return Response("Forbidden", status_code=403)
        authed = hmac.compare_digest(request.cookies.get(COOKIE, ""), token)
        qt = request.query_params.get("t")
        if not authed and qt and hmac.compare_digest(qt, token) and request.method == "GET":
            r = RedirectResponse(request.url.path, status_code=303)
            r.set_cookie(COOKIE, token, httponly=True, samesite="strict", path="/")
            return _hardened(r)
        if not authed:
            return _hardened(html(ui.error_page(
                "Please open Free My ID from its icon",
                ["Please open Free My ID from its icon on your desktop."]), 403))
        if request.method == "POST":
            origin = request.headers.get("origin")
            if origin and urlsplit(origin).netloc.lower() not in allowed_hosts:
                return _hardened(html(ui.error_page(
                    "That didn't work",
                    ["Free My ID could not tell that this request came from its own window."]),
                    403))
            sent = request.headers.get("x-csrf")
            if sent is None:
                body = await request.body()

                async def replay(body=body):
                    return {"type": "http.request", "body": body, "more_body": False}
                request._receive = replay   # let the route re-read the body
                form = await request.form()
                sent = str(form.get("csrf", ""))
            if not hmac.compare_digest(sent, csrf_token):
                return _hardened(html(ui.error_page(
                    "That page timed out",
                    ["That page timed out. Go back and try again."]), 403))
        return _hardened(await call_next(request))

    def _hardened(resp: Response) -> Response:
        resp.headers["Content-Security-Policy"] = CSP
        resp.headers["X-Content-Type-Options"] = "nosniff"
        resp.headers["Referrer-Policy"] = "same-origin"
        resp.headers["Cache-Control"] = "no-store"
        resp.headers["X-Frame-Options"] = "DENY"
        return resp

    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    def html(s: str, status: int = 200) -> HTMLResponse:
        return HTMLResponse(s, status_code=status)

    # ---------------------------------------------------------------- dashboard
    @app.get("/")
    async def home(request: Request):
        from .. import config as cfgmod
        profiles = store.list_profiles()
        if not profiles:
            return redirect("/wizard/consent?new=1")
        queued = store.list_requests(status=RequestStatus.QUEUED_FOR_APPROVAL)
        nm = names()
        who = {p.id: p.label for p in profiles}
        people = [{"profile": p, "consent_problem": _consent_problem(p)} for p in profiles]
        todos = [(t, who.get(t.profile_id, ""), nm.get(t.broker_id or "", ""))
                 for t in store.list_todos()]
        return html(dash.home_page(
            statuses=store.list_statuses(), todos=todos, people=people,
            outbox_count=len(queued), csrf=csrf_token, flash=flash(request),
            practice=not cfgmod.load().real_submissions_enabled,
            running=bool(app.state.running), fill=True,
            filling=bool(app.state.fill["running"])))

    @app.get("/profile/{pid}")
    async def profile_view(pid: str, request: Request):
        p = store.get_profile(pid)
        if not p:
            return html(ui.layout("Not found", "<h1>Not found</h1>"), 404)
        ev: dict[str, list] = {}
        for e in store.list_evidence(pid):
            if e.broker_id != "_consent":
                ev.setdefault(e.broker_id, []).append(e)
        return html(dash.profile_page(p, store.list_statuses(pid), names(), store.list_todos(pid),
                                      ev, csrf_token, _consent_problem(p), flash(request),
                                      fill=not app.state.fill["running"]))

    @app.get("/evidence/{pid}/{eid}")
    async def evidence(pid: str, eid: str):
        for e in store.list_evidence(pid):
            if e.id == eid:
                try:
                    data = store.read_evidence(e)   # decrypted in memory only
                except Exception:  # noqa: BLE001
                    return Response("Could not decrypt this item.", status_code=500)
                if data[:8] == b"\x89PNG\r\n\x1a\n":
                    hdr: dict[str, str]
                    mt, hdr = "image/png", {}
                elif data[:3] == b"\xff\xd8\xff":
                    mt, hdr = "image/jpeg", {}
                else:
                    mt = "application/octet-stream"
                    hdr = {"Content-Disposition": f'attachment; filename="evidence-{e.id[:8]}"'}
                hdr["Content-Security-Policy"] = "sandbox; default-src 'none'"
                return Response(data, media_type=mt, headers=hdr)
        return Response("Not found", status_code=404)

    def _todo(tid: str):
        return next((t for t in store.list_todos() if t.id == tid), None)

    def _back(t) -> str:
        return "/"

    @app.post("/todo/{tid}/done")
    async def todo_done(tid: str):
        t = _todo(tid)
        if not t:
            return redirect("/")
        if t.kind in (TodoKind.ASSISTED_OPT_OUT, TodoKind.SEND_EMAIL_MANUALLY) and t.broker_id:
            try:   # the person did the opt-out themselves: broker moves to "submitted"
                from ..engine.handoff import mark_manual_submitted
                mark_manual_submitted(store, t.profile_id, t.broker_id, t.request_id)
            except Exception as e:  # noqa: BLE001  e.g. engine missing or odd state
                log.info("mark_manual_submitted skipped: %s", type(e).__name__)
        store.complete_todo(t.id)
        store.log(Event(profile_id=t.profile_id, broker_id=t.broker_id, actor=Actor.USER,
                        action="todo_done", detail={"todo_kind": t.kind.value}))
        return redirect(_back(t), "done")

    # "Fill it in for me" (D9): interactive only, one at a time, in a background thread.
    def _fill_ack_path():
        from .. import paths
        return paths.home() / ".fill-confirmed"

    def _needs_fill_confirm() -> bool:
        from .. import config as cfgmod
        return not cfgmod.load().real_submissions_enabled and not _fill_ack_path().exists()

    @app.get("/todo/{tid}/fill/confirm")
    async def todo_fill_confirm(tid: str):
        t = _todo(tid)
        if not t or t.kind != TodoKind.ASSISTED_OPT_OUT or not t.broker_id:
            return redirect("/")
        return html(dash.fill_confirm_page(t.id, csrf_token))

    @app.post("/todo/{tid}/fill")
    async def todo_fill(tid: str, request: Request):
        t = _todo(tid)
        if not t or t.kind != TodoKind.ASSISTED_OPT_OUT or not t.broker_id:
            return redirect("/")
        if _needs_fill_confirm():   # SEC-38: one-time plain-language confirmation
            form = await request.form()
            if form.get("confirm") != "yes":
                return redirect(f"/todo/{t.id}/fill/confirm")
            try:
                _fill_ack_path().write_text("1", encoding="utf-8")
            except OSError:
                pass
        with fill_lock:
            if app.state.fill["running"]:
                return redirect("/", "fill_busy")
            app.state.fill = {"running": True, "tid": t.id, "result": None}
        pid, bid = t.profile_id, t.broker_id

        def job() -> None:
            res = None
            try:
                from ..engine import fill_for_me as ffm
                from ..storage import Store
                res = ffm.fill_for_me_sync(Store(), pid, bid)
            except Exception as e:  # noqa: BLE001  never leave the page waiting forever
                log.warning("fill failed: %s", type(e).__name__)
            finally:
                app.state.fill = {"running": False, "tid": t.id, "result": res}
        threading.Thread(target=job, name="freemyid-fill-ui", daemon=True).start()
        return redirect("/fill")

    @app.get("/fill")
    async def fill_status():
        f = app.state.fill
        if f["tid"] is None:
            return html(dash.fill_page("none", "", csrf_token))
        if f["running"]:
            return html(dash.fill_page("waiting", f["tid"], csrf_token))
        res, tid = f["result"], f["tid"]
        app.state.fill = {"running": False, "tid": None, "result": None}
        if res is not None and getattr(res, "status", "") == "submitted":
            return redirect("/", "fill_done")
        if res is not None and getattr(res, "status", "") == "fallback" \
                and getattr(res, "submit_seen", False):
            return html(dash.fill_page("pressed", getattr(res, "todo_id", None) or tid,
                                       csrf_token))
        return redirect("/", "fill_none")

    @app.post("/todo/{tid}/couldnt")
    async def todo_couldnt(tid: str):
        t = _todo(tid)
        if t:
            store.complete_todo(t.id)
            store.log(Event(profile_id=t.profile_id, broker_id=t.broker_id, actor=Actor.USER,
                            action="todo_could_not", detail={"todo_kind": t.kind.value}))
        return redirect("/", "couldnt")

    @app.post("/todo/{tid}/open")
    async def todo_open(tid: str):
        t = _todo(tid)
        url = dash.open_url_of(t) if t else None
        if not url:
            return redirect("/")
        ok = False
        try:
            ok = open_url(url)
        except Exception as e:  # noqa: BLE001
            log.warning("open browser failed: %s", type(e).__name__)
        return redirect("/", "opened" if ok else "openfail")

    @app.post("/todo/{tid}/compose/{provider}")
    async def todo_compose(tid: str, provider: str):
        t = _todo(tid)
        if not t or t.kind != TodoKind.SEND_EMAIL_MANUALLY:
            return redirect("/")
        to, subject, letter = dash.email_parts(t)
        url = dash.compose_url(provider, to, subject, letter)
        if not url:
            return redirect("/")
        ok = False
        try:
            ok = open_url(url)
        except Exception as e:  # noqa: BLE001
            log.warning("open browser failed: %s", type(e).__name__)
        return redirect("/", "opened" if ok else "openfail")

    @app.post("/todo/{tid}/resolve")
    async def todo_resolve(tid: str):
        t = _todo(tid)
        if not t:
            return redirect("/")
        try:   # let the engine resume the paused flow if it exposes a hook
            from ..engine import handoff
            hook = getattr(handoff, "mark_resolved", None)
            if hook and t.resume_token:
                hook(store, t)
        except ImportError:
            pass
        store.complete_todo(t.id)
        store.log(Event(profile_id=t.profile_id, broker_id=t.broker_id, actor=Actor.USER,
                        action="todo_resolved", detail={"todo_kind": t.kind.value}))
        return redirect("/", "resolved")

    @app.get("/outbox")
    async def outbox(request: Request):
        who = {p.id: p.label for p in store.list_profiles()}
        nm = names()
        try:
            from ..engine.outbox import letter_for
        except ImportError:
            letter_for = None  # type: ignore[assignment]
        items = []
        for r in store.list_requests(status=RequestStatus.QUEUED_FOR_APPROVAL):
            try:
                letter = (letter_for(store, r) if letter_for  # type: ignore[truthy-function]
                          else ("", "", ""))
            except Exception:  # noqa: BLE001
                letter = ("", "", "(the letter could not be read)")
            items.append((r, who.get(r.profile_id, "?"), nm.get(r.broker_id, r.broker_id),
                          letter))
        releases: dict[str, list[str]] = {}
        try:
            from ..engine.outbox import released_by_approval
            profiles = {p.id: p for p in store.list_profiles()}
            for r, *_ in items:
                prof = profiles.get(r.profile_id)
                others = released_by_approval(store, prof, r) if prof else []
                if others:
                    releases[r.id] = [nm.get(o.broker_id, o.broker_id) for o in others]
        except ImportError:
            pass
        return html(dash.outbox_page(items, csrf_token, flash(request), releases))

    @app.post("/outbox/{rid}/approve")
    async def outbox_approve(rid: str):
        r = store.get_request(rid)
        if not r or r.status != RequestStatus.QUEUED_FOR_APPROVAL:
            return redirect("/outbox")
        try:
            from ..engine.outbox import approve_and_send
        except ImportError:
            return redirect("/outbox", "noengine")
        try:
            # SEC-48: approving can send a burst of emails (SEC-27 release); never block
            # the event loop with SMTP. The store is thread-safe (RLock).
            from starlette.concurrency import run_in_threadpool
            await run_in_threadpool(approve_and_send, store, rid)
        except Exception as e:  # noqa: BLE001
            log.warning("approve_and_send failed: %s", type(e).__name__)
            return redirect("/outbox", "sendfail")
        return redirect("/outbox", "sent")

    @app.post("/outbox/{rid}/cancel")
    async def outbox_cancel(rid: str):
        r = store.get_request(rid)
        if r and r.status == RequestStatus.QUEUED_FOR_APPROVAL:
            store.save_request(r.model_copy(update={"status": RequestStatus.CANCELLED}))
            store.log(Event(profile_id=r.profile_id, broker_id=r.broker_id, actor=Actor.USER,
                            action="email_cancelled"))
        return redirect("/outbox", "cancelled")

    @app.get("/settings")
    async def settings(request: Request):
        from .. import config as cfgmod
        from .. import scheduler
        try:
            sched = scheduler.status()
        except Exception:  # noqa: BLE001
            sched = "unknown"
        return html(dash.settings_page(
            people=store.list_profiles(), schedule_status=sched,
            practice=not cfgmod.load().real_submissions_enabled, csrf=csrf_token,
            flash=flash(request), can_quit=app.state.on_quit is not None))

    @app.post("/_focus")
    async def focus():
        cb = app.state.on_focus
        if cb:
            try:
                cb()
            except Exception as e:  # noqa: BLE001
                log.info("focus failed: %s", type(e).__name__)
        return Response("ok", media_type="text/plain")

    @app.post("/quit")
    async def quit_app():
        cb = app.state.on_quit
        if cb:
            threading.Timer(0.3, cb).start()
            return html(ui.layout("Closed", "<h1>Free My ID is closing.</h1><p>You can close this "
                                  "tab.</p>", nav=False))
        return redirect("/settings")

    def _practice_done() -> bool:
        return (any(st.last_scan_at for st in store.list_statuses())
                or any(r.dry_run for r in store.list_requests()))

    @app.get("/settings/submissions/confirm")
    async def submissions_confirm(request: Request):
        people = store.list_profiles()
        if not _practice_done():
            return redirect("/settings", "no_practice")
        return html(dash.confirm_real_page(people, csrf_token))

    @app.post("/settings/submissions/{mode}")
    async def submissions(mode: str, request: Request):
        from .. import config as cfgmod
        if mode == "on":
            form = await request.form()
            if form.get("confirm") != "yes":
                return redirect("/settings/submissions/confirm")
            if not _practice_done():
                return redirect("/settings", "no_practice")
        if mode in ("on", "off"):
            cfg = cfgmod.load()
            cfgmod.save(cfg.model_copy(update={"real_submissions_enabled": mode == "on"}))
            store.log(Event(actor=Actor.USER, action=f"real_submissions_{mode}"))
        return redirect("/settings", "real_on" if mode == "on" else "real_off")

    @app.post("/settings/{pid}/permissions")
    async def set_permissions(pid: str, request: Request):
        p = store.get_profile(pid)
        if not p:
            return redirect("/settings")
        d = dr.draft_from_profile(p)
        dr.apply_step(d, "permissions", await request.form())
        dr.save_draft(store, d)
        return redirect("/settings", "saved")

    @app.get("/settings/{pid}/mailbox")
    async def mailbox_get(pid: str):
        p = store.get_profile(pid)
        if not p:
            return redirect("/settings")
        d = dr.draft_from_profile(p)
        return html(dash.mailbox_settings_page(p, ui._mailbox_body(d), csrf_token, []))

    @app.post("/settings/{pid}/mailbox")
    async def mailbox_post(pid: str, request: Request):
        p = store.get_profile(pid)
        if not p:
            return redirect("/settings")
        d = dr.draft_from_profile(p)
        d.tls_pin = getattr(app.state, "approved_pin", None) or d.tls_pin
        errs = dr.apply_step(d, "mailbox", await request.form())
        if not errs:
            try:
                dr.save_draft(store, d)
            except dr.SaveError as e:
                errs = [str(e)]
        if errs:
            return html(dash.mailbox_settings_page(p, ui._mailbox_body(d), csrf_token, errs), 400)
        return redirect("/settings", "saved")

    @app.post("/schedule/{action}")
    async def schedule(action: str):
        from .. import scheduler
        if action not in ("install", "remove"):
            return redirect("/settings")
        try:
            getattr(scheduler, action)()
        except Exception as e:  # noqa: BLE001
            log.warning("scheduler %s failed: %s", action, type(e).__name__)
            return redirect("/settings", "sched_fail")
        return redirect("/settings", "sched_on" if action == "install" else "sched_off")

    @app.get("/profile/{pid}/report")
    async def report(pid: str):
        from .report import build_report
        reg = registry_loader()
        if not store.get_profile(pid) or reg is None:
            return Response("Report unavailable.", status_code=404)
        path = build_report(store, reg, pid, "html")
        return Response(path.read_bytes(), media_type="text/html; charset=utf-8",
                        headers={"Content-Disposition": f'attachment; filename="{path.name}"'})

    @app.post("/profile/{pid}/authorization")
    async def attach_auth(pid: str, request: Request):
        p = store.get_profile(pid)
        form = await request.form()
        up = form.get("authorization")
        if not p or not hasattr(up, "read"):
            return redirect("/")
        data = await up.read()  # type: ignore[union-attr]
        if not data or len(data) > dr.MAX_AUTH_BYTES:
            return redirect(f"/profile/{pid}")
        doc = dr.save_authorization(store, pid, getattr(up, "filename", "") or "", data)
        p = p.model_copy(update={"consent": p.consent.model_copy(
            update={"authorization_doc": doc})})
        store.save_profile(p)
        store.log(Event(profile_id=pid, actor=Actor.USER, action="authorization_attached"))
        return redirect(f"/profile/{pid}", "attached")

    @app.get("/profile/{pid}/edit")
    async def edit(pid: str):
        p = store.get_profile(pid)
        if not p:
            return redirect("/")
        app.state.draft = dr.draft_from_profile(p)
        return redirect("/wizard/name")

    # ---------------------------------------------------------------- wizard
    @app.get("/wizard/authorization-form")
    async def auth_form():
        d = get_draft()
        person = " ".join(x for x in (d.first, d.middle, d.last) if x)
        return html(ui.authorization_form(person, d.attested_by))

    @app.post("/wizard/test-connection")
    async def test_conn(request: Request):
        form = await request.form()
        d = dr.Draft(editing=True)
        d.password = app.state.draft.password if app.state.draft else ""
        d.tls_pin = (getattr(app.state, "approved_pin", None)
                     or (app.state.draft.tls_pin if app.state.draft else ""))
        errs = dr._apply_mailbox(d, form, require_trust=False)
        if errs and not d.mailbox:
            return JSONResponse({"ok": False, "status": "fail", "message": errs[0]})
        mb = dict(d.mailbox or {})
        if d.tls_pin:
            mb["tls_cert_sha256"] = d.tls_pin
        ok, msg, status = dr.check_mailbox(mb, d.password)
        if status in ("needs_trust", "cert_changed"):
            return JSONResponse(offer_trust(mb, status))
        return JSONResponse({"ok": ok, "status": status, "message": msg})

    def offer_trust(mb: dict, status: str) -> dict:
        """Read (without any password) the local mail app's certificate and ask the user."""
        from ..engine.mail_tls import TlsPinError, trust_on_first_use
        from ..models import MailboxConfig
        try:
            res = trust_on_first_use(MailboxConfig(
                **{k: v for k, v in mb.items() if k != "tls_cert_sha256"},
                keyring_service="freemyid-mailbox"))
        except TlsPinError as e:
            return {"ok": False, "status": "fail", "message": str(e)}
        except ValueError:
            return {"ok": False, "status": "fail",
                    "message": "Those mail settings are not complete yet."}
        app.state.pending_pin = res.fingerprint
        changed = status == "cert_changed"
        if changed:
            text = ("The security code of your mail app has changed since you last approved "
                    "it. This is normal if you just reinstalled or updated Proton Mail "
                    "Bridge. If you did not, say No.")
        else:
            text = ("Free My ID found your mail app on this computer. Please check that "
                    "the code below matches the one in Proton Mail Bridge.")
        return {"ok": False, "status": "trust", "changed": changed, "message": text,
                "display": res.display, "question": (
                    "Do you trust the new code?" if changed else "Do you trust this code?")}

    @app.post("/wizard/trust-certificate")
    async def trust_cert(request: Request):
        form = await request.form()
        pending = getattr(app.state, "pending_pin", None)
        if form.get("answer") != "yes" or not pending:
            app.state.pending_pin = None
            return JSONResponse({"ok": False, "message": (
                "Not trusted. Nothing was saved and no password was sent.")})
        app.state.approved_pin = pending
        if app.state.draft is not None:
            app.state.draft.tls_pin = pending
        app.state.pending_pin = None
        return JSONResponse({"ok": True, "message": "Saved. Testing again..."})

    @app.get("/wizard/import")
    async def import_form():
        from .flows import find_family_bundle
        found = find_family_bundle()
        pick = ('<p>A setup file came with this program. Just type its passphrase.</p>'
                if found else
                '<label for="bundle">Setup file (.freemyid-profile)</label>'
                '<input id="bundle" name="bundle" type="file" required>')
        body = ('<h1>Use a family setup file</h1><form class="card" method="post" '
                'enctype="multipart/form-data" action="/wizard/import">'
                f'{ui.csrf_field(csrf_token)}{pick}'
                '<label for="passphrase">Password for the setup file</label>'
                '<input id="passphrase" name="passphrase" type="password" required>'
                '<p class="hint">You will review everything and give your own permission '
                'before anything is saved.</p><div class="actions"><button type="submit" '
                'class="big">Continue</button></div></form>')
        return html(ui.layout("Import", body, nav=False))

    @app.post("/wizard/import")
    async def import_post(request: Request):
        from .flows import find_family_bundle, load_bundle
        form = await request.form()
        up = form.get("bundle")
        try:
            found = find_family_bundle()
            data = found.read_bytes() if found and not hasattr(up, "read") else await up.read()  # type: ignore[union-attr]
            app.state.draft = load_bundle(data, str(form.get("passphrase", "")))
        except Exception:  # noqa: BLE001
            return html(ui.layout("Import", ui.errors_html(
                ["That file or passphrase did not work."]) + '<a href="/wizard/import">Back</a>'),
                400)
        return redirect("/wizard/consent")

    @app.get("/wizard/{step}")
    async def wizard_get(step: str, request: Request):
        if step not in dr.STEPS:
            return redirect("/")
        d = get_draft(new=request.query_params.get("new") == "1" and step == "consent")
        if step not in ui.visible_steps(d):
            return redirect("/wizard/name")
        if step != "consent" and not d.editing and not d.consent_ack:
            return redirect("/wizard/consent")
        return html(ui.step_page(step, d, csrf_token, []))

    @app.post("/wizard/{step}")
    async def wizard_post(step: str, request: Request):
        if step not in dr.STEPS:
            return redirect("/")
        d = get_draft()
        form = await request.form()
        files = {}
        up = form.get("authorization")
        if hasattr(up, "read"):
            files["authorization"] = (getattr(up, "filename", "") or "", await up.read())  # type: ignore[union-attr]
        errs = dr.apply_step(d, step, form, files)
        if errs:
            return html(ui.step_page(step, d, csrf_token, errs), 400)
        if step != "finish":
            vs = ui.visible_steps(d)
            return redirect(f"/wizard/{vs[vs.index(step) + 1]}")
        try:
            prof = dr.save_draft(store, d)
        except dr.SaveError as e:
            return html(ui.step_page("finish", d, csrf_token, [str(e)]), 400)
        was_edit, sched_on = d.editing, d.weekly_recheck and d.schedule_consent
        app.state.draft = None
        if was_edit:
            return redirect("/", "updated")
        (on_finish or (lambda p, on: _default_finish(app, registry_loader, p, on)))(prof, sched_on)
        return redirect("/", "created")

    return app


def _bind(port: int) -> socket.socket:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    if sys.platform == "win32":
        # REUSEADDR on Windows would let another local process share the port.
        s.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
    else:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        s.bind(("127.0.0.1", port))
    except OSError:
        s.bind(("127.0.0.1", 0))   # configured port busy: pick a free one
    s.listen(16)
    return s


def serve(port: int, open_browser: bool = True) -> None:
    """Run the wizard/dashboard on 127.0.0.1 until interrupted."""
    import uvicorn

    from ..storage import Store

    sock = _bind(port)
    real_port = sock.getsockname()[1]
    token = pysecrets.token_urlsafe(32)
    allowed = {f"127.0.0.1:{real_port}", f"localhost:{real_port}"}
    app = create_app(Store(), token, allowed)
    url = f"http://127.0.0.1:{real_port}/?t={token}"
    print(f"Free My ID is running. If your browser does not open, visit:\n  {url}\n"
          "Press Ctrl+C to stop.")
    if open_browser:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    paths.home()
    server = uvicorn.Server(uvicorn.Config(app, log_level="warning", access_log=False))
    server.run(sockets=[sock])


class Running:
    """A server running on a background thread (used by the desktop launcher)."""

    def __init__(self, app: FastAPI, server: Any, thread: threading.Thread, port: int,
                 token: str) -> None:
        self.app, self.server, self.thread, self.port, self.token = (
            app, server, thread, port, token)

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.port}/?t={self.token}"

    def stop(self) -> None:
        self.server.should_exit = True
        self.thread.join(timeout=5)


def start_background(port: int = 0, store=None, registry_loader=_load_registry) -> Running:
    """Start the app on 127.0.0.1 (port 0 = any free port) without blocking."""
    import time

    import uvicorn

    from ..storage import Store

    sock = _bind(port)
    real_port = sock.getsockname()[1]
    token = pysecrets.token_urlsafe(32)
    allowed = {f"127.0.0.1:{real_port}", f"localhost:{real_port}"}
    paths.home()
    app = create_app(store or Store(), token, allowed, registry_loader)
    server = uvicorn.Server(uvicorn.Config(app, log_level="warning", access_log=False))
    t = threading.Thread(target=lambda: server.run(sockets=[sock]), name="freemyid-server",
                         daemon=True)
    t.start()
    for _ in range(100):
        if server.started:
            break
        time.sleep(0.05)
    return Running(app, server, t, real_port, token)
