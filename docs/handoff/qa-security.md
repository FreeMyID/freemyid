# qa-security handoff
Done: scaffold review (docs/SECURITY_REVIEW.md, verdict BLOCK); conftest, fixtures, test_models, test_state,
test_crypto, test_storage (findings as strict xfails; verified each fails for the stated reason via --runxfail).
In progress: test_redaction, test_netpolicy, test_consent_cli, test_registry.
Next: pytest + ruff; tools/registry_health.py (--dry); adopt wizard/_test_drafts; review engine/*, wizard/*,
templates -> new section in SECURITY_REVIEW.md.
Note: orchestrator is fixing SEC-01..05 in contract files; on XPASS just drop the marker.
