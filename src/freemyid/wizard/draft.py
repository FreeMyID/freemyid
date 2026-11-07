"""Wizard draft (in-memory, one person at a time) shared by the web wizard and CLI flows.

The draft holds PII and the mailbox password only in process memory until `save_draft`.
"""
from __future__ import annotations

import imaplib
import logging
import re
import smtplib
import ssl
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Protocol

from ..consent import CURRENT_TEXT_VERSION
from ..engine.mail_tls import TlsPinError, check_peer, client_context, is_loopback
from ..models import (
    Actor,
    Address,
    Consent,
    ConsentBasis,
    EmailMode,
    Event,
    Evidence,
    EvidenceKind,
    MailboxConfig,
    Permissions,
    PersonName,
    Profile,
    ScheduleConfig,
    new_id,
    utcnow,
)

log = logging.getLogger(__name__)

CONSENT_VERSION = CURRENT_TEXT_VERSION   # single source of truth (consent.py)
CONSENT_TEXT = [
    ("Free My ID will look for the information of the person named in this setup on "
    "people-search sites (websites that publish names, addresses and phone numbers) and "
    "ask those sites to delete it."),
    ("Everything you type here stays on this computer, encrypted. Nothing is sent to us "
    "or to any server we run. There is no account, no tracking and no cloud."),
    ("When Free My ID contacts a site it sends only what that site already shows about the "
    "person, plus the email address for replies if you set one up. It never pays anyone."),
    ("Honest limits: some sites need a step from a person, details can come back after a "
    "site has deleted them, and a site saying it deleted your details is true for that one "
    "site only, not for the whole internet. Free My ID does not change what Facebook, "
    "Google or any other service does with your account."),
    "You can pause, edit or delete everything at any time.",
]
BASIS_LABELS = {
    ConsentBasis.SELF.value: "I am this person and I am allowing Free My ID to act for me.",
    ConsentBasis.GUARDIAN_OF_MINOR.value:
        "I am the parent or legal guardian of this person, who is under 18.",
    ConsentBasis.AUTHORIZED_AGENT.value:
        "I am helping an adult who gave me signed written permission (an authorized agent).",
}

STEPS = ["consent", "name", "address", "about", "mailbox", "finish"]
STEP_TITLES = {
    "consent": "Welcome. Who is this for?", "name": "What is the person's name?",
    "address": "Where do they live?", "about": "A few details to recognize them",
    "mailbox": "A separate email address for replies", "finish": "Run automatically?",
}
NO_CONSENT_NEEDED = ("consent",)

PRESETS: dict[str, dict[str, Any]] = {
    "gmail": {"imap_host": "imap.gmail.com", "imap_port": 993, "imap_ssl": True,
                  "smtp_host": "smtp.gmail.com", "smtp_port": 465, "smtp_starttls": False},
    "proton_bridge": {"imap_host": "127.0.0.1", "imap_port": 1143, "imap_ssl": False,
                          "imap_starttls": True, "smtp_host": "127.0.0.1", "smtp_port": 1025, "smtp_starttls": True},
    "yahoo": {"imap_host": "imap.mail.yahoo.com", "imap_port": 993, "imap_ssl": True,
                  "smtp_host": "smtp.mail.yahoo.com", "smtp_port": 465, "smtp_starttls": False},
    "icloud": {"imap_host": "imap.mail.me.com", "imap_port": 993, "imap_ssl": True,
                   "smtp_host": "smtp.mail.me.com", "smtp_port": 587, "smtp_starttls": True},
    "other": {"imap_host": "", "imap_port": 993, "imap_ssl": True,
                  "smtp_host": "", "smtp_port": 465, "smtp_starttls": False},
}

OUTLOOK_MSG = ("Outlook.com and Hotmail no longer allow programs like Free My ID to sign in. "
               "Please choose \"Skip, I'll do these by hand\" (Free My ID will prepare each "
               "message and open your email for you), or pick a different email service.")
# MailboxConfig.provider only accepts these; yahoo/icloud are stored as "other" (same servers).
STORED_PROVIDERS = ("gmail", "outlook", "proton_bridge", "other")
MAX_AUTH_BYTES = 10 * 1024 * 1024
_HOST_RE = re.compile(r"^[A-Za-z0-9]([A-Za-z0-9.\-]{0,251}[A-Za-z0-9])?$")


class FormLike(Protocol):
    def get(self, key: str, /, *args: Any) -> Any: ...
    def getlist(self, key: str, /) -> list[Any]: ...


