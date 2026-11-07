"""Render the sample report screenshot from a fake profile and ONLY the public sample registry (SEC-41).
Usage: .venv/bin/python brand/src/capture_report_sample.py <scratch_dir> <out_png>
Throwaway FREEMYID_HOME; registry loaded explicitly from brokers/registry.sample.yaml."""
import os, sys
from pathlib import Path
scratch, out = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
os.environ["FREEMYID_HOME"] = str(scratch / "home")
os.environ["FREEMYID_NO_BACKGROUND"] = "1"
from datetime import timedelta
from freemyid.models import (Todo, TodoKind, Address, BrokerStatus, Consent, ConsentBasis, ListingState as L,
                             PersonName, Profile, utcnow)
from freemyid.registry import bundled_sample_registry_path, load_registry
from freemyid.storage import Store
from freemyid.wizard.report import build_report
from playwright.sync_api import sync_playwright

store = Store()
reg = load_registry(bundled_sample_registry_path())
prof = Profile(label="Pat Testperson", consent=Consent(basis=ConsentBasis.SELF, attested_by="Pat Testperson", text_version="1"),
               name=PersonName(first="Pat", last="Testperson"),
               addresses=[Address(city="Raleigh", state="NC", current=True)])
store.save_profile(prof)
ids = [x.id for x in reg.brokers if x.id != "ca_drop" and not getattr(x, "covered_by", None)][:14]
plan = [L.CONFIRMED]*5 + [L.REMOVED]*2 + [L.SUBMITTED]*2 + [L.AWAITING_VERIFICATION] + [L.NEEDS_HUMAN]*2 + [L.NOT_FOUND]*2
now = utcnow()
for i, (bid, st) in enumerate(zip(ids, plan)):
    store.save_status(BrokerStatus(profile_id=prof.id, broker_id=bid, state=st,
        updated_at=now - timedelta(days=i), last_scan_at=now - timedelta(days=i),
        last_submitted_at=None if st == L.NOT_FOUND else now - timedelta(days=i + 3),
        attempts=0 if st == L.NOT_FOUND else 1, next_check_at=now + timedelta(days=20),
        needs_human_reason="Needs you" if st == L.NEEDS_HUMAN else None))
nh = [bid for bid, st in zip(ids, plan) if st == L.NEEDS_HUMAN]
store.save_todo(Todo(profile_id=prof.id, broker_id=nh[0], kind=TodoKind.ASSISTED_OPT_OUT, title="Remove your listing",
    body="1. Open the page\n2. Find your listing\n3. Click Remove", links=["https://example.com/optout"]))
store.save_todo(Todo(profile_id=prof.id, broker_id=nh[1], kind=TodoKind.SEND_EMAIL_MANUALLY, title="Send this letter",
    body="Please delete my data.", copy_fields={"To": "privacy@example.com"}))
print(len(ids), "brokers:", ids)
rp = build_report(store, reg, prof.id, "html")
with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    ctx = b.new_context(viewport={"width": 900, "height": 900}, device_scale_factor=2)
    ctx.route("http*://**", lambda r: r.abort())
    pg = ctx.new_page(); pg.goto(rp.resolve().as_uri()); pg.wait_for_load_state()
    pg.set_viewport_size({"width": 900, "height": min(pg.evaluate("document.documentElement.scrollHeight"), 1600)})
    pg.screenshot(path=str(out), full_page=True)
    b.close()
