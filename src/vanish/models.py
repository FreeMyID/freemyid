"""Shared data contracts for Vanish.

OWNER: orchestrator. Other agents must not edit this file; send change requests instead.

Everything here is plain data (pydantic v2). No I/O, no network, no Playwright.
"""
from __future__ import annotations

import re
import string
import uuid
from datetime import UTC, date, datetime
from enum import StrEnum
from pathlib import PurePosixPath
from typing import Annotated, Any, Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator, model_validator


def utcnow() -> datetime:
    return datetime.now(UTC)


def new_id() -> str:
    return uuid.uuid4().hex


# SEC-02: ids end up in filesystem paths (evidence/<profile_id>/...), so they are constrained.
Id = Annotated[str, Field(pattern=r"^[0-9a-f]{32}$")]
BrokerId = Annotated[str, Field(pattern=r"^[a-z0-9_]{1,64}$")]


def _safe_relpath(v: str | None) -> str | None:
    if v is None:
        return v
    if not v or "\\" in v or "\x00" in v:
        raise ValueError("relpath must be a non-empty POSIX relative path")
    p = PurePosixPath(v)
    if p.is_absolute() or any(part in ("..", "") for part in v.split("/")):
        raise ValueError("relpath must be relative and must not contain '..'")
    return v


# SEC-07: hosts a (remotely updatable) registry may name. Public suffixes / shared hosting
# would make NetPolicy allow unrelated sites.
_HOST_RE = re.compile(r"^(?=.{4,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$")
_SHARED_SUFFIXES = frozenset({
    "github.io", "githubusercontent.com", "gitlab.io", "herokuapp.com", "appspot.com",
    "cloudfront.net", "amazonaws.com", "azurewebsites.net", "blogspot.com", "netlify.app",
    "vercel.app", "pages.dev", "workers.dev", "web.app", "firebaseapp.com", "co.uk", "com.au",
    "co.nz", "co.jp", "com.br", "co.in",
})
_SEARCH_PLACEHOLDERS = frozenset(
    {"first", "last", "middle", "city", "state", "state_name", "zip", "phone"})
_SUBMITTER_RE = re.compile(r"^vanish\.submitters\.[a-z0-9_.]+:[A-Za-z_][A-Za-z0-9_]*$")


def _check_host(h: str) -> str:
    if not _HOST_RE.match(h) or h in _SHARED_SUFFIXES:
        raise ValueError(f"invalid or shared-suffix hostname: {h!r}")
    return h


def _host_in(host: str | None, domains: list[str]) -> bool:
    if not host:
        return False
    host = host.lower().rstrip(".")
    return any(host == d or host.endswith("." + d) for d in domains)


class _Base(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)


# --------------------------------------------------------------------------- enums


class Method(StrEnum):
    WEB_FORM = "web_form"
    EMAIL = "email"
    POSTAL = "postal"
    PHONE = "phone"
    ACCOUNT_REQUIRED = "account_required"


class BrokerCategory(StrEnum):
    PEOPLE_SEARCH = "people_search"
    BACKGROUND_CHECK = "background_check"
    DATA_BROKER = "data_broker"          # B2B / marketing data (Acxiom, Epsilon, ...)
    RISK_DATA = "risk_data"              # LexisNexis-style identity/risk data
    FAMILY_TREE = "family_tree"
    PHONE_LOOKUP = "phone_lookup"
    OTHER = "other"


class VerificationStatus(StrEnum):
    VERIFIED = "verified"        # opt-out URL loaded live and matched the cited source
    UNVERIFIED = "unverified"    # could not be confirmed live; see verification_notes
    BROKEN = "broken"            # health check found it dead/changed


class ProfileField(StrEnum):
    """Profile data a broker's opt-out may require."""
    FULL_NAME = "full_name"
    FIRST_NAME = "first_name"
    LAST_NAME = "last_name"
    MIDDLE_NAME = "middle_name"
    CITY = "city"
    STATE = "state"
    ZIP = "zip"
    STREET_ADDRESS = "street_address"
    AGE = "age"
    DOB = "dob"
    PHONE = "phone"
    EMAIL = "email"               # the dedicated removal mailbox, never personal email
    LISTING_URL = "listing_url"
    ID_DOCUMENT = "id_document"