@dataclass
class Draft:
    id: str = field(default_factory=new_id)
    editing: bool = False
    imported: bool = False
    saved_password: bool = False   # a mailbox password really exists in the secret store
    tls_pin: str = ""      # approved certificate fingerprint for a local mail app (Bridge)
    # consent
    basis: str = ConsentBasis.SELF.value
    attested_by: str = ""
    consent_ack: bool = False
    consent_at: datetime | None = None
    auth_bytes: bytes | None = None
    auth_filename: str = ""
    existing_consent: Consent | None = None
    # names
    label: str = ""
    first: str = ""
    middle: str = ""
    last: str = ""
    suffix: str = ""
    nicknames: list[str] = field(default_factory=list)
    previous_names: list[str] = field(default_factory=list)
    # addresses
    addresses: list[dict[str, Any]] = field(default_factory=list)
    # details
    dob: str = ""
    age: str = ""
    phones: list[str] = field(default_factory=list)
    emails: list[str] = field(default_factory=list)
    relatives: list[str] = field(default_factory=list)
    # permissions
    allow_id_upload: bool = False
    allow_account_creation: bool = False
    allow_phone_disclosure: bool = False
    # mailbox
    skip_mailbox: bool = False
    mailbox_answered: bool = False   # the mailbox screen has been completed
    provider: str = "gmail"
    schedule_consent: bool = False
    mailbox: dict[str, Any] = field(default_factory=dict)
    password: str = ""
    # email
    email_mode: str = EmailMode.APPROVE_EACH.value
    # schedule
    weekly_recheck: bool = True
    weekday: int = 6
    hour: int = 10


class SaveError(RuntimeError):
    pass


# --------------------------------------------------------------------------- helpers


def _lines(text: str | None) -> list[str]:
    return [ln.strip() for ln in (text or "").replace(",", "\n").splitlines() if ln.strip()]


def _name_lines(text: str | None) -> list[str]:
    return [ln.strip() for ln in (text or "").splitlines() if ln.strip()]


def parse_person_name(text: str) -> PersonName:
    parts = text.split()
    if len(parts) < 2:
        raise ValueError(f"Please give a first and last name for \"{text}\".")
    return PersonName(first=parts[0], last=parts[-1],
                      middle=" ".join(parts[1:-1]) or None)


def age_of(d: Draft, today: date | None = None) -> int | None:
    today = today or date.today()
    if d.dob:
        b = date.fromisoformat(d.dob)
        return today.year - b.year - ((today.month, today.day) < (b.month, b.day))
    if d.age.strip():
        return int(d.age)
    return None


def is_minor(d: Draft) -> bool:
    try:
        a = age_of(d)
    except ValueError:
        return False
    return a is not None and a < 18


# --------------------------------------------------------------------------- step parsing


