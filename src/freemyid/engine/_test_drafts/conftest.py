"""Draft-test glue: reuse the shared fixtures from tests/conftest.py (qa-security owns it).

Run from the repo root with `.venv/bin/python -m pytest src/freemyid/engine/_test_drafts`.
When qa adopts these files into tests/, delete this conftest.
"""
from tests.conftest import (  # noqa: F401
    fake_registry,
    freemyid_env,
    make_profile,
    memkeyring,
    profile,
    store,
)