class ListingState(StrEnum):
    """Per (profile, broker) state. See vanish.state for transitions."""
    UNKNOWN = "unknown"                       # never scanned
    NOT_FOUND = "not_found"
    FOUND = "found"
    SUBMITTED = "submitted"
    AWAITING_VERIFICATION = "awaiting_verification"
    CONFIRMED = "confirmed"                   # broker acknowledged / verification clicked
    REMOVED = "removed"                       # re-scan no longer finds listing
    REAPPEARED = "reappeared"
    NEEDS_HUMAN = "needs_human"               # captcha / ID / unexpected page / manual method
    ERROR = "error"


class RequestKind(StrEnum):
    OPT_OUT = "opt_out"
    RESUBMIT = "resubmit"
    FOLLOW_UP = "follow_up"
    LEGAL_DEMAND = "legal_demand"


class RequestStatus(StrEnum):
    DRAFT = "draft"
    QUEUED_FOR_APPROVAL = "queued_for_approval"   # email waiting on user approval
    SENT = "sent"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Actor(StrEnum):
    USER = "user"
    SCHEDULER = "scheduler"
    ENGINE = "engine"
    WIZARD = "wizard"
    SYSTEM = "system"


class ConsentBasis(StrEnum):
    SELF = "self"                          # "I am this person"
    GUARDIAN_OF_MINOR = "guardian_of_minor"
    AUTHORIZED_AGENT = "authorized_agent"  # signed written permission from the adult


class EmailMode(StrEnum):
    APPROVE_EACH = "approve_each"   # default: every outgoing email queued for user approval
    AUTO = "auto"                   # opt-in; legal demands STILL require approval


class Tier(StrEnum):
    """How Vanish handles a broker for a profile (docs/PLAN_V1.md D1)."""
    EMAIL = "email"          # automatic privacy-request letter from the removal mailbox
    ASSISTED = "assisted"    # user does it in their own browser with copy buttons
    AUTOMATIC = "automatic"  # Playwright, data-driven Broker.search/form, verified brokers only


class TodoKind(StrEnum):
    CAPTCHA = "captcha"
    ID_UPLOAD = "id_upload"
    UNEXPECTED_PAGE = "unexpected_page"
    POSTAL_LETTER = "postal_letter"
    PHONE_CALL = "phone_call"
    ACCOUNT_REQUIRED = "account_required"
    APPROVE_EMAIL = "approve_email"
    COMPLAINT = "complaint"           # escalate to AG / CPPA
    GOVERNMENT_PORTAL = "government_portal"  # e.g. California DROP
    REVIEW_MATCH = "review_match"     # possible match; user confirms it's them
    ASSISTED_OPT_OUT = "assisted_opt_out"  # "Do it with me": user fills the form in own browser
    SEND_EMAIL_MANUALLY = "send_email_manually"  # no mailbox: user sends the prepared letter
    PERMISSION_NEEDED = "permission_needed"  # broker wants ID/account/phone, flag is off
    OTHER = "other"


class EvidenceKind(StrEnum):
    SCREENSHOT = "screenshot"
    HTML = "html"
    EMAIL_SENT = "email_sent"
    EMAIL_RECEIVED = "email_received"
    LETTER = "letter"


# --------------------------------------------------------------------------- profile


class Consent(_Base):
    basis: ConsentBasis
    attested_by: str = Field(description="Name typed by the person giving consent")
    attested_at: datetime = Field(default_factory=utcnow)
    text_version: str = Field(description="Version id of the consent text shown")
    authorization_doc: str | None = Field(
        default=None, description="Evidence id of signed agent authorization (AUTHORIZED_AGENT)"
    )

    @model_validator(mode="after")
    def _agent_needs_doc_flag(self) -> Consent:
        # Authorization doc may be attached after setup; enforcement happens at run time.
        return self