def apply_step(d: Draft, step: str, f: FormLike, files: dict[str, tuple[str, bytes]] | None = None
               ) -> list[str]:
    """Apply one wizard step's form to the draft. Returns a list of plain-language errors."""
    files = files or {}
    errs: list[str] = []
    if step in ("consent", "sign"):
        if step == "consent":
            basis = f.get("basis", "")
            if basis not in BASIS_LABELS:
                errs.append("Please choose who is giving permission.")
            else:
                d.basis = basis
        d.attested_by = (f.get("attested_by") or "").strip()
        if not d.attested_by:
            errs.append("Please type your full name to confirm.")
        if not f.get("ack"):
            errs.append("Please tick the box to confirm you have read and agree.")
        if "authorization" in files and files["authorization"][1]:
            name, data = files["authorization"]
            if len(data) > MAX_AUTH_BYTES:
                errs.append("That file is too large (10 MB maximum).")
            else:
                d.auth_filename, d.auth_bytes = name[:100], data
        if not errs:
            d.consent_ack = True
            d.consent_at = utcnow()
    elif step in ("name", "names", "othernames"):
        def got(k: str) -> str | None:
            v = f.get(k)
            return None if v is None else str(v)
        for k in ("first", "middle", "last", "suffix"):
            if (v := got(k)) is not None:
                setattr(d, k, v.strip())
        if got("nicknames") is not None:
            d.nicknames = _lines(got("nicknames"))
        if got("previous_names") is not None:
            d.previous_names = _name_lines(got("previous_names"))
        if got("label") is not None:
            d.label = str(got("label")).strip() or d.first
        elif step in ("name", "names") and not d.label:
            d.label = d.first
        if step in ("name", "names") and (not d.first or not d.last):
            errs.append("First and last name are required.")
        for n in d.previous_names:
            try:
                parse_person_name(n)
            except ValueError as e:
                errs.append(str(e))
    elif step in ("address", "addresses", "moreaddr"):
        rows: list[dict[str, Any] | None] = (list(d.addresses) + [None] * 4)[:4]
        cur = f.get("current")
        for i in range(4):
            if f.get(f"city{i}") is None and f.get(f"state{i}") is None:
                continue
            city = (f.get(f"city{i}") or "").strip()
            st = (f.get(f"state{i}") or "").strip().upper()
            if not city and not st:
                rows[i] = None
                continue
            if not city or not re.fullmatch(r"[A-Z]{2}", st):
                errs.append(f"Please give a city and a 2-letter state (like IL) for address {i + 1}.")
                continue
            old = rows[i] or {}
            rows[i] = {"street": (f.get(f"street{i}") or old.get("street") or "").strip(),
                       "city": city, "state": st,
                       "zip": (f.get(f"zip{i}") or old.get("zip") or "").strip(),
                       "current": bool(old.get("current")) if cur is None else str(i) == cur}
        kept = [r for r in rows if r]
        if step in ("address", "addresses") and not kept and not errs:
            errs.append("Please enter at least one city and state.")
        if kept and not any(r["current"] for r in kept):
            kept[0]["current"] = True
        if not errs:
            d.addresses = kept
    elif step in ("about", "details", "birth", "phones", "emails", "relatives"):
        if f.get("birth_year") is not None:
            _apply_birth_year(d, str(f.get("birth_year")).strip(), errs)
        # A posted "dob" is deliberately ignored (SEC-42): only a year is collected.
        if f.get("age") is not None and f.get("birth_year") is None:
            d.age = (f.get("age") or "").strip()
        if f.get("phones") is not None:
            d.phones = _lines(f.get("phones"))
        if f.get("emails") is not None:
            d.emails = _lines(f.get("emails"))
        if f.get("relatives") is not None:
            d.relatives = _name_lines(f.get("relatives"))
        if d.dob:
            try:
                if date.fromisoformat(d.dob) > date.today():
                    errs.append("Date of birth is in the future.")
            except ValueError:
                errs.append("Date of birth should look like 1960-04-23.")
        if d.age and (not d.age.isdigit() or not 0 <= int(d.age) <= 130):
            errs.append("Age should be a number.")
        if not errs and is_minor(d) and d.basis != ConsentBasis.GUARDIAN_OF_MINOR.value:
            errs.append("This person is under 18, so a parent or guardian must give "
                        "permission. Go back to the first screen and choose the parent or "
                        "guardian option.")
    elif step == "permissions":
        d.allow_id_upload = bool(f.get("allow_id_upload"))
        d.allow_account_creation = bool(f.get("allow_account_creation"))
        d.allow_phone_disclosure = bool(f.get("allow_phone_disclosure"))
    elif step == "mailbox":
        prov = f.get("provider") or ("skip" if f.get("skip_mailbox") else "")
        if prov == "skip":
            d.skip_mailbox, d.mailbox_answered = True, True
        elif prov == "outlook":
            errs.append(OUTLOOK_MSG)
        elif prov not in PRESETS:
            errs.append("Please choose one of the options, or Skip.")
        else:
            d.skip_mailbox, d.provider = False, prov
            errs += _apply_mailbox(d, f)
            d.mailbox_answered = not errs
    elif step == "mailbox_login":
        d.skip_mailbox = False
        errs += _apply_mailbox(d, f)
    elif step == "email":
        mode = f.get("email_mode", EmailMode.APPROVE_EACH.value)
        if mode not in (EmailMode.APPROVE_EACH.value, EmailMode.AUTO.value):
            errs.append("Please choose an email option.")
        else:
            d.email_mode = mode
    elif step in ("schedule", "finish"):
        d.weekly_recheck = bool(f.get("weekly_recheck"))
        d.schedule_consent = d.weekly_recheck   # ticking the box IS the consent
    return errs


def _apply_birth_year(d: Draft, text: str, errs: list[str]) -> None:
    if not text:
        return
    this_year = date.today().year
    if not (text.isdigit() and len(text) == 4 and 1900 <= int(text) <= this_year):
        errs.append("Birth year should be four digits, like 1952.")
        return
    y = int(text)
    if d.dob and d.dob[:4] == text:
        return      # same year as the stored date of birth: keep the exact date
    d.dob, d.age = "", str(this_year - y)


