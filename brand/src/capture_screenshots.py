"""Capture website screenshots of the real Free My ID app. Fake persona only (Jane Q Testperson).
Usage: .venv/bin/python brand/src/capture_screenshots.py <scratch_dir> <out_dir>
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
W = 1000
with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    ctx = b.new_context(viewport={"width": W, "height": 900}, device_scale_factor=2)
    ctx.route("**/*", lambda r: r.continue_() if r.request.url.startswith(origin) else r.abort())
    pg = ctx.new_page()
    def shot(name, sel=None):
        pg.wait_for_load_state()
        h = pg.evaluate("document.documentElement.scrollHeight")
        pg.set_viewport_size({"width": W, "height": min(h, 1400)})
        pg.screenshot(path=str(out / f"{name}.png"), full_page=True)
    def go():
        with pg.expect_navigation():
            pg.locator("form button[type=submit]").last.click()
    pg.goto(run.url)
    pg.locator("input[name=basis][value=self]").check()
    pg.fill("input[name=attested_by]", "Jane Q Testperson")
    box = pg.locator("input[name=ack]"); box.check(force=not box.is_visible())
    go()
    pg.fill("input[name=first]", "Jane"); pg.fill("input[name=last]", "Testperson")
    shot("wizard-name")
    go()
    pg.fill("input[name=street0]", "742 Evergreen Terrace") if pg.locator("input[name=street0]").count() else None
    pg.fill("input[name=city0]", "Springfield"); pg.fill("input[name=state0]", "IL")
    if pg.locator("input[name=zip0]").count(): pg.fill("input[name=zip0]", "62704")
    shot("wizard-address")
    go()
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
    pg.goto(origin + "/")
    shot("dashboard")
    from freemyid.wizard.report import build_report
    rp = build_report(store, reg, prof.id, "html")
    ctx2 = b.new_context(viewport={'width': 900, 'height': 900}, device_scale_factor=2)
    ctx2.route('http*://**', lambda r: r.abort())
    pg2 = ctx2.new_page(); pg2.goto(rp.resolve().as_uri()); pg2.wait_for_load_state()
    pg2.set_viewport_size({"width": 900, "height": min(pg2.evaluate("document.documentElement.scrollHeight"), 1600)})
    pg2.screenshot(path=str(out / "report.png"), full_page=True)
    b.close()
run.stop()