class PersonName(_Base):
    first: str
    middle: str | None = None
    last: str
    suffix: str | None = None

    @property
    def full(self) -> str:
        parts = [self.first, self.middle, self.last, self.suffix]
        return " ".join(p for p in parts if p)


class Address(_Base):
    street: str | None = None
    city: str
    state: str = Field(min_length=2, max_length=2, description="USPS 2-letter code")
    zip: str | None = None
    current: bool = False
    from_year: int | None = None
    to_year: int | None = None

    @field_validator("state")
    @classmethod
    def _upper(cls, v: str) -> str:
        return v.upper()


class MailboxConfig(_Base):
    """Dedicated removal mailbox. Password lives ONLY in the OS keychain."""
    address: str
    provider: Literal["gmail", "yahoo", "icloud", "outlook", "proton_bridge", "other"] = "other"
    imap_host: str
    imap_port: int = 993
    imap_ssl: bool = True          # implicit TLS (993)
    imap_starttls: bool = False    # e.g. Proton Bridge 127.0.0.1:1143
    smtp_host: str
    smtp_port: int = 465
    smtp_starttls: bool = False
    username: str
    keyring_service: str = "vanish-mailbox"
    # keyring username is f"{profile_id}:{address}"


class Permissions(_Base):
    """Off by default. If a broker demands one of these and the flag is False, NEEDS_HUMAN.

    Paying money is never permitted and has no flag.
    """
    allow_id_upload: bool = False
    allow_account_creation: bool = False
    allow_phone_disclosure: bool = False


class MatchLevel(StrEnum):
    CONFIRMED = "confirmed"   # name match AND >=2 supporting signals -> auto-submit allowed
    POSSIBLE = "possible"     # name match AND exactly 1 signal -> NEEDS_HUMAN review
    NO_MATCH = "no_match"     # ignored


class ScheduleConfig(_Base):
    weekly_recheck: bool = True
    weekday: int = Field(default=6, ge=0, le=6, description="0=Mon .. 6=Sun")
    hour: int = Field(default=10, ge=0, le=23)
    respect_broker_intervals: bool = True


class Profile(_Base):
    id: Id = Field(default_factory=new_id)
    label: str = Field(description="Display name, e.g. 'Mom'")
    consent: Consent
    name: PersonName
    nicknames: list[str] = []
    previous_names: list[PersonName] = []
    addresses: list[Address] = Field(min_length=1)
    dob: date | None = None
    age: int | None = Field(default=None, ge=0, le=130)
    phones: list[str] = []
    emails: list[str] = []          # personal emails: for matching only, never sent anywhere
    relatives: list[str] = []
    is_minor: bool = False
    mailbox: MailboxConfig | None = None
    email_mode: EmailMode = EmailMode.APPROVE_EACH
    permissions: Permissions = Permissions()
    schedule: ScheduleConfig = ScheduleConfig()
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)

    @property
    def state_of_residence(self) -> str:
        cur = [a for a in self.addresses if a.current]
        return (cur or self.addresses)[0].state

    def estimated_age(self, today: date | None = None) -> int | None:
        if self.dob:
            t = today or date.today()
            return t.year - self.dob.year - ((t.month, t.day) < (self.dob.month, self.dob.day))
        return self.age

    def all_names(self) -> list[PersonName]:
        return [self.name, *self.previous_names]


# --------------------------------------------------------------------------- broker registry


class FormStep(_Base):
    """Declarative web-form step, so most brokers need no Python.

    `value` is a jinja2 template rendered with {profile, listing, mailbox, broker}.
    """
    action: Literal[
        "goto", "fill", "select", "check", "click", "wait_for", "screenshot", "submit",
        "expect_text", "human",
    ]
    selector: str | None = None
    value: str | None = None
    url: str | None = None
    timeout_ms: int = 15000
    note: str | None = None