def birth_year_of(d: Draft) -> str:
    if d.dob:
        return d.dob[:4]
    if d.age.isdigit():
        return str(date.today().year - int(d.age))
    return ""


UNENCRYPTED_MSG = ("Your password would be sent unprotected. Turn on SSL or STARTTLS "
                   "for incoming mail. If you are not sure, leave SSL ticked.")


def _apply_mailbox(d: Draft, f: FormLike, require_trust: bool = True) -> list[str]:
    errs: list[str] = []
    provider = f.get("provider") or d.provider or "other"
    if provider == "outlook":
        return [OUTLOOK_MSG]
    if provider not in PRESETS:
        provider = "other"
    mb: dict[str, Any] = dict(PRESETS[provider])
    mb["provider"] = provider if provider in STORED_PROVIDERS else "other"
    mb["address"] = (f.get("address") or "").strip()
    mb["username"] = (f.get("username") or "").strip() or mb["address"]
    if provider == "other" or f.get("custom_hosts"):
        try:
            mb.update(imap_host=(f.get("imap_host") or "").strip(),
                      smtp_host=(f.get("smtp_host") or "").strip(),
                      imap_port=int(f.get("imap_port") or 993),
                      smtp_port=int(f.get("smtp_port") or 465),
                      imap_ssl=bool(f.get("imap_ssl")),
                      imap_starttls=bool(f.get("imap_starttls")),
                      smtp_starttls=bool(f.get("smtp_starttls")))
        except ValueError:
            errs.append("Ports must be numbers.")
    if not (mb.get("imap_ssl") or mb.get("imap_starttls")):
        errs.append(UNENCRYPTED_MSG)
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", mb["address"]):
        errs.append("Please enter the removal mailbox's email address.")
    for k in ("imap_host", "smtp_host"):
        if not _HOST_RE.match(mb.get(k) or ""):
            errs.append("Please enter valid mail server names.")
            break
    pw = f.get("password") or ""
    if pw:
        d.password = pw
    elif d.editing and d.mailbox and not d.password and (
            mb["address"] != d.mailbox.get("address") or mb["imap_host"] != d.mailbox.get(
                "imap_host")):
        errs.append("You changed the email service, so please enter its app password.")
    elif not d.password and not (d.editing and d.mailbox):
        errs.append("Please enter the app password. (It is not your normal email password.)")
    if not errs:
        if is_loopback(mb["imap_host"]) or is_loopback(mb["smtp_host"]):
            if d.tls_pin:
                mb["tls_cert_sha256"] = d.tls_pin
            elif require_trust:
                errs.append("Please press \"Test that it works\" and approve the "
                            "security code first.")
        else:
            d.tls_pin = ""
        if not errs:
            d.mailbox = mb
    return errs


# --------------------------------------------------------------------------- connection test


def test_mailbox_connection(mb: dict[str, Any], password: str, timeout: float = 10.0
                            ) -> tuple[bool, str]:
    """Log in to IMAP and SMTP on exactly the hosts given. Contacts nothing else.

    Returns (ok, plain-language message). The password never appears in the message.
    """
    ok, msg, _status = check_mailbox(mb, password, timeout)
    return ok, msg


