# Home-page A/B/C test: three design directions

Status (2026-11-21): **built, not live.** The arms deploy with the site but nothing links to them, and the edge
worker that sends visitors to them ships switched off. Turning it on needs the owner's OK on two things below
(privacy wording, then the deploy). Branch `inhouse/design-directions`.

## What is being tested

Four arms, equal shares by default:

| Arm | Look | Home page |
|---|---|---|
| `control` | the current site (system fonts, navy, flag rule) | `pages/index.astro`, unchanged |
| `heritage` | founding-document Americana: parchment, Libre Caslon, double gold rules, the seal | `components/home/HomeHeritage.astro` |
| `frontier` | workwear ledger: canvas, denim header, Zilla Slab + Oswald, stitched seams, barn-star patch | `components/home/HomeFrontier.astro` |
| `glory` | Old Glory Modern: white, flag-blue hero with a star field, stripes, Public Sans, shield mark | `components/home/HomeGlory.astro` |

Source designs: `FreeMyID-Design-Directions` (Figma `vZTYWejWbGgEaj50PW8Ig5`, zip of Nov 2026). The arms differ in
**design only**: every arm has the same Download wording ("Download Free My ID", "Free for Windows 10 and 11"), the same
trust panel (WO-162 short form), the same practice-mode / version / SmartScreen lines (`HomeFinePrint.astro`) and the
same sourced facts. `tests/test_web_ab_arms.py` enforces that, so a winner is a design win, not a copy win.

Every other page in an arm is the normal page in the direction's colours, fonts, header, footer and logo
(`styles/directions/<name>.css`, colour overrides in `site_src/tokens.yaml` `directions:`; all 60 contrast pairs are
checked for every direction in light and dark by `scripts/gen-tokens.mjs`).

Copy changes from the mockups (copy rules win over the mockup):
- Trust panel: the WO-162 short form ("...Social Security number or bank or card details, and never charges you."),
  not the older `docs/BRAND.md` line the mockups used.
- Frontier "That post didn't stop anyone. This does." -> "...didn't **reach** anyone. This does." ("stops" promises
  an outcome).
- Frontier "Is it safe?": the `/safety/#local` wording. The mockup's "go only to the sites you ask to remove you" is
  banned (`tests/test_web_absolute_claims.py`: practice mode still looks people up).
- Heritage facts: added the required caveat "It does not stop overseas access or government data purchases."
- Demo cards say "example" and carry "Example with made-up data." (D7). The mockups' "Help a parent" nav label stays
  "For families" so the nav is the same in every arm.

## How it works

```
visitor -> freemyid.org/ -> worker picks an arm at random -> serves the HTML of /x/<arm>/ at "/" (no-store)
           every link in that page points into /x/<arm>/...  -> the visitor stays in that design, no cookie needed
           Download button -> /x/<arm>/get/windows/ -> worker counts "download" for the arm -> 302 to /get/windows
```

- **Build** (`web/scripts/build-arms.mjs`, `pnpm build:ab`, run by `pages.yml` after `pnpm build`): four extra full
  copies of the site with base `/x/<arm>/` in `web/dist/x/<arm>/`. Every arm page is `noindex` with its canonical on
  the normal URL, and the arms are not in the sitemap, so search engines see one site. About 4 x 3 MB on Pages.
- **Worker** (`worker/ab-test/`, routes `freemyid.org/` and `freemyid.org/x/*`): bots and link previews always get
  the normal home page; HEAD requests are never counted; if an arm is missing it serves the normal home page.
- **Without the worker** nothing changes for anyone: `/` is the normal site, and an arm's `get/windows/` page forwards
  to the normal download.

## What is counted (and what is not)

Workers Analytics Engine dataset `freemyid_ab`, one data point per event: `arm`, `event` (`assign` = a visit to "/"
drew this arm, `view` = an arm page was opened, `download` = a Download button was clicked) and the page path. That
is all. No IP address, no user agent, no referrer, no location, no cookie, no identifier of any kind, and worker
logs are off (`observability.enabled: false`). The test can't follow a person: a refresh draws again.

Free plan: 100,000 data points written and 10,000 queries a day; Cloudflare's pricing page says Analytics Engine is
not billed at present (checked 2026-11-21). Workers Free allows 100,000 requests a day; the worker only runs on "/"
and "/x/*".

## Before switching it on (owner)

1. **Privacy wording (Tier 3: privacy-policy meaning).** The site promises "No cookies, no trackers, no analytics"
   (`/safety/#this-website`) and the footer says "No tracking, no cookies." Aggregate counting is still a change, so
   say so. Proposed text for `/safety/#this-website`, to ship in the same deploy that turns the worker on:

   > We are trying out new designs for this site. When you open the home page, our server picks one of four designs at
   > random. To learn which one helps people most, it counts how many times each design was shown and how many
   > downloads started from it. Those are plain totals: no cookies, no IP address, nothing about your device and
   > nothing that could tell us it was you. There are still no trackers, no analytics scripts and nothing from other
   > companies on this site.

   The footer line can stay ("No tracking, no cookies"): nothing about a person is recorded.
2. **Deploy (Tier 2, rollback below).** The repo now has a Wrangler config, so use Wrangler (not `cf`):
   `cd worker/ab-test && npx wrangler deploy` with an account that can edit Workers on freemyid.org, then set
   `AB_ENABLED` to `"1"` in `wrangler.jsonc` and deploy again. Check: `curl -sI https://freemyid.org/` shows
   `cache-control: no-store`; `/x/glory/` loads; a download from an arm reaches GitHub.
3. **Off / rollback:** `AB_ENABLED: "0"` and deploy (instant, everything passes through), or delete the two routes or
   the worker. The arm copies on Pages are harmless without the worker.

## Reading the results

`CF_ACCOUNT_ID=<id> python3 tools/ab_report.py --days 30` (token in `~/.config/freemyid/cf_token` with Account >
Account Analytics > Read; the current token may need that permission added). It prints visits, downloads, the
download rate with a 95% interval per arm, and each design against the control (two-proportion z-test). It names a
winner only when every arm has at least 400 visits and the design beats the control at p < 0.05 / 3 (three designs
compared with one control).

How long: at a 5% download rate, telling a 30% better design (5% -> 6.5%) from the control with 80% power at that
threshold takes about 5,000 visits per arm, so about 20,000 home-page visits in all. A bigger difference shows sooner.
Change the split with `AB_WEIGHTS` (for example drop a clear loser to `0`).

When there is a winner: make its direction the normal site (render its home in `pages/index.astro`, move its
colours into `site_src/tokens.yaml` `color:`, load its stylesheet for the normal build), switch the worker off, and
remove the arms from `pages.yml`.

## Files

| Path | What |
|---|---|
| `web/astro.config.mjs` | `FMID_ARM` -> base `/x/<arm>/`, `dist-arms/<arm>`, `@direction` stylesheet alias |
| `web/src/lib/arm.ts` | `ARM`, `DIRECTION`, `IN_TEST` for components |
| `web/src/styles/directions/` | `_shared.css`, one stylesheet per direction, generated `*.tokens.css`, `none.css` |
| `web/src/components/home/` | the three direction homes and the shared fine print |
| `web/src/fonts/` | self-hosted OFL fonts (README lists them) |
| `web/scripts/build-arms.mjs` | builds the arms into `dist/x/` |
| `worker/ab-test/` | the edge worker and its Wrangler config |
| `tools/ab_report.py` | results |
| `tests/test_ab_test.py`, `tests/test_web_ab_arms.py` | worker, report and built-arm checks |
