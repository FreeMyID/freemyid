"""Coverage for profile registration and sensitive log-record fields."""
from __future__ import annotations

import logging
from datetime import date
from io import StringIO
from urllib.parse import quote, quote_plus

import pytest

from freemyid import logging_setup
from freemyid.logging_setup import RedactingFilter, register_profile
from freemyid.models import (
    Address,
    Consent,
    ConsentBasis,
    MailboxConfig,
    PersonName,
    Profile,
)


@pytest.fixture(autouse=True)
def restore_pii_registry():
    """Isolate this module's registered synthetic values from all other tests."""
    with logging_setup._lock:
        saved = set(logging_setup._pii)
        logging_setup._pii.clear()
    try:
        yield
    finally:
        with logging_setup._lock:
            logging_setup._pii.clear()
            logging_setup._pii.update(saved)


def fake_profile() -> Profile:
    return Profile(
        label="Sample Profile",
        consent=Consent(
            basis=ConsentBasis.SELF,
            attested_by="Casey Exampleperson",
            text_version="test-v1",
        ),
        name=PersonName(first="Jane", middle="Quinn", last="Testperson", suffix="Jr"),
        previous_names=[
            PersonName(first="Alex", middle="Riley", last="Formerperson", suffix="Sr"),
            PersonName(first="Avery", last="Previousperson"),
        ],
        nicknames=["Janey Sample", "J Testperson"],
        addresses=[
            Address(street="742 Example Terrace", city="Testville", state="IL", zip="63107"),
            Address(street="19 Sample Road", city="Mockburg", state="NY", zip="10019"),
        ],
        dob=date(1981, 2, 3),
        phones=["217-555-0142", "+1 312 555 0188"],
        emails=["jane.testperson@example.com", "former.person@example.net"],
        relatives=["Morgan Exampleperson", "Taylor Sampleperson"],
        mailbox=MailboxConfig(
            address="removal.box@example.org",
            username="synthetic-mailbox-user",
            imap_host="imap.fake.example",
            smtp_host="smtp.fake.example",
        ),
    )


def variants(value: str) -> set[str]:
    values = {value, value.upper(), quote(value, safe=""), quote_plus(value, safe="")}
    words = value.split()
    if len(words) > 1:
        values.update(separator.join(words) for separator in ("+", "_", "-", ".", "%20"))
    return values


def capture_logged_text(monkeypatch: pytest.MonkeyPatch, *, stack_marker: str | None = None):
    stream = StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(logging.Formatter("%(message)s %(stack_info)s"))
    handler.addFilter(RedactingFilter())
    # A private Logger object: nothing shared through the logging registry, so no other
    # test (or pytest's own capture handlers) can attach to it or reuse its name.
    logger = logging.Logger(f"codex.redaction.fields.{id(stream)}")  # noqa: LOG001
    logger.setLevel(logging.INFO)
    logger.propagate = False
    logger.addHandler(handler)
    if stack_marker is not None:
        monkeypatch.setattr(
            logging.Logger,
            "findCaller",
            lambda self, stack_info, stacklevel=1: (
                "fake.py", 1, "test", stack_marker if stack_info else None,
            ),
        )
    return logger, handler, stream


def test_register_profile_redacts_every_field_and_common_encoding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    profile = fake_profile()
    register_profile(profile)
    logger, handler, stream = capture_logged_text(monkeypatch)
    values = [
        profile.label,
        "Jane", "Quinn", "Testperson", "Jr", "Jane Quinn Testperson Jr", "Jane Testperson",
        "Testperson Jane", "Jane Quinn Testperson", "Alex", "Riley", "Formerperson", "Sr",
        "Formerperson Alex", "Alex Formerperson", "Alex Riley Formerperson Sr",
        "Avery", "Previousperson", "Avery Previousperson", "Previousperson Avery",
        "Janey Sample", "J Testperson", "742 Example Terrace", "Testville", "63107",
        "19 Sample Road", "Mockburg", "10019", "217-555-0142", "+1 312 555 0188",
        "jane.testperson@example.com", "former.person@example.net", "Morgan Exampleperson",
        "Taylor Sampleperson", "Casey Exampleperson", "removal.box@example.org",
        "synthetic-mailbox-user",
    ]
    try:
        all_variants = {variant for value in values for variant in variants(value)}
        for text in sorted(all_variants):
            logger.warning("synthetic fixture: %s", text)
        output = stream.getvalue().casefold()
        assert "[pii]" in output or "[email]" in output or "[phone]" in output
        leaked = [text for text in all_variants if text and text.casefold() in output]
        assert not leaked, f"registered profile values remained in log output: {leaked!r}"
    finally:
        logger.removeHandler(handler)
        handler.close()


@pytest.mark.parametrize("date_form", [
    "1981-02-03", "1981/02/03", "19810203", "02/03/1981", "2/3/1981",
    "02-03-1981", "2-3-1981", "02/03/81", "2/3/81",
])
def test_registered_dob_redacts_all_supported_forms_and_keeps_timestamps(
    date_form: str,
) -> None:
    profile = fake_profile()
    register_profile(profile)
    assert date_form not in logging_setup.redact(f"date={date_form}")
    timestamp = "2026-11-09T12:00:00"
    assert timestamp in logging_setup.redact(f"updated={timestamp}")


def test_zip_word_boundary_and_one_character_registration() -> None:
    register_profile(fake_profile())
    text = logging_setup.redact("zip 63107; order 631073; suffix X63107Z")
    assert "63107" not in text.split(";", maxsplit=1)[0]
    assert "631073" in text
    assert "X63107Z" in text
    logging_setup.register_pii("x")
    assert logging_setup.redact("single x marker") == "single x marker"


def test_stack_info_and_bad_format_args_are_redacted_without_raising(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    register_profile(fake_profile())
    marker = "Casey Exampleperson stack synthetic marker"
    logger, handler, stream = capture_logged_text(monkeypatch, stack_marker=marker)
    try:
        logger.warning("captured stack", stack_info=True)
        bad_format = "%s %s"
        logger.info(bad_format, "Casey Exampleperson")
        output = stream.getvalue()
        assert "captured stack" in output
        assert "Casey Exampleperson" not in output
        assert "Exampleperson" not in output
    finally:
        logger.removeHandler(handler)
        handler.close()