def check_mailbox(mb: dict[str, Any], password: str, timeout: float = 10.0
                  ) -> tuple[bool, str, str]:
    """Like `test_mailbox_connection` plus a status: "ok", "fail", "needs_trust" (local mail
    app with no approved certificate yet) or "cert_changed" (certificate differs from the
    approved one). The password is only sent after the certificate check passes: a local app
    without an approved pin is never contacted with credentials."""
    for k in ("imap_host", "smtp_host"):
        if not _HOST_RE.match(str(mb.get(k) or "")):
            return False, "Please fill in the mail server names first.", "fail"
    if not (mb.get("imap_ssl", True) or mb.get("imap_starttls")):
        return False, UNENCRYPTED_MSG, "fail"
    if not password:
        return False, "Please enter the password first.", "fail"
    pin = (mb.get("tls_cert_sha256") or None)
    local = is_loopback(str(mb["imap_host"])) or is_loopback(str(mb["smtp_host"]))
    if local and not pin:
        return False, ("Free My ID needs you to approve this mail app's security code "
                       "first."), "needs_trust"

    user = mb.get("username") or mb.get("address") or ""
    try:
        ih, ip = mb["imap_host"], int(mb["imap_port"])
        ictx = client_context(ih, pin if is_loopback(ih) else None)
        ipin = pin if is_loopback(ih) else None
        if mb.get("imap_ssl", True):
            im: imaplib.IMAP4 = imaplib.IMAP4_SSL(ih, ip, ssl_context=ictx, timeout=timeout)
        else:
            im = imaplib.IMAP4(ih, ip, timeout=timeout)
            if mb.get("imap_starttls"):
                im.starttls(ictx)
        try:
            check_peer(im.sock, ipin)           # before any credential is sent
            im.login(user, password)
        finally:
            try:
                im.logout()
            except Exception:  # noqa: BLE001
                log.debug("logout failed")
    except TlsPinError:
        return False, _CHANGED_MSG, "cert_changed"
    except imaplib.IMAP4.error:
        return False, ("The mail server did not accept that address and password. Please "
                       "check them (use an app password, not your normal one)."), "fail"
    except (OSError, ssl.SSLError):
        return False, unreachable_message(mb["imap_host"]), "fail"
    try:
        sh, sp = mb["smtp_host"], int(mb["smtp_port"])
        spin = pin if is_loopback(sh) else None
        sctx = client_context(sh, spin)
        if mb.get("smtp_starttls"):
            sm: smtplib.SMTP = smtplib.SMTP(sh, sp, timeout=timeout)
            sm.ehlo()
            sm.starttls(context=sctx)
            sm.ehlo()
        else:
            sm = smtplib.SMTP_SSL(sh, sp, timeout=timeout, context=sctx)
        try:
            check_peer(sm.sock, spin)           # before any credential is sent
            sm.login(user, password)
        finally:
            try:
                sm.quit()
            except Exception:  # noqa: BLE001
                log.debug("quit failed")
    except TlsPinError:
        return False, _CHANGED_MSG, "cert_changed"
    except (smtplib.SMTPException, OSError, ssl.SSLError):
        msg = ("Incoming mail works, but sending did not. Please check the outgoing server "
               "name and port, then press Test again.")
        return False, msg, "fail"
    return True, "Connection works. Free My ID can read and send from this mailbox.", "ok"


def unreachable_message(host: str) -> str:
    """Calm text for a mail app/server that did not answer. Never includes an exception name."""
    if is_loopback(host):
        return ("Free My ID could not find Proton Mail Bridge on this computer. Please open "
                "Proton Mail Bridge, sign in, wait until it says it is running, then press "
                "Test again.")
    return ("Free My ID could not reach that mail server. Please check the server name and "
            "your internet connection, then press Test again.")


_CHANGED_MSG = ("The security code of your mail app is not the one you approved. Nothing was "
                "sent. This can happen after Proton Mail Bridge is reinstalled or updated.")


# --------------------------------------------------------------------------- build + save


def build_profile(d: Draft) -> Profile:
    if not d.consent_ack and d.existing_consent is None:
        raise SaveError("Consent has not been given.")
    minor = is_minor(d)
    if d.existing_consent is not None and not d.consent_ack:
        consent = d.existing_consent
    else:
        consent = Consent(basis=ConsentBasis(d.basis), attested_by=d.attested_by,
                          attested_at=d.consent_at or utcnow(), text_version=CONSENT_VERSION,
                          authorization_doc=(d.existing_consent.authorization_doc
                                             if d.existing_consent else None))
    if minor and consent.basis != ConsentBasis.GUARDIAN_OF_MINOR:
        raise SaveError("A parent or guardian must give permission for someone under 18.")
    mailbox = None
    if d.mailbox and not d.skip_mailbox:
        try:
            mailbox = MailboxConfig(**d.mailbox, keyring_service="freemyid-mailbox")
        except ValueError as e:
            if not (d.mailbox.get("imap_ssl") or d.mailbox.get("imap_starttls")):
                raise SaveError(UNENCRYPTED_MSG) from e
            raise SaveError("The email settings look incomplete; please go back and "
                            "check them.") from e
    try:
        return Profile(
            id=d.id, label=d.label or d.first, consent=consent,
            name=PersonName(first=d.first, middle=d.middle or None, last=d.last,
                            suffix=d.suffix or None),
            nicknames=d.nicknames,
            previous_names=[parse_person_name(n) for n in d.previous_names],
            addresses=[Address(**{k: (v or None) if k in ("street", "zip") else v  # type: ignore[arg-type]
                                  for k, v in a.items()}) for a in d.addresses],
            dob=date.fromisoformat(d.dob) if d.dob else None,
            age=int(d.age) if d.age and not d.dob else None,
            phones=d.phones, emails=d.emails, relatives=d.relatives, is_minor=minor,
            mailbox=mailbox, email_mode=EmailMode(d.email_mode),
            permissions=Permissions(allow_id_upload=d.allow_id_upload,
                                    allow_account_creation=d.allow_account_creation,
                                    allow_phone_disclosure=d.allow_phone_disclosure),
            schedule=ScheduleConfig(weekly_recheck=d.weekly_recheck, weekday=d.weekday,
                                    hour=d.hour),
        )
    except ValueError as e:   # pydantic ValidationError subclasses ValueError
        raise SaveError("Some details are missing or invalid; please go back and check them."
                        ) from e


