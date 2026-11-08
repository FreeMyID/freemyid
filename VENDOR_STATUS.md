## Done

- Corrected the Proton Mail security-code recovery citation and added the scoped plain-language explanation.

## Next

- Ready for owner review.

## Questions for the owner

- None.

## How to test

- `sed -n '745,753p' src/freemyid/wizard/server.py` — verified the cited recovery message and question.
- `git diff --check` — passed.
