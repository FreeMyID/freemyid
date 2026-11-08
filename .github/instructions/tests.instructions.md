---
applyTo: "tests/**"
---

- Fake people and data only ("Pat Testperson, Springfield IL"); never real names, addresses, emails or phones.
- No network: no real broker sites, no real mail servers. Use fixtures, fakes and `src/freemyid/engine/_dev/`.
- Browser tests reuse the existing Playwright helpers in the test suite and run offline against the built site
  or a local test server.
- Never weaken an existing assertion to make a test pass. A real bug gets a strict xfail with a reason and a
  note under "Questions for the owner".
- Website tests (`tests/test_web_*`) need a fresh build: `cd web && pnpm build`.
