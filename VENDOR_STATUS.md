# Done

- Applied the four verified, source-backed corrections in `docs/USER_GUIDE.md`: Proton Bridge trust wording, the status-table marker, permission instructions, and the Emails queue label.
- Left the line-7 banner, review-match UI wording, and Google, Proton plan, and DROP claims unchanged.

# Next

- Ready for owner review.

# Questions for the owner

- None.

# How to test

- `python -c "from pathlib import Path; text = Path('docs/USER_GUIDE.md').read_text(); checks = [\"Free My ID shows you the mail app's **security code**\" in text, 'exact chip labels and colors' not in text, 'open **Settings**, select the person, tick the permission, and click **Save**' in text, 'open **Emails**, read the email, and click **Approve and send**' in text]; assert all(checks); print('PASS: four guide corrections')"` — PASS.
- `git diff --check` — PASS.
