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
import secrets as pysecrets
import socket
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
    ConsentBasis,
    Event,
    ListingState,
    RequestStatus,
)
from . import dashboard as dash
from . import draft as dr
from . import ui

log = logging.getLogger(__name__)
STATIC_DIR = Path(__file__).resolve().parent / "static"
COOKIE = "vanish_session"
CSP = ("default-src 'none'; img-src 'self'; style-src 'self'; script-src 'self'; "
       "connect-src 'self'; form-action 'self'; base-uri 'none'; frame-ancestors 'none'")
MSGS = {
    "created": "Saved. Next: do a practice run with `vanish run --dry-run`.",
    "updated": "Changes saved.", "done": "Marked done.", "resolved": "Resolved.",
    "sent": "Email sent.", "cancelled": "Email cancelled.",
    "sendfail": "Could not send that email. Check the mailbox settings and try again.",
    "noengine": "The sending engine is not available yet in this install.",
    "attached": "Authorization attached.", "sched_on": "Background checks turned on.",
    "sched_off": "Background checks turned off.", "sched_fail": "Could not change the schedule.",
}


def _csrf_for(token: str) -> str:
    return hmac.new(token.encode(), b"vanish-csrf", hashlib.sha256).hexdigest()


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


def create_app(store, token: str, allowed_hosts: set[str],
               registry_loader: Callable[[], Any] = _load_registry) -> FastAPI:
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    app.state.draft = None
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
            return _hardened(Response("Open Vanish using the link printed when it started.",
                                      status_code=403, media_type="text/plain"))
        if request.method == "POST":
            origin = request.headers.get("origin")
            if origin and urlsplit(origin).netloc.lower() not in allowed_hosts:
                return _hardened(Response("Bad origin", status_code=403))
            sent = request.headers.get("x-csrf")
            if sent is None:
                body = await request.body()

                async def replay(body=body):
                    return {"type": "http.request", "body": body, "more_body": False}
                request._receive = replay   # let the route re-read the body
                form = await request.form()
                sent = str(form.get("csrf", ""))
            if not hmac.compare_digest(sent, csrf_token):
                return _hardened(Response("Bad or missing form token. Go back and try again.",
                                          status_code=403, media_type="text/plain"))
        return _hardened(await call_next(request))

    def _hardened(resp: Response) -> Response:
        resp.headers["Content-Security-Policy"] = CSP
        resp.headers["X-Content-Type-Options"] = "nosniff"
        resp.headers["Referrer-Policy"] = "no-referrer"
        resp.headers["Cache-Control"] = "no-store"
        resp.headers["X-Frame-Options"] = "DENY"
        return resp

    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    def html(s: str, status: int = 200) -> HTMLResponse:
        return HTMLResponse(s, status_code=status)

    # ---------------------------------------------------------------- dashboard
    @app.get("/")
    async def home(request: Request):
        profiles = store.list_profiles()
        if not profiles:
            return redirect("/wizard/consent?new=1")
        queued = store.list_requests(status=RequestStatus.QUEUED_FOR_APPROVAL)
        rows = []
        for p in profiles:
            counts: dict[ListingState, int] = {}
            for st in store.list_statuses(p.id):
                counts[st.state] = counts.get(st.state, 0) + 1
            rows.append({"profile": p, "counts": counts, "todos": len(store.list_todos(p.id)),
                             "outbox": sum(1 for r in queued if r.profile_id == p.id),
                             "consent_problem": _consent_problem(p)})
        return html(dash.home_page(rows, csrf_token, flash(request)))

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
                                      ev, csrf_token, _consent_problem(p), flash(request)))

    @app.get("/evidence/{pid}/{eid}")
    async def evidence(pid: str, eid: str):
        for e in store.list_evidence(pid):
            if e.id == eid:
                try:
                    data = store.read_evidence(e)   # decrypted in memory only
                except Exception:  # noqa: BLE001
                    return Response("Could not decrypt this item.", status_code=500)
                if data[:8] == b"\x89PNG\r\n\x1a\n":
                    mt, hdr = "image/png", {}
                elif data[:3] == b"\xff\xd8\xff":
                    mt, hdr = "image/jpeg", {}
                else:
                    mt = "application/octet-stream"
                    hdr = {"Content-Disposition": f'attachment; filename="evidence-{e.id[:8]}"'}
                hdr["Content-Security-Policy"] = "sandbox; default-src 'none'"
                return Response(data, media_type=mt, headers=hdr)
        return Response("Not found", status_code=404)

    @app.post("/todo/{tid}/done")
    async def todo_done(tid: str):
        t = store.complete_todo(tid)
        if t:
            store.log(Event(profile_id=t.profile_id, broker_id=t.broker_id, actor=Actor.USER,
                            action="todo_done", detail={"todo_kind": t.kind.value}))
        return redirect(f"/profile/{t.profile_id}" if t else "/", "done")

    @app.post("/todo/{tid}/resolve")
    async def todo_resolve(tid: str):
        match = [t for t in store.list_todos() if t.id == tid]
        if not match:
            return redirect("/")
        t = match[0]
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
        return redirect(f"/profile/{t.profile_id}", "resolved")

    @app.get("/outbox")
    async def outbox(request: Request):
        who = {p.id: p.label for p in store.list_profiles()}
        nm = names()
        items = [(r, who.get(r.profile_id, "?"), nm.get(r.broker_id, r.broker_id))
                 for r in store.list_requests(status=RequestStatus.QUEUED_FOR_APPROVAL)]
        return html(dash.outbox_page(items, csrf_token, flash(request)))

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
            approve_and_send(store, rid)
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
        from .. import scheduler
        return html(dash.settings_page(scheduler.status(), csrf_token, flash(request)))

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
        data = await up.read()
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
        return redirect("/wizard/names")

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
        errs = dr._apply_mailbox(d, form)
        if errs and not d.mailbox:
            return JSONResponse({"ok": False, "message": errs[0]})
        ok, msg = dr.test_mailbox_connection(d.mailbox, d.password)
        return JSONResponse({"ok": ok, "message": msg})

    @app.get("/wizard/import")
    async def import_form():
        body = ('<h1>Use a family setup file</h1><form class="card" method="post" '
                'enctype="multipart/form-data" action="/wizard/import">'
                f'{ui.csrf_field(csrf_token)}'
                '<label for="bundle">Setup file (.vanish-profile)</label>'
                '<input id="bundle" name="bundle" type="file" required>'
                '<label for="passphrase">Passphrase</label>'
                '<input id="passphrase" name="passphrase" type="password" required>'
                '<p class="hint">You will review everything and give your own permission '
                'before anything is saved.</p><div class="actions"><button type="submit">'
                'Continue</button></div></form>')
        return html(ui.layout("Import", body))

    @app.post("/wizard/import")
    async def import_post(request: Request):
        from .flows import load_bundle
        form = await request.form()
        up = form.get("bundle")
        try:
            data = await up.read()
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
        if step != "consent" and not d.editing and not d.consent_ack:
            return redirect("/wizard/consent")
        summary = ""
        if step == "review":
            warn = []
            if d.basis == ConsentBasis.AUTHORIZED_AGENT.value and not d.auth_bytes and not (
                    d.existing_consent and d.existing_consent.authorization_doc):
                warn.append("The signed authorization is not attached. Vanish will not run for "
                            "this person until you attach it from their page.")
            summary = ui.review_summary(d, warn)
        return html(ui.step_page(step, d, csrf_token, [], summary))

    @app.post("/wizard/{step}")
    async def wizard_post(step: str, request: Request):
        if step not in dr.STEPS:
            return redirect("/")
        d = get_draft()
        form = await request.form()
        files = {}
        up = form.get("authorization")
        if hasattr(up, "read"):
            files["authorization"] = (getattr(up, "filename", "") or "", await up.read())
        if step == "review":
            try:
                prof = dr.save_draft(store, d)
            except dr.SaveError as e:
                return html(ui.step_page("review", d, csrf_token, [str(e)],
                                         ui.review_summary(d, [])), 400)
            was_edit = d.editing
            app.state.draft = None
            return redirect(f"/profile/{prof.id}", "updated" if was_edit else "created")
        errs = dr.apply_step(d, step, form, files)
        if errs:
            return html(ui.step_page(step, d, csrf_token, errs), 400)
        nxt = dr.STEPS[dr.STEPS.index(step) + 1]
        return redirect(f"/wizard/{nxt}")

    return app


def _bind(port: int) -> socket.socket:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
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
    print(f"Vanish is running. If your browser does not open, visit:\n  {url}\n"
          "Press Ctrl+C to stop.")
    if open_browser:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    paths.home()
    server = uvicorn.Server(uvicorn.Config(app, log_level="warning", access_log=False))
    server.run(sockets=[sock])
