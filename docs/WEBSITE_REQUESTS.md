# Website request queue

How the marketing (brand-marketing), art (graphic-designer) and web (web-developer) agents hand work to each other. The orchestrator settles any disagreement.

- **brand-marketing** adds requests. **graphic-designer** handles `art:` items. **web-developer** builds the rest and sets the status.
- One row per small, buildable change. Copy goes in the row, ready to paste. Any new factual claim carries a source link or `needs-verify` (broker-researcher checks it first; web-developer won't publish unsourced claims).
- Status: `open` → `in-progress` → `done <commit>` | `rejected (<reason>)` | `blocked (<what>)`.

| ID | Page | Request and why | Copy / asset | Priority | Owner | Status |
|---|---|---|---|---|---|---|
| WR-1 | all | `art:` proposals for the logo/wordmark (2–3 directions) | brand/logo/options.html | P2 | graphic-designer | open |
| WR-2 | all | `art:` Open Graph share image 1200×630 for Facebook link previews (the audience arrives from Facebook) | brand/social/og-default.png | P1 | graphic-designer | open |
| WR-3 | index | Conversion review of the new landing page: section order, CTA wording, objections answered. Output new WR rows. | n/a | P1 | brand-marketing | open |
