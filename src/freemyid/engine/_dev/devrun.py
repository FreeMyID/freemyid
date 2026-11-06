"""Run the whole loop end to end against the dev fixtures. No internet, no real email.

    .venv/bin/python -m freemyid.engine._dev.devrun                 # `freemyid run --dry-run`
    .venv/bin/python -m freemyid.engine._dev.devrun --no-mailbox    # D2 manual-send path
    .venv/bin/python -m freemyid.engine._dev.devrun --submit        # fixture "submissions"
    .venv/bin/python -m freemyid.engine._dev.devrun --scheduled     # quiet D4 run

It makes a throwaway FREEMYID_HOME (weak test key, fake person Jane Q Testperson), installs
the fixture registry as that home's registry cache, starts the fixture server and calls the
real CLI. `--submit` enables "real" submissions in the throwaway home only: every request is
answered by the local fixture server and mail goes to FakeMailer.
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
import tempfile
from pathlib import Path


def _setup_home(home: Path, *, mailbox: bool, submit: bool) -> None:
    os.environ["FREEMYID_HOME"] = str(home)
    os.environ.setdefault("FREEMYID_TEST_KEY", "devrun-weak-key-fake-data-only")
    os.environ["FREEMYID_ALLOW_TEST_KEY"] = "1"
    from freemyid import config as cfgmod
    from freemyid import paths
    from freemyid.consent import CURRENT_TEXT_VERSION
    from freemyid.models import Address, Consent, ConsentBasis, MailboxConfig, PersonName, Profile
    from freemyid.storage import Store

    from . import REGISTRY_PATH
    shutil.copyfile(REGISTRY_PATH, paths.registry_cache_path())
    cfg = cfgmod.Config(min_delay_s=0, max_delay_s=0, max_retries=1,
                        real_submissions_enabled=submit)
    cfgmod.save(cfg)
    store = Store()
    if not store.list_profiles():
        mb = MailboxConfig(address="removals.testperson@mail.example",
                           imap_host="imap.mail.example", smtp_host="smtp.mail.example",
                           username="removals.testperson@mail.example") if mailbox else None
        store.save_profile(Profile(
            label="Tester",
            consent=Consent(basis=ConsentBasis.SELF, attested_by="Jane Q Testperson",
                            text_version=CURRENT_TEXT_VERSION),
            name=PersonName(first="Jane", middle="Q", last="Testperson"),
            addresses=[Address(city="Springfield", state="IL", zip="62704", current=True)],
            age=46, relatives=["John Testperson"], mailbox=mb))
    store.close()


def _show(home: Path) -> None:
    from freemyid.storage import Store
    store = Store()
    print("\n--- statuses (broker: state / tier)")
    for st in sorted(store.list_statuses(), key=lambda s: s.broker_id):
        print(f"  {st.broker_id:12} {st.state.value:22} {st.tier.value if st.tier else '-'}")
    print("--- open to-dos")
    for t in store.list_todos():
        print(f"  {t.kind.value:20} {t.broker_id or '-':12} {t.title}  "
              f"[copy: {', '.join(t.copy_fields)}]")
    print("--- requests")
    for r in store.list_requests():
        print(f"  {r.broker_id:12} {r.kind.value:12} {r.status.value:20} dry_run={r.dry_run}")
    n = sum(len(store.list_evidence(p.id)) for p in store.list_profiles())
    print(f"--- evidence: {n} item(s)")
    store.close()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--home", type=Path, help="FREEMYID_HOME to use (default: new temp dir)")
    ap.add_argument("--no-mailbox", action="store_true")
    ap.add_argument("--submit", action="store_true", help="fixture submissions, not dry run")
    ap.add_argument("--scheduled", action="store_true")
    ap.add_argument("--keep", action="store_true", help="keep the temp home")
    a = ap.parse_args(argv)
    home = a.home or Path(tempfile.mkdtemp(prefix="freemyid-devrun-"))
    _setup_home(home, mailbox=not a.no_mailbox, submit=a.submit)

    from freemyid.cli import app

    from . import fixture_server
    args = ["run"] + ([] if a.submit else ["--dry-run"]) + (["--scheduled"] if a.scheduled
                                                           else [])
    code = 0
    with fixture_server() as base:
        print(f"fixture server: {base}  home: {home}")
        try:
            app(args, standalone_mode=False)
        except SystemExit as e:
            code = int(e.code or 0)
    _show(home)
    if not a.keep and not a.home:
        shutil.rmtree(home, ignore_errors=True)
    return code


if __name__ == "__main__":
    sys.exit(main())