class SearchSpec(_Base):
    """How to find listings. Selectors are CSS; all optional so researcher can fill later."""
    result_selector: str | None = None
    name_selector: str | None = None
    age_selector: str | None = None
    location_selector: str | None = None
    relatives_selector: str | None = None
    link_selector: str | None = None
    no_results_text: str | None = None


class PostalContact(_Base):
    recipient: str
    lines: list[str]


class Broker(_Base):
    id: BrokerId
    name: str
    url: HttpUrl
    category: BrokerCategory
    domains: list[str] = Field(min_length=1, description="Hostnames the engine may contact")
    search_url_pattern: str | None = Field(
        default=None,
        description="Python format string. Placeholders: {first} {last} {middle} {city} {state} "
        "{state_name} {zip} {phone}; values are slugified/URL-encoded by the engine",
    )
    opt_out_url: HttpUrl | None = None
    search_page_url: HttpUrl | None = Field(
        default=None, description="Page with the people-search form, if not Broker.url "
        "(listing finder)",
    )
    method: Method
    alt_methods: list[Method] = []
    opt_out_email: str | None = None
    postal: PostalContact | None = None
    phone: str | None = None
    required_fields: list[ProfileField] = []
    needs_email_verification: bool = False
    confirmation_domains: list[str] = Field(
        default=[], description="Only links on these domains are auto-clicked from IMAP"
    )
    has_captcha: bool = False
    needs_id_upload: bool = False
    typical_processing_days: int = Field(default=30, ge=0, le=365)
    recheck_interval_days: int = Field(default=30, ge=1, le=365)
    parent_company: str | None = None
    feeds_from: list[str] = Field(default=[], description="Broker ids this site copies from")
    covered_by: str | None = Field(
        default=None, description="Broker id whose opt-out also removes this site (shared "
        "suppression center); engine submits once to covered_by and only re-scans this one",
    )
    legal_basis_notes: str | None = None
    ca_registered: bool | None = None   # on California data broker registry
    vt_registered: bool | None = None
    steps: list[str] = Field(default=[], description="Human-readable step-by-step notes")
    search: SearchSpec | None = None
    form: list[FormStep] = []
    success_text: list[str] = Field(
        default=[], description="Visible text that means the opt-out was accepted (any match). "
        "Used by 'Fill it in for me' when the form steps have no expect_text",
    )
    success_url_pattern: str | None = Field(
        default=None, max_length=200,
        description="Regex matched against the URL path+query after submit; a match = success",
    )
    safe_checkboxes: list[str] = Field(
        default=[], description="CSS selectors of plain consent checkboxes 'Fill it in for me' "
        "may tick (never CAPTCHA, never marketing opt-ins). Empty = tick nothing",
    )
    listing_url_pattern: str | None = Field(
        default=None, max_length=200,
        description="Regex matched against a listing page's URL path (listing finder)",
    )
    submitter: str | None = Field(
        default=None, description="Optional custom submitter 'module:Class'"
    )
    source_urls: list[HttpUrl] = Field(default=[], description="Citations for opt-out info")
    verification_status: VerificationStatus = VerificationStatus.UNVERIFIED
    verification_notes: str | None = None
    last_verified: date | None = None
    priority: int = Field(default=50, ge=0, le=100, description="Higher runs first")
    enabled: bool = True

    @field_validator("domains", "confirmation_domains")
    @classmethod
    def _hosts(cls, v: list[str]) -> list[str]:
        return [_check_host(h) for h in v]

    @field_validator("success_url_pattern", "listing_url_pattern")
    @classmethod
    def _regex(cls, v: str | None) -> str | None:
        if v is not None:
            re.compile(v)   # raises -> validation error
        return v

    @field_validator("submitter")
    @classmethod
    def _submitter_ns(cls, v: str | None) -> str | None:
        if v is not None and not _SUBMITTER_RE.match(v):
            raise ValueError("submitter must be 'vanish.submitters.<module>:<Class>'")
        return v

    @model_validator(mode="after")
    def _hosts_inside_domains(self) -> Broker:
        doms = self.domains
        urls = [str(self.url), str(self.opt_out_url) if self.opt_out_url else None,
                str(self.search_page_url) if self.search_page_url else None]
        urls += [st.url for st in self.form if st.url]
        for u in filter(None, urls):
            if not _host_in(urlsplit(u).hostname, doms):
                raise ValueError(f"{self.id}: URL host outside broker domains: {u}")
        if self.search_url_pattern:
            fields = {f for _, f, _, _ in string.Formatter().parse(self.search_url_pattern) if f}
            if bad := fields - _SEARCH_PLACEHOLDERS:
                raise ValueError(f"{self.id}: unknown search placeholders {sorted(bad)}")
            probe = self.search_url_pattern.format(**{k: "x" for k in fields})
            if urlsplit(probe).scheme != "https" or not _host_in(urlsplit(probe).hostname, doms):
                raise ValueError(f"{self.id}: search_url_pattern must be https on broker domains")
        if self.opt_out_email:
            local, _, host = self.opt_out_email.rpartition("@")
            if not local or not _host_in(host, doms):
                raise ValueError(f"{self.id}: opt_out_email must be on a broker domain")
        return self

    @model_validator(mode="after")
    def _method_requirements(self) -> Broker:
        if self.verification_status == VerificationStatus.VERIFIED:
            if not self.source_urls:
                raise ValueError(f"{self.id}: verified brokers must cite source_urls")
            if not self.last_verified:
                raise ValueError(f"{self.id}: verified brokers need last_verified")
        if self.method == Method.EMAIL and not self.opt_out_email:
            raise ValueError(f"{self.id}: method=email requires opt_out_email")
        if self.method == Method.POSTAL and not self.postal:
            raise ValueError(f"{self.id}: method=postal requires postal")
        if self.method == Method.PHONE and not self.phone:
            raise ValueError(f"{self.id}: method=phone requires phone")
        if self.method in (Method.WEB_FORM, Method.ACCOUNT_REQUIRED) and not self.opt_out_url:
            raise ValueError(f"{self.id}: method={self.method} requires opt_out_url")
        return self