def save_authorization(store, pid: str, name: str, data: bytes) -> str:
    """Encrypt the signed authorization form as evidence; return the evidence id."""
    ev = Evidence(profile_id=pid, broker_id="_consent", kind=EvidenceKind.LETTER,
                  relpath=f"{pid}/consent/authorization-{new_id()[:8]}.bin", sha256="",
                  caption="Signed authorization (agent consent)")
    ev = store.save_evidence(ev, data)
    return ev.id


def save_draft(store, d: Draft, actor: Actor = Actor.WIZARD) -> Profile:
    """Validate, store the profile, put the mailbox password in the keychain."""
    from ..secrets import set_mailbox_password

    prof = build_profile(d)
    if d.auth_bytes:
        doc = save_authorization(store, prof.id, d.auth_filename, d.auth_bytes)
        prof = prof.model_copy(update={
            "consent": prof.consent.model_copy(update={"authorization_doc": doc})})
    if prof.mailbox and d.password:
        try:
            set_mailbox_password(prof.id, prof.mailbox, d.password)
        except Exception as e:
            raise SaveError("Could not store the mailbox password in this computer's "
                            "keychain. Unlock the keychain and try again.") from e
    prior = store.get_profile(prof.id)
    if prior:
        prof = prof.model_copy(update={"created_at": prior.created_at})
    store.save_profile(prof)
    store.log(Event(profile_id=prof.id, actor=actor,
                    action="profile_updated" if d.editing else "profile_created",
                    detail={"consent_basis": prof.consent.basis.value,
                            "consent_text_version": prof.consent.text_version}))
    d.password = ""
    return prof


def _provider_of(p: Profile) -> str:
    if not p.mailbox:
        return "gmail"
    for name, preset in PRESETS.items():
        if preset["imap_host"] and preset["imap_host"] == p.mailbox.imap_host:
            return name
    return p.mailbox.provider or "other"


def _has_saved_password(p: Profile) -> bool:
    """True only if the password is really in the secret store (never in the DB)."""
    if not p.mailbox:
        return False
    try:
        from ..secrets import get_mailbox_password
        return bool(get_mailbox_password(p.id, p.mailbox))
    except Exception:  # noqa: BLE001 - a broken keychain must not break the settings page
        return False


def draft_from_profile(p: Profile, *, keep_consent: bool = True) -> Draft:
    d = Draft(provider=_provider_of(p), id=p.id, editing=True, label=p.label, first=p.name.first,
              middle=p.name.middle or "", last=p.name.last, suffix=p.name.suffix or "",
              nicknames=list(p.nicknames),
              previous_names=[" ".join(x for x in (n.first, n.middle, n.last) if x)
                              for n in p.previous_names],
              addresses=[{"street": a.street or "", "city": a.city, "state": a.state,
                              "zip": a.zip or "", "current": a.current} for a in p.addresses],
              dob=p.dob.isoformat() if p.dob else "", age=str(p.age) if p.age is not None else "",
              phones=list(p.phones), emails=list(p.emails), relatives=list(p.relatives),
              allow_id_upload=p.permissions.allow_id_upload,
              allow_account_creation=p.permissions.allow_account_creation,
              allow_phone_disclosure=p.permissions.allow_phone_disclosure,
              email_mode=p.email_mode.value, weekly_recheck=p.schedule.weekly_recheck,
              weekday=p.schedule.weekday, hour=p.schedule.hour,
              basis=p.consent.basis.value, attested_by=p.consent.attested_by)
    if keep_consent:
        d.existing_consent = p.consent
    d.mailbox_answered = True
    if p.mailbox:
        d.saved_password = _has_saved_password(p)
        d.mailbox = p.mailbox.model_dump(exclude={"keyring_service"})
        d.tls_pin = p.mailbox.tls_cert_sha256 or ""
    else:
        d.skip_mailbox = True
    return d
