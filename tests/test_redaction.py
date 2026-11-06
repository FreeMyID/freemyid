"""logging_setup: PII redaction in messages, args, tracebacks and the log file."""
from __future__ import annotations

import logging

import pytest

from freemyid import logging_setup
from freemyid.logging_setup import RedactingFilter, redact, register_pii

PID = "0" * 32  # valid Id


@pytest.fixture
def caplog_redacted(caplog):
    caplog.handler.addFilter(RedactingFilter())
    yield caplog
    caplog.handler.removeFilter(caplog.handler.filters[-1])


@pytest.mark.parametrize("text", [
    "mail jane.testperson@example.com now", "call 217-555-0142", "call (217) 555-0142",
    "call +1 217 555 0142", "call 2175550142",
])
def test_regex_backstop(text):
    out = redact(text)
    assert "testperson" not in out.lower() and "555" not in out


def test_registered_values_case_insensitive_and_slug():
    register_pii("Jane Testperson", "Springfield")
    out = redact("JANE TESTPERSON of springfield at /name/jane-testperson/il")
    assert "testperson" not in out.lower()
    assert "springfield" not in out.lower()


def test_short_values_ignored_not_crash():
    register_pii(None, "", "  ")
    assert redact("hello") == "hello"


def test_filter_redacts_args(caplog_redacted):
    register_pii("Testperson")
    logging.getLogger("t").warning("found %s at %s", "Jane Testperson", "217-555-0142")
    assert "Testperson" not in caplog_redacted.text
    assert "555-0142" not in caplog_redacted.text


def test_log_file_redacted(freemyid_env):
    root = logging.getLogger()
    before = list(root.handlers)
    logging_setup.setup()
    try:
        register_pii("Testperson")
        logging.getLogger("t").info("listing for Jane Testperson jane.testperson@example.com")
        for h in root.handlers:
            h.flush()
        text = (freemyid_env / "logs" / "freemyid.log").read_text()
        assert "listing for" in text and "Testperson" not in text and "@example" not in text
    finally:
        for h in list(root.handlers):
            if h not in before:
                root.removeHandler(h)
                h.close()


# ---- SEC-04 regressions ----

def test_traceback_redacted(caplog_redacted):
    register_pii("Testperson")
    try:
        raise ValueError("bad value Jane Testperson")
    except ValueError:
        logging.getLogger("t").exception("failed")
    text = "\n".join(caplog_redacted.handler.format(r) for r in caplog_redacted.records)
    assert "Testperson" not in text


@pytest.mark.parametrize("variant", ["Jane+Testperson", "Jane%20Testperson", "jane_testperson"])
def test_separator_variants(variant):
    register_pii("Jane Testperson")
    assert "testperson" not in redact(f"url ?q={variant}").lower()


@pytest.mark.parametrize("dob", ["1980-04-01", "04/01/1980"])
def test_dob_backstop(dob):
    assert dob not in redact(f"born {dob}")


def test_store_registers_profile_pii(store, profile):
    store.save_profile(profile)
    store.get_profile(profile.id)
    assert "Testperson" not in redact("Jane Q Testperson lives at 742 Evergreen Terrace")
    assert "Evergreen" not in redact("742 Evergreen Terrace")


# ---- v1: Assisted copy_fields values must never reach logs ----

def test_copy_fields_values_never_logged(store, profile, caplog_redacted):
    from freemyid.models import Todo, TodoKind
    store.save_profile(profile)          # registers profile PII
    t = Todo(profile_id=profile.id, broker_id="fakepeople", kind=TodoKind.ASSISTED_OPT_OUT,
             title="Remove your listing",
             copy_fields={"Full name": "Jane Q Testperson",
                          "Address": "742 Evergreen Terrace, Springfield, IL 62704",
                          "Phone": "217-555-0142", "Email": "jane.testperson@example.com",
                          "Birth date": "04/01/1980"})
    store.save_todo(t)
    log = logging.getLogger("freemyid.engine.test")
    log.info("todo %s", t)                      # careless: whole model
    log.info("fields %r", store.list_todos(profile.id)[0].copy_fields)
    log.warning("dump %s", t.model_dump_json())
    for v in ("Testperson", "Evergreen", "Springfield", "62704", "555-0142",
              "jane.testperson", "1980"):
        assert v not in caplog_redacted.text, v


def test_copy_fields_hidden_from_repr():
    from freemyid.models import Todo, TodoKind
    t = Todo(profile_id=PID, kind=TodoKind.ASSISTED_OPT_OUT, title="t",
             copy_fields={"Name": "Unregistered Alias"})
    assert "Unregistered Alias" not in repr(t) and "Unregistered Alias" not in str(t)