class StateLaw(_Base):
    state: str = Field(min_length=2, max_length=2)
    statute_name: str | None = None          # e.g. "California Consumer Privacy Act (CPRA)"
    citation: str | None = None              # e.g. "Cal. Civ. Code § 1798.105"
    effective_date: date | None = None
    rights: list[str] = []                   # delete, opt_out_sale, opt_out_targeting, ...
    response_days: int | None = None
    extension_days: int | None = None
    data_broker_law: str | None = None       # e.g. CA Delete Act
    government_portal_url: HttpUrl | None = None   # e.g. DROP
    ag_complaint_url: HttpUrl | None = None
    other_complaint_urls: list[HttpUrl] = []
    authorized_agent_allowed: bool | None = None
    template: str = Field(default="generic", description="Template family to use")
    notes: str | None = None
    source_urls: list[HttpUrl] = []
    last_verified: date | None = None


class Registry(_Base):
    version: str
    updated: date
    brokers: list[Broker]

    @model_validator(mode="after")
    def _unique_ids(self) -> Registry:
        ids = [b.id for b in self.brokers]
        dupes = {i for i in ids if ids.count(i) > 1}
        if dupes:
            raise ValueError(f"duplicate broker ids: {sorted(dupes)}")
        known = set(ids)
        for b in self.brokers:
            bad = [f for f in [*b.feeds_from, *([b.covered_by] if b.covered_by else [])]
                   if f not in known]
            if bad:
                raise ValueError(f"{b.id}: feeds_from references unknown ids {bad}")
        return self

    def get(self, broker_id: str) -> Broker:
        for b in self.brokers:
            if b.id == broker_id:
                return b
        raise KeyError(broker_id)


class StateLawRegistry(_Base):
    version: str
    updated: date
    states: list[StateLaw]


# --------------------------------------------------------------------------- runtime records


