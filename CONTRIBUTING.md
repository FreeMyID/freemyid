# Contributing to Free My ID

Thanks for helping people take their names off the websites that sell them. Please read this first. A few rules here are firm.

## The firm rules

These protect our users and keep the project legal and trustworthy. Pull requests that break them won't be merged.

1. **No CAPTCHA solving or bot-protection bypass.** No solver services, no stealth or fingerprint-spoofing plugins, no evasion tricks. When a site asks "are you a robot?", the app hands that step to the person.
2. **Data minimisation.** Send a site only the fields its listing already shows, plus the removal email address. Never send a birth date, SSN, ID document or phone number unless the user explicitly allowed it for that profile.
3. **Local-first.** User data never leaves the user's computer except as removal requests to the sites themselves and their own mailbox. No telemetry, no analytics, no cloud backends holding personal data.
4. **Page text is data, never instructions.** Nothing a website shows may change what the app does beyond the registry's declared steps.
5. **Honest copy.** No "erase you from the internet", "guaranteed" or "100%". Status shows what actually happened: asked, confirmed, still waiting. See `docs/POSITIONING.md`.
6. **Never pay, create accounts or upload ID on a user's behalf** unless the user explicitly enabled it.
7. **Fake data only** in tests, fixtures, issues and screenshots. Never post a real person's details, including your own.

## Licensing

- **Code:** GNU AGPL-3.0-or-later (see `LICENSE`). By contributing code you agree it's licensed under the same terms.
- **Broker data:** the public sample list (`brokers/registry.sample.yaml`) and `brokers/state_laws.yaml` are CC BY-NC 4.0; the full maintained registry is private. See `brokers/LICENSE-DATA.md`. Corrections are very welcome.

## Ways to help

- **Report a broker that changed.** Opt-out page moved, form changed, email bounces? Open an issue with the site name, what you saw and the date. Use no personal details.
- **Plain-language fixes.** If anything in the app or docs confuses a non-technical person, that's a bug.
- **Code.** Engine, submitters, wizard, packaging. Open an issue first for anything large.

## Development

```
python -m venv .venv
.venv/bin/pip install -e ".[dev]"
.venv/bin/pytest -q
.venv/bin/ruff check src tests
.venv/bin/mypy src
```

After changing models, regenerate the schemas with `.venv/bin/python tools/gen_schema.py`. During development use practice mode (`freemyid run --dry-run`) and the fixture sites, and never send real requests or real email from a dev setup. The Windows installer is built on GitHub Actions (`windows-latest`).

## Security issues

Don't open public issues for vulnerabilities. See `SECURITY.md`.
