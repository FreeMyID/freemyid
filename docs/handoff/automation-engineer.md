# automation-engineer handoff

## Done (import clean, ruff clean)
- engine/matcher.py: Candidate, score() (CONFIRMED = name + >=2 signals), shown_fields, score_all
- engine/browser.py: BrowserManager (system channel -> bundled chromium, per-broker allowlist
  route, honest UA, delays/rate limit/retries), detect_challenge() pure fn, ChallengeEncountered
- engine/handoff.py: QueuedHandoff (non-blocking), InteractiveHandoff (headed window, Enter or
  dashboard done; no tty/display falls back to queued), get_notifier fallback, confirm_review,
  mark_manual_submitted
- engine/letters.py: render(), split_subject, choose_template, letter_vars (data-minimized)

## In progress
- templates/*.txt.j2 (7 templates)

## Next steps (in order)
1. templates -> 2. outbox.py + mail.py -> 3. submitters/base.py, web_form, email, postal, phone,
   account_required -> 4. engine/plugins.py -> 5. engine/runner.py -> 6. _dev fixture registry +
   fixture server + devrun -> 7. per-broker parsers (10) + tests/fixtures/<id>/search.html ->
   8. _test_drafts tests

## Notes
- New dep installed into .venv: beautifulsoup4 (CR for pyproject).
- Bundled Playwright chromium-1208 already in ~/.cache/ms-playwright; no system Chrome.
