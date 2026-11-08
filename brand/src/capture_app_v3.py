"""Capture app v3 screenshots (light + dark, 1280x800). Fake persona only (Jane Q Testperson).
Usage: .venv/bin/python brand/src/capture_app_v3.py <scratch_dir> <out_dir>
Uses a throwaway FREEMYID_HOME, an in-memory keyring, no scheduler and blocks non-local network."""
import os, sys
from pathlib import Path
scratch, out = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
home = scratch / "home"
os.environ["FREEMYID_HOME"] = str(home)
os.environ["FREEMYID_NO_BACKGROUND"] = "1"
import keyring
from keyring.backend import KeyringBackend
class Mem(KeyringBackend):
    priority = 1
    def __init__(s): super().__init__(); s.d = {}
    def get_password(s, a, b): return s.d.get((a, b))
    def set_password(s, a, b, c): s.d[(a, b)] = c
    def delete_password(s, a, b): s.d.pop((a, b), None)
keyring.set_keyring(Mem())
from datetime import timedelta
from freemyid.models import BrokerStatus, ListingState as L, Todo, TodoKind, utcnow
from freemyid.registry import load_registry
from freemyid.storage import Store
from freemyid.wizard.server import start_background
from playwright.sync_api import sync_playwright

store = Store()
run = start_background(store=store)
origin = f"http://127.0.0.1:{run.port}"
with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    def mk(scheme):
        c = b.new_context(viewport={"width": 1280, "height": 800}, device_scale_factor=1, color_scheme=scheme)
        c.route("**/*", lambda r: r.continue_() if r.request.url.startswith(origin) else r.abort())
        return c, c.new_page()
    ctx, pg = mk("light")
    def go():
        with pg.expect_navigation():
            pg.locator("form button[type=submit]").last.click()
    first = {}
    def grab(page, name, full=False):
        page.wait_for_load_state()
        page.screenshot(path=str(out / name), full_page=full)
    pg.goto(run.url)
    pg.locator("input[name=basis][value=self]").check()
    pg.fill("input[name=attested_by]", "Jane Q Testperson")
    box = pg.locator("input[name=ack]"); box.check(force=not box.is_visible())
    go()
    pg.fill("input[name=first]", "Jane"); pg.fill("input[name=last]", "Testperson")
    grab(pg, "01-wizard-name-light.png")
    go()
    pg.fill("input[name=street0]", "742 Evergreen Terrace") if pg.locator("input[name=street0]").count() else None
    pg.fill("input[name=city0]", "Springfield"); pg.fill("input[name=state0]", "IL")
    if pg.locator("input[name=zip0]").count(): pg.fill("input[name=zip0]", "62704")
    go()
    grab(pg, "02-wizard-address-light.png")
    pg.fill("input[name=birth_year]", "1950"); go()
    pg.locator("input[name=provider][value=skip]").check(); go()
    go()
    prof = store.list_profiles()[0]
    reg = load_registry()
    ids = [x.id for x in reg.brokers if x.id != "ca_drop" and not getattr(x, "covered_by", None)][:14]
    now = utcnow()
    plan = [L.CONFIRMED]*5 + [L.REMOVED]*2 + [L.SUBMITTED]*2 + [L.AWAITING_VERIFICATION] + [L.NEEDS_HUMAN]*2 + [L.NOT_FOUND]*2
    for i, (bid, st) in enumerate(zip(ids, plan)):
        store.save_status(BrokerStatus(profile_id=prof.id, broker_id=bid, state=st,
            updated_at=now - timedelta(days=i), last_scan_at=now - timedelta(days=i),
            last_submitted_at=None if st == L.NOT_FOUND else now - timedelta(days=i + 3),
            attempts=0 if st == L.NOT_FOUND else 1,
            next_check_at=now + timedelta(days=20), needs_human_reason="Needs you" if st == L.NEEDS_HUMAN else None))
    nh = [bid for bid, st in zip(ids, plan) if st == L.NEEDS_HUMAN]
    store.save_todo(Todo(profile_id=prof.id, broker_id=nh[0], kind=TodoKind.ASSISTED_OPT_OUT,
        title="Remove your listing", body="1. Open the page\n2. Find your listing\n3. Click Remove",
        links=["https://example.com/optout"], copy_fields={"Name": "Jane Testperson", "City": "Springfield, IL"}))
    store.save_todo(Todo(profile_id=prof.id, broker_id=nh[1], kind=TodoKind.SEND_EMAIL_MANUALLY,
        title="Send this letter", body="Please delete my data. Thank you.",
        copy_fields={"To": "privacy@example.com", "Subject": "Deletion request"}))
    pid = prof.id
    ctx.close()
    pages = [("today", "/", False), ("broker-detail", f"/profile/{pid}/site/{ids[0]}", False),
             ("protect", "/protect", False), ("summary", f"/profile/{pid}/summary", True)]
    for scheme in ("light", "dark"):
        c, q = mk(scheme)
        q.goto(run.url)
        for i, (n, path, full) in enumerate(pages, 3):
            q.goto(origin + path); grab(q, f"{i:02d}-{n}-{scheme}.png", full)
        c.close()
    b.close()
run.stop()