class Listing(_Base):
    id: Id = Field(default_factory=new_id)
    profile_id: Id
    broker_id: BrokerId
    url: str
    name_shown: str | None = None
    age_shown: int | None = None
    locations_shown: list[str] = []
    relatives_shown: list[str] = []
    match_score: float = Field(ge=0, le=100)
    match_level: MatchLevel
    match_reasons: list[str] = []   # signal names only: "city", "age", "relative", "phone"
    shown_fields: list[ProfileField] = Field(
        default=[], description="What the listing displays. Data minimization: submitters "
        "may only send the broker fields in this list, plus the removal mailbox address.",
    )
    first_seen: datetime = Field(default_factory=utcnow)
    last_seen: datetime = Field(default_factory=utcnow)
    gone_since: datetime | None = None


class Request(_Base):
    id: Id = Field(default_factory=new_id)
    profile_id: Id
    broker_id: BrokerId
    kind: RequestKind
    method: Method
    listing_ids: list[Id] = []
    status: RequestStatus = RequestStatus.DRAFT
    created_at: datetime = Field(default_factory=utcnow)
    sent_at: datetime | None = None
    original_request_id: Id | None = None   # for follow-ups / legal demands
    reference: str | None = None             # broker ticket / confirmation number
    attempt: int = 1
    dry_run: bool = False


class BrokerStatus(_Base):
    """Current state for one (profile, broker). History lives in Event rows."""
    profile_id: Id
    broker_id: BrokerId
    state: ListingState = ListingState.UNKNOWN
    updated_at: datetime = Field(default_factory=utcnow)
    last_scan_at: datetime | None = None
    last_submitted_at: datetime | None = None
    attempts: int = 0
    escalation_level: int = 0     # 0 none, 1 resubmitted, 2 follow-up, 3 legal demand, 4 complaint
    last_escalated_at: datetime | None = None
    next_check_at: datetime | None = None
    needs_human_reason: str | None = None
    tier: Tier | None = None      # set by engine.runner each run


class Evidence(_Base):
    id: Id = Field(default_factory=new_id)
    profile_id: Id
    broker_id: BrokerId
    kind: EvidenceKind
    listing_id: Id | None = None
    request_id: Id | None = None
    relpath: str = Field(description="Path under VANISH_HOME/evidence, encrypted file")
    sha256: str
    created_at: datetime = Field(default_factory=utcnow)
    caption: str | None = None

    _relpath_ok = field_validator("relpath")(classmethod(lambda cls, v: _safe_relpath(v)))


class Event(_Base):
    """Append-only audit row. `detail` MUST NOT contain PII (ids/enums/counts only)."""
    id: Id = Field(default_factory=new_id)
    ts: datetime = Field(default_factory=utcnow)
    profile_id: Id | None = None
    broker_id: BrokerId | None = None
    actor: Actor
    action: str
    from_state: ListingState | None = None
    to_state: ListingState | None = None
    detail: dict[str, Any] = {}


class Todo(_Base):
    id: Id = Field(default_factory=new_id)
    profile_id: Id
    broker_id: BrokerId | None = None
    kind: TodoKind
    title: str
    body: str = ""
    links: list[str] = []
    request_id: Id | None = None
    artifact_relpath: str | None = None    # letter / call script
    created_at: datetime = Field(default_factory=utcnow)
    done_at: datetime | None = None
    resume_token: str | None = None        # engine uses to resume after human step
    copy_fields: dict[str, str] = Field(
        default={}, repr=False,
        description="Label -> value shown with a Copy button on Assisted cards. "
        "Only fields the broker needs (data minimization); never stored in logs.")

    _relpath_ok = field_validator("artifact_relpath")(
        classmethod(lambda cls, v: _safe_relpath(v)))


class SubmitOutcome(_Base):
    """What a submitter returns to the engine."""
    new_state: ListingState
    request: Request | None = None
    evidence: list[Evidence] = []
    todos: list[Todo] = []
    message: str = ""     # non-PII summary for logs
