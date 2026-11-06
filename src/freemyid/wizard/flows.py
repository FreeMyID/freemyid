"""CLI setup/edit flows and family bundle export/import."""
from __future__ import annotations

import getpass
import json
from pathlib import Path

from ..crypto import export_with_passphrase, import_with_passphrase
from ..models import Profile
from . import draft as dr

BUNDLE_VERSION = 1


def _ask(text: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    return (input(f"{text}{suffix}: ").strip()) or default


def _yes(text: str, default: bool = False) -> bool:
    ans = input(f"{text} [{'Y/n' if default else 'y/N'}]: ").strip().lower()
    return default if not ans else ans.startswith("y")


def _secret(text: str) -> str:
    return getpass.getpass(f"{text}: ")


def _say(text: str = "") -> None:
    print(text)


class _Form(dict):
    """Adapter so CLI answers go through the same validators as the web form."""

    def getlist(self, key):
        v = self.get(key)
        return v if isinstance(v, list) else ([v] if v else [])


def _step(d: dr.Draft, step: str, answers: dict) -> bool:
    errs = dr.apply_step(d, step, _Form(answers))
    for e in errs:
        _say(f"  ! {e}")
    return not errs


def _loop(d: dr.Draft, step: str, ask) -> None:
    while True:
        if _step(d, step, ask()):
            return


def _lines_default(items: list[str]) -> str:
    return "; ".join(items)


def _split(text: str) -> str:
    return "\n".join(x.strip() for x in text.split(";") if x.strip())


def _consent(d: dr.Draft) -> None:
    _say("\n== Permission ==")
    for t in dr.CONSENT_TEXT:
        _say(f"- {t}")
    _say("\nWho is giving permission?")
    keys = list(dr.BASIS_LABELS)
    for i, k in enumerate(keys, 1):
        _say(f"  {i}. {dr.BASIS_LABELS[k]}")

    def ask():
        n = _ask("Choose 1-3", "1")
        basis = keys[int(n) - 1] if n.isdigit() and 1 <= int(n) <= 3 else ""
        if basis == "authorized_agent":
            _say("  The signed form can be attached later from the dashboard; Free My ID will "
                 "not run for this person until it is.")
        return {"basis": basis, "attested_by": _ask("Type your full name to sign", d.attested_by),
                    "ack": "1" if _yes("I have read this and I agree") else ""}
    _loop(d, "consent", ask)


def _names(d: dr.Draft) -> None:
    _say("\n== Names ==")
    _loop(d, "names", lambda: {
        "first": _ask("First name", d.first), "middle": _ask("Middle name (optional)", d.middle),
        "last": _ask("Last name", d.last), "suffix": _ask("Suffix (optional)", d.suffix),
        "label": _ask("What to call them on screen", d.label or d.first),
        "nicknames": _split(_ask("Nicknames, separated by ;", _lines_default(d.nicknames))),
        "previous_names": _split(_ask("Previous/maiden full names, separated by ;",
                                   _lines_default(d.previous_names)))})


def _addresses(d: dr.Draft) -> None:
    _say("\n== Addresses (city and state are enough) ==")

    def ask():
        a: dict = {}
        cur = "0"
        for i in range(4):
            old = d.addresses[i] if i < len(d.addresses) else {}
            city = _ask(f"Address {i + 1} city (blank to stop)", old.get("city", ""))
            if not city:
                break
            a[f"city{i}"] = city
            a[f"state{i}"] = _ask("  State (2 letters)", old.get("state", ""))
            a[f"street{i}"] = _ask("  Street (optional)", old.get("street", ""))
            a[f"zip{i}"] = _ask("  ZIP (optional)", old.get("zip", ""))
            if _yes("  Is this the current address", i == 0):
                cur = str(i)
        a["current"] = cur
        return a
    _loop(d, "addresses", ask)


def _details(d: dr.Draft) -> None:
    _say("\n== Other details (used only for matching, never sent to brokers) ==")
    _loop(d, "details", lambda: {
        "dob": _ask("Date of birth YYYY-MM-DD (or blank)", d.dob),
        "age": _ask("Age (if no date of birth)", d.age),
        "phones": _split(_ask("Phones, separated by ;", _lines_default(d.phones))),
        "emails": _split(_ask("Personal emails, separated by ;", _lines_default(d.emails))),
        "relatives": _split(_ask("Relatives (full names), separated by ;",
                              _lines_default(d.relatives)))})


def _permissions(d: dr.Draft) -> None:
    _say("\n== What Free My ID may do (all off unless you say yes; it never pays) ==")
    _step(d, "permissions", {
        "allow_id_upload": "1" if _yes("Allow uploading an ID when a broker requires it") else "",
        "allow_account_creation": "1" if _yes("Allow creating a broker account if required")
        else "",
        "allow_phone_disclosure": "1" if _yes("Allow giving a phone number if required") else ""})


def _mailbox(d: dr.Draft) -> None:
    _say("\n== Dedicated removal mailbox ==")
    if not _yes("Set it up now", True):
        d.skip_mailbox = True
        return
    d.skip_mailbox = False
    provs = list(dr.PRESETS)   # gmail, yahoo, icloud, proton_bridge, other (Outlook.com: skip)
    old = d.mailbox or {}

    def ask():
        prov = _ask(f"Provider ({'/'.join(provs)})", old.get("provider", "gmail"))
        a = {"provider": prov, "address": _ask("Mailbox address", old.get("address", "")),
                 "password": _secret("Password / app password (hidden; blank keeps saved)")}
        if prov == "other":
            a.update(imap_host=_ask("IMAP server"), smtp_host=_ask("SMTP server"),
                     imap_port=_ask("IMAP port", "993"), smtp_port=_ask("SMTP port", "465"),
                     imap_ssl="1" if _yes("IMAP uses SSL", True) else "",
                     smtp_starttls="1" if _yes("SMTP uses STARTTLS") else "")
        return a
    _loop(d, "mailbox", ask)
    if d.password and _yes("Test the connection now"):
        _say(dr.test_mailbox_connection(d.mailbox, d.password)[1])


def _email_sched(d: dr.Draft) -> None:
    _say("\n== Email approval ==")
    auto = _yes("Send routine removal emails automatically? (No = ask me each time)")
    _step(d, "email", {"email_mode": "auto" if auto else "approve_each"})
    _say("\n== Schedule ==")
    on = _yes("Re-check regularly", d.weekly_recheck)
    _step(d, "schedule", {"weekly_recheck": "1" if on else "", "weekday": d.weekday, "hour": d.hour})


def _finish(store, d: dr.Draft) -> Profile:
    _say("\nSome brokers need manual steps, listings can reappear, and 'removed' means "
         "removed from that broker only.")
    if not _yes("Save this person", True):
        raise SystemExit("Cancelled; nothing saved.")
    prof = dr.save_draft(store, d)
    _say("Saved. Next: `freemyid run --dry-run`, then `freemyid schedule install`.")
    return prof


def setup_cli(store, prefill: Path | None = None) -> Profile:
    """Interactive terminal setup, same steps as the web wizard."""
    d = dr.Draft()
    if prefill:
        d = load_bundle(Path(prefill).read_bytes(), _secret("Passphrase for the setup file"))
        _say("Loaded. Please review everything and give your own permission.")
    _consent(d)
    _names(d)
    _addresses(d)
    _details(d)
    _permissions(d)
    _mailbox(d)
    _email_sched(d)
    return _finish(store, d)


def edit_cli(store, profile_id: str) -> Profile:
    p = store.get_profile(profile_id)
    if p is None:
        raise ValueError("no such profile")
    d = dr.draft_from_profile(p)
    sections = [("Names", _names), ("Addresses", _addresses), ("Other details", _details),
                ("Permissions", _permissions), ("Mailbox", _mailbox),
                ("Email approval and schedule", _email_sched)]
    for title, fn in sections:
        if _yes(f"Change {title}"):
            fn(d)
    return _finish(store, d)


# --------------------------------------------------------------------------- bundles


def export_family_bundle(store, profile_id: str, dest: Path, passphrase: str) -> Path:
    """Passphrase-encrypted pre-filled profile. No consent, mailbox or password inside."""
    p = store.get_profile(profile_id)
    if p is None:
        raise ValueError("no such profile")
    data = p.model_dump(mode="json", exclude={"id", "consent", "mailbox", "created_at",
                                              "updated_at", "is_minor"})
    blob = export_with_passphrase(
        json.dumps({"freemyid_bundle": BUNDLE_VERSION, "profile": data}).encode(), passphrase)
    dest = Path(dest)
    if dest.suffix != ".freemyid-profile":
        dest = dest.with_name(dest.name + ".freemyid-profile")
    dest.write_bytes(blob)
    dest.chmod(0o600)
    return dest


def find_family_bundle() -> Path | None:
    """A .freemyid-profile shipped next to the installed app (the "family installer")."""
    import sys
    base = Path(sys.executable).parent if getattr(sys, "frozen", False) else None
    if base is None:
        return None
    return next(iter(sorted(base.glob("*.freemyid-profile"))), None)


def load_bundle(blob: bytes, passphrase: str) -> dr.Draft:
    """Decrypt a bundle into a fresh draft. Consent and mailbox are never imported."""
    obj = json.loads(import_with_passphrase(blob, passphrase))
    if obj.get("freemyid_bundle") != BUNDLE_VERSION:
        raise ValueError("unsupported bundle version")
    pr = obj.get("profile")
    if not isinstance(pr, dict):
        raise TypeError("bad bundle")
    # Never trust identifiers from a file: a fresh id is minted on save (path-traversal guard).
    for k in ("id", "consent", "mailbox", "created_at", "updated_at", "is_minor"):
        pr.pop(k, None)
    from ..models import Consent, ConsentBasis
    tmp = Profile.model_validate({
        **pr, "consent": Consent(basis=ConsentBasis.SELF, attested_by="x",
                                 text_version="import").model_dump(mode="json")})
    d = dr.draft_from_profile(tmp, keep_consent=False)
    d.editing = False
    d.imported = True
    d.attested_by = ""
    d.basis = ConsentBasis.SELF.value
    d.mailbox, d.skip_mailbox, d.mailbox_answered = {}, False, False
    return d
