# Website quality pass (2026-11-06)

Method: Playwright at 360 and 1280 px, light and dark, on 10 pages (home, download, how-it-works, privacy, faq,
i-do-not-consent, guides index, spokeo, equifax, california-drop). Automated checks on every page: horizontal
scroll, heading order, h1 count, img alt, tap size. Screenshots: scratchpad/quality/. Full-page 360 shots
were downscaled too far to judge fine detail; layout verdicts rest on the DOM checks plus the 1280 shot.

Clean: no horizontal scroll at 360 or 1280 in either theme; one h1 per page; no skipped heading levels;
no img without alt; all internal links on spokeo resolve; no "guaranteed", "100%", "identity theft" or
"hackers" copy; state-law qualifier present on home, FAQ and the "I do not consent" page; build already checks
the token pairs, and I found only one extra pair under 7:1 (Q-4).

| ID | Page | Sev | Problem | Suggested fix | File |
|---|---|---|---|---|---|
| Q-1 | download | P2 | Primary button points at `releases/latest/download/FreeMyIDSetup.exe` in a repo that is still private and has no release. An older reader clicks and gets a 404. The page admits "version, size and checksum will show here" so the SHA256 block is empty. | Launch-day gate: do not publish the site until a release exists. Until then show the button as disabled text ("Coming soon") or link to the how-it-works page. | site_src/pages download |
| Q-2 | home | P2 | Hero kicker "That post didn't stop anyone. This does." can read as mocking people who shared the "I do not consent" post (POSITIONING: never mock). | Warmer: "That post was a good instinct. This sends it to the right place." (matches the section lower down). | site_src/ home |
| Q-3 | home | P3 | Hero lead opens "Right now, websites are selling your home address ... scammers and stalkers included." Sourced to CFPB 2024, but it is the most fear-toned sentence on the site and "Right now" adds urgency. | Drop "Right now,"; keep the cited fact lower on the page. | home hero |
| Q-4 | all (CSS) | P3 | `link` on `surface-strong` is 6.45:1 in light theme (below the 7:1 body target, above AA). Not in the build's pair list. | Add pair `[link, surface-strong, 7]` to tokens.yaml and darken `link` slightly, or avoid links on chips. | site_src/tokens.yaml |
| Q-5 | home, faq, privacy, i-do-not-consent, guides | P3 | Inline text links are 23-27 px tall (e.g. "See all questions", "Share this page on Facebook", "CC BY-NC 4.0"). Inline links in sentences are exempt from WCAG 2.2 target size, but the stand-alone ones ("See all questions", "See all opt-out guides", "Share this page on Facebook") are not inside a sentence. | Make standalone links `.btn--small` or give them `min-block-size: var(--tap)` and padding. | site_src/css |
| Q-6 | home | P3 | "Erase you from the whole internet. Nobody honest can promise that." appears in the does-not list. It is a denial, so it is allowed, but the banned phrase appears verbatim in page text; a copy grep for "erase" will trip. | Rephrase: "Remove you from every corner of the internet." | home |
| Q-7 | home, download | P3 | Footer "Source code on GitHub" and release links go to a private repo (already a LAUNCH_CHECKLIST item). | Re-check at launch. | footer partial |
| Q-8 | download | P3 | SmartScreen step 2 mockup is a drawing, labelled as such. Good. But the page says "Click Install ... walks you through six simple screens" while PLAN_V1 is the source; confirm the count stays six. | Verify with wizard-packager before launch. | download |

Counts: P1 0, P2 2, P3 6.
