# WO-204R — integrated website re-audit

Date: 2026-11-08. Authorization: CLAUDE-046. Reviewed snapshot: owner-prepared `.vendor-wt/wo-204r`, based on the owner's reported combined main `f14c92f`; the prebuilt `web/dist` was supplied by Morgan. Nora did not rebuild. The original WO-204 report and embedded runners are retained below; the audit runner code is unchanged and its raw output has been refreshed against this worktree.

## Decision and delta

**No P1 or P2 findings remain in the unchanged re-audit runner.** Initial findings A01–A11 are not reproduced after the merged repairs. The download SmartScreen size/clipping regression passed independently at all four specified widths (WO-210 test: 4 passed). A12 remains as an owner-accepted P3 classification: the eyebrow labels measure 6.919:1, above the 4.5:1 other-text threshold. No page, shared styles, or assets were changed during this read-only audit.

| Initial finding | WO-204R result |
| --- | --- |
| A01–A04 CTA and brand-band contrast | Not reproduced in 196 browser states. |
| A05–A06, A09–A11 link targets | Not reproduced; no undersized target reported. |
| A07–A08 safety/families hero gutters | Not reproduced; no H1 gutter defect reported. |
| A12 eyebrow classification | Retained as owner-accepted P3; five labels at 6.919:1 in light theme pass the 4.5:1 other-text threshold. |
| A13 SmartScreen illustration labels | WO-210 built-output browser regression: 4 passed at 320/360/390/1280px; labels >=20px, within figures, no page overflow. |

## Re-audit evidence

- Unchanged embedded audit runner: 14 routes × 2 themes × 7 effective width/scale cases = 196 browser states, plus 14 normal-motion checks. No new P1/P2 contrast, body-text, target-size, gutter, overflow, broken-image, or animation issue was emitted.
- Keyboard traversal reached the first content control with a visible 3px solid focus outline; sampled visible controls were reachable in DOM order and FAQ disclosures opened with Enter.
- Built-output scan: 67 HTML files; no inline `style=` attributes, duplicate IDs, or CSP hash differences against the compared main `web/dist`. The existing external `CopyHash` script on download is the only executable script reported.
- `pnpm check` from `web/`: passed, 67 HTML files / 61 indexable. `PYTHONPATH=src ../../.venv/bin/python tools/site_check.py web/dist`: passed, 67 HTML pages.
- `PYTHONPATH=src FREEMYID_REQUIRE_WEB_DIST=1 ../../.venv/bin/pytest -q tests/codex/test_cx_audit_download_followup.py`: 4 passed.
- The screenshot overview runner below was retained unchanged but not rerun; the re-audit evidence is based on the unchanged measurement runner, keyboard interaction, static output checks, site checks, and WO-210's focused built-output browser test.
- Windows display scaling and browser chrome zoom remain emulated, not checked on physical Windows hardware. The full owner leak scan, exact-final-commit suite, and publication decision remain Morgan's gates. This report records zero P1/P2 in the re-audit and is not itself authorization to publish.

---

## Original WO-204 report (historical baseline)

Date: 2026-11-08. Authorization: CLAUDE-041. Reviewed snapshot: owner-prepared `.vendor-wt/wo-204` containing all ten merged refresh WOs. No git operations were used; a commit ID was not independently established. The findings below are the initial baseline and are superseded by the WO-204R delta above.

### Initial decision and severity

P1 = materially unreadable primary action; address before accepting the refresh. P2 = clear target-size/layout contract failure; correct in a separately approved work order. P3 = a visual/readability observation requiring an owner classification or exception. No fixes, tests, assets or styling were changed in this audit worktree.

The first five pages still have defects that their focused structural tests did not catch. The last five pages and sampled guide articles had no defects in the measured checks. Passing the existing tests does not establish D6 compliance for all page elements.

### Findings, ranked by severity (initial audit)

| ID | Severity | Route and exact element | Evidence and reproduction | Suggested disposition (not implemented) |
| --- | --- | --- | --- | --- |
| A01 | P1 | `/` — price-card `Download Free My ID` (`web/src/pages/index.astro:247`), helpers secondary CTA (`:268`) and final brand-band CTA (`:287`) | At 320/1280, both themes: a filled CTA has text contrast 1.379:1 light / 1.065:1 dark; another dark CTA 1.477:1. Hero CTA at `:58` already has the refresh class and is readable. Inspect every CTA, not only the hero. | Apply token-based page-local button ink/background treatment in all states. Preserve release logic and labels. |
| A02 | P1 | `/how-it-works/` — `.how-download a`, `web/src/pages/how-it-works/index.astro:103` | 1.379:1 light / 1.065:1 dark at every measured width, below 4.5:1. | Correct the page call site's refresh button styling. |
| A03 | P1 | `/families/` — hero and final `CtaDownload`, `web/src/pages/families/index.astro:33` and `:186` | Both CTA instances measure 1.379:1 light / 1.065:1 dark at every measured width. The screenshot overview visibly confirms the unreadable label in light mode. | Correct both page call sites and cover them with browser assertions. |
| A04 | P1 | `/` — final brand-band text link `How you can check our work`, `web/src/pages/index.astro:286` | 1.471:1 in light theme across all seven width/scale cases, below 4.5:1. | Use existing band ink tokens for ordinary links in that section. |
| A05 | P2 | `/` — ordinary content links, including `See all questions`, `Browse the guides`, support, guide, sample-report and verification links | `See all questions` is 196.78 × 34px at 320px and all other cases. Many single-line links are 34px high at desktop. Full affected labels/cases are in measurements below. Requirement is >=44px. | Size every relevant link target, including opened FAQ answers; verify wrapped links remain readable and do not overlap. |
| A06 | P2 | `/how-it-works/` — breadcrumb `Home` and `free opt-out guides` | Breadcrumb 71.14 × 40px; guide link 225.53 × 34px, all measured widths/themes. | Page-scoped target sizing without changing shared chrome. |
| A07 | P2 | `/safety/` — hero H1 (`#site-refresh-hero-title`) and lead | H1 left edge is exactly 0 CSS px at 320/360/640/768/1024/1280 in both themes. Breadcrumb and later sections have gutters. Screenshot overview confirms the hero copy touches the left edge. No document overflow is required to reproduce it. | Put the existing hero inside a page-local approved wrap. |
| A08 | P2 | `/families/` — hero H1 (`#site-refresh-hero-title`) and lead | Same 0px left edge across every measured width/theme; hero is outside its breadcrumb wrap. | Restore hero gutters at the page call site. |
| A09 | P2 | `/safety/` — `our download page`, `Where developers find the code` | First link 228.86 × 34px at 768px and desktop/scaling cases; second 372.91 × 34px at 1280px. | Enforce >=44px targets while preserving text and hrefs. |
| A10 | P2 | `/download/` — `Here's a one-page guide for them.` (`web/src/pages/download/index.astro:72`) and `SHA256 code, under “For helpers” above` (`:131`) | 400.73 × 34px and 472.61 × 34px respectively at single-line layouts, both themes. | Page-scoped target sizing; preserve direct installer/release/fingerprint logic. |
| A11 | P2 | `/families/` — `See the full list`, `See the answer on our Questions page.`, `See it with pictures.` | First 170.86 × 34px at every width; remaining links 34px high in single-line desktop layouts, both themes. | Page-scoped target sizing including answer links. |
| A12 | P3 / owner classification | `/`, `/how-it-works/`, `/safety/` — red eyebrow labels `Our promises`, `A clear process`, `Your choices`, `Your choice`, `About this site` | 6.919:1 in light mode. These are `<p>` labels; they meet the 4.5:1 **other-text** threshold but fall just below 7:1 if classified as body text. | Owner classifies eyebrows as other text, or use an existing token meeting 7:1. Do not change global tokens in a vendor repair. |
| A13 | P3 / owner exception | `/download/` — `Don't run` and `Run anyway` spans inside the illustrative SmartScreen drawing | Computed size 17px. Surrounding instructions are >=20px. These spans imitate Windows UI inside `role=img`, not interactive site controls; no 44px control failure is claimed for them. Source: `web/src/components/SmartScreen.astro:18`. | Decide whether the approved drawing is an intentional illustration exception or should receive a page-local >=20px override. Shared SmartScreen edits require separate scope. |

The common CTA failure follows from the scoped `.site-refresh :where(a)` link color winning over the legacy button utility color. The last batch's pages already apply the stronger refresh button class. This is an inference from the measured colors and checked-in selectors; repairs must remeasure the actual normal/hover/focus states rather than merely assert a class name.

### Page-by-page result (initial audit)

| Page/work order | Result | Details |
| --- | --- | --- |
| Home / WO-200 | Repairs required | A01, A04, A05; A12 classification. Hero product image has explicit dimensions and `Example with made-up data`. |
| How it works / WO-201 | Repairs required | A02, A06; A12 classification. Daily-check sentence retains PC-on/signed-in qualifier. |
| Safety / WO-205 | Repairs required | A07, A09; A12 classification. Privacy/report scope qualifiers remain present. |
| Download / WO-206 | Repairs required | A10; A13 drawing exception. Direct installer link retained as authorized. Existing checksum module remains. |
| Families / WO-202 | Repairs required | A03, A08, A11. Daily-check sentence retains qualifier. Existing half-hour guidance is approved copy, not a newly introduced timed claim. |
| FAQ / WO-207 | No measured defect | Native answers open by keyboard; all opened answer controls included. |
| Guides index/template/standalone / WO-203 | No measured defect | Browser samples: index, Spokeo, BeenVerified, parent guide and phone guide. Build/site checks traverse all generated guide pages; other articles are not individually claimed as manually inspected. |
| Developer hub / WO-197 | No measured defect | Platform readiness and qualified daily-check wording retained. |
| CLI / WO-198 | No measured defect | Reference cards and source locations readable; code overflow confined to containers. |
| Config / WO-199 | No measured defect | Table headers and keyboard-focusable scroll region retained. |

### Checks and limits (initial audit)

Commands run from `.vendor-wt/wo-204`:

- `(cd web && pnpm build && pnpm check)` — PASS: 62 generated routes; CSP tightened across 67 HTML documents; checker reports 67 HTML / 61 indexable, OK. Token generator reports 39 configured contrast pairs passing in both themes. This token result does not cover incorrect token combinations on individual elements, as A01–A04 demonstrate. Existing Shiki CSP configuration warning emitted; final built-output checks pass.
- `PYTHONPATH=src ../../.venv/bin/python tools/site_check.py web/dist` — PASS: 67 HTML pages, OK. Local links/assets/fragments checked. **Private-host fingerprint inventory is absent in this worktree**, so this run is not independent proof of Morgan's full leak-scan result. Owner's CLAUDE-041 reports the integrated main leak scan passed; retain that distinction.
- Embedded offline audit runner below — 196 route/theme/width states (14 routes × 2 themes × 7 widths/scales), plus 14 normal-motion checks. Width/scale pairs: 320/1, 360/1, 768/1, 1280/1, 1024/1.25, 1280/1.5, 640/2. Chromium outside-sandbox execution was approved because browser launch is blocked inside the sandbox. All browser resource requests use the existing test route handler and are fulfilled from local build files or aborted. JavaScript disabled for layout/keyboard checks.
- First content control reached with real Tab at 320 in both themes and showed a 3px solid visible focus outline on every sampled route. After opening disclosures, visible content controls traversed in DOM order with Tab at 320 and 1280 (including 1.5x); no unreachable control was found. Initial control focus for the complete traversal is reset programmatically; this does not claim an entire end-to-end screen-reader audit. All summaries open with Enter. Text selection/scrolling in every individual code block was not manually operated.
- No horizontal document overflow, broken/alt-less images, duplicate IDs or inline `style=` attributes found in the measured scope/static output. No CSS animations detected in the refreshed content in reduced-motion states or the normal-motion desktop samples. Hover-only behavior was not comprehensively exercised.
- All 67 generated documents' CSP hash lists match the already integrated main build. The only executable script found is the existing external CopyHash module on download. No new executable script was introduced by this audit. **A pre-refresh CSP baseline is unavailable without owner-provided artifacts**, so no independent before-refresh hash diff is claimed. Owner should retain that baseline check for release acceptance.
- Visually inspected in-memory screenshot overviews of all ten page tops at 1280/light and 320/dark. They confirm missing hero gutters and weak family CTA text. These overview images are not a full-page pixel review at every size. The screenshot runner below reproduces the views; no screenshot files were added to the worktree.
- Windows 125%/150% display settings and browser chrome 200% zoom were **emulated** through effective CSS widths and device scale, not operated on a real Windows desktop. Screen-reader speech, real Windows scaling, real installer behavior, forced-colors mode, printing and external destinations are not verified here. No external URLs were opened.
- Morgan reports all 279 Codex tests passing on integrated main in CLAUDE-041. This audit did not repeat the full suite or claim that result as an independent run. A full test run on the owner's exact final commit remains a release gate after CodeRabbit fixes and approved repairs.

## Copy / D8 review

Applied CLAUDE-040's distinction: D8 gates **new** claims; preserved, source-cited approved copy remains accepted. No new unsupported refresh claim was identified in this local review; this is not a fresh external fact check or a review of protected implementation.

| Route(s) | Claim families checked | Local provenance / disposition |
| --- | --- | --- |
| Home | Local operation, six screens, daily checks, printable report, comparison, free/no-account/no-card | Source comments in home; `docs/WEBSITE_REDESIGN.md` D8/D9; `brokers/SOURCES.md` “Website claims: comparison (R5)”; approved existing copy under CLAUDE-040. Once-a-day occurrences include the PC-on/signed-in qualifier. Recheck time-sensitive comparison source notes before launch as the source file requests; no prices independently verified. |
| How it works | Approved request methods, practice mode, rechecks | Page source comments cite PLAN_V1, USER_GUIDE and positioning; existing approved copy, not runtime-verified in this audit. Daily sentence is qualified. |
| Safety | Encrypted storage, limited network/recipient scope, printable-report caveat, no forms/tracking, limitations | Page source comments; D8 and SEC-43 report ruling in WEBSITE_REDESIGN. Approved statements preserved; no crypto/network/mail code accessed for this audit. |
| Download | Version/size/fingerprint and Windows warning/install guidance | Public release metadata, approved page/source comments, existing SmartScreen drawing. Direct installer retained per CLAUDE-040. No external release, certificate status or Windows action freshly verified. |
| Families | Permission, local storage, half-hour setup guidance, daily checks | Page source comments and approved `site_src/templates/pages/families.html:7` cite HELPER_GUIDE. Existing half-hour/notice-example copy falls under CLAUDE-040 acceptance; it is not flagged merely because D8's new-claim list is narrower. Daily sentence qualified. |
| FAQ | Privacy, legal limits, platform and removal expectations | Same `site_src/data/faq.yaml` with source notes; release-dependent branches rendered. Accepted existing answers; no new facts added. |
| Guides (all generated routes) | Site steps, citations, verification dates, re-listing caveats | Public sample registry/guides and source attribution retained; standalone pages retain source comments. Existing approvals accepted. External live steps not rechecked. |
| Developers, CLI, config | Platform readiness, command contract, schema fields and fake examples | Page source comments, public command JSON, docs/CLI and versioned schema links. These are existing approved reference facts; no protected schema or product behavior was changed. Hub daily sentence qualified. |

**Owner clarification, not a source defect assertion:** CLAUDE-040 says the shared CTA on other pages “points here” (download), while D5 and `CtaDownload.astro` explicitly send a published release CTA directly to the installer. The integrated pages retain the D5 behavior. Confirm the intended wording before any repair changes hrefs; proposed repairs preserve all destinations.

## Rollback and staging-system acceptance

Owner tooling performs all reverts. Tracker issue numbers in previous handoffs are not assumed to be PR numbers; owner must map WOs to actual merge/revert commits. No revert was performed.

1. A single page WO can be reverted independently while retaining WO-195's foundation and WO-196 art for remaining consumers.
2. For full rollback, reverse the page sequence: **WO-199 → WO-198 → WO-197 → WO-203 → WO-207 → WO-202 → WO-206 → WO-205 → WO-201 → WO-200**. Independent page reverts may be reordered if the owner confirms no later dependencies. WO-203 reverts its index, shared template and both standalone guides together.
3. **WO-195 must follow every dependent page revert**, because all refreshed pages import its stylesheet/components. Do not remove that foundation while page imports remain.
4. **WO-196 art can be removed separately only after its last consuming page has been reverted** (notably how-it-works, safety and families). Home's real screenshot belongs to WO-200, not WO-196. After all pages revert, 195 and 196 are independent removals.
5. After each owner revert, rebuild, run both site checkers and verify local links/assets/fragments. No app/database migration is involved.

The staging namespace still exists by design: `web/src/styles/site-refresh.css`, page imports and `.site-refresh` wrappers. `web/src/components/site-refresh/README.md:5` requires in-house fold-back into the main design system and namespace removal **after WO-204 passes**. That operation has not occurred and cannot be signed off as complete here. Audit acceptance is currently held, so the pending fold-back is not itself a new defect. In-house should record its follow-up and confirm zero remaining namespace imports/selectors after migration, with fresh visual and CSP checks. Codex has not changed global styles or tokens.

## Owner handoff

Propose four non-overlapping repair scopes for batch approval: home; how-it-works; safety+families; download. Preserve approved copy, all IDs/hrefs, release behavior and shared components. P3 eyebrow/drawing classifications are owner decisions. No implementation starts without the owner's work orders and prepared worktrees. Also retain owner-controlled CodeRabbit fixes, full-suite/exact-commit validation and full leak/CSP baseline checks before publication.

## Reproduction

The following report-embedded scripts are diagnostic tools, not new tests or product code. Run from the audit worktree using the installed environment; no packages or external resources are fetched. The measurement runner updates only the raw section of this report. The screenshot runner returns in-memory JPEG overviews and writes no image files. Only this report and worktree status were authored in the audit branch; local ignored build artifacts are required by the prescribed checks.

## Reproducible offline audit runner

<!-- AUDIT_RUNNER -->
```python
from pathlib import Path
import json
import re
from collections import defaultdict
from playwright.sync_api import sync_playwright
from tests.test_web_home_hero_layout import BASE, ORIGIN, serve

ROUTES = ["", "how-it-works/", "safety/", "download/", "families/", "faq/", "guides/", "developers/", "developers/cli/", "developers/config/", "guides/spokeo/", "guides/beenverified/", "guides/help-a-parent-remove-their-information/", "guides/get-your-phone-number-off-people-search-sites/"]
ROOT = Path.cwd()
REPORT = ROOT / "docs/vendor/site-refresh/QA_REPORT.md"
METRICS = r"""root => {
 const visible = e => !!e.getClientRects().length && getComputedStyle(e).visibility !== 'hidden';
 const label = e => ({tag:e.tagName,id:e.id,text:(e.innerText||e.textContent||'').trim().replace(/\s+/g,' ').slice(0,110)});
 const rgb = s => (s.match(/[\d.]+/g)||[]).map(Number);
 const lum = c => c.slice(0,3).map(v => {v/=255;return v<=.04045?v/12.92:((v+.055)/1.055)**2.4}).reduce((v,n,i)=>v+n*[.2126,.7152,.0722][i],0);
 const issues = [];
 for(const e of root.querySelectorAll('h1')) {const r=e.getBoundingClientRect();if(r.left<8)issues.push({kind:'gutter',...label(e),left:r.left,right:r.right,viewport:innerWidth});}
 if(document.documentElement.scrollWidth>innerWidth+1) issues.push({kind:'overflow',width:innerWidth,scroll:document.documentElement.scrollWidth});
 for(const e of root.querySelectorAll('a,summary,button')) {
  if(!visible(e)) continue;
  const r=e.getBoundingClientRect();
  if(r.width<43.9||r.height<43.9) issues.push({kind:'target',...label(e),w:+r.width.toFixed(2),h:+r.height.toFixed(2)});
 }
 for(const e of root.querySelectorAll('*')) {
  if(!visible(e)||!Array.from(e.childNodes).some(n=>n.nodeType===3&&n.textContent.trim())||e.closest('svg,script,style,[aria-hidden=true]')) continue;
  const css=getComputedStyle(e);const size=parseFloat(css.fontSize);
  if(e.closest('p,li,td,dd,figcaption')&&!e.closest('[data-slot=badge]')&&size<19.99) issues.push({kind:'body-size',...label(e),size});
  const fg=rgb(css.color);let parent=e,bg;
  while(parent){const c=rgb(getComputedStyle(parent).backgroundColor);if(c.length===3||c[3]===1){bg=c;break;}parent=parent.parentElement;}
  if(!bg||fg.length<3)continue;
  const ratio=(Math.max(lum(fg),lum(bg))+.05)/(Math.min(lum(fg),lum(bg))+.05);
  const threshold=e.closest('h1,h2,h3,h4,a,summary,[data-slot=badge]')?4.5:7;
  if(ratio+.01<threshold) issues.push({kind:'contrast',...label(e),ratio:+ratio.toFixed(3),threshold});
 }
 for(const e of root.querySelectorAll('img')) if(visible(e)&&(!e.complete||!e.naturalWidth||!e.getAttribute('alt'))) issues.push({kind:'image',...label(e),src:e.getAttribute('src')});
 for(const e of root.querySelectorAll('*')) {const c=getComputedStyle(e);if(visible(e)&&c.animationName!=='none'&&c.animationDuration.split(',').some(v=>parseFloat(v)>0.001)) issues.push({kind:'animation',...label(e),name:c.animationName,duration:c.animationDuration});}
 return issues;
}"""

results=[]
with sync_playwright() as driver:
 browser=driver.chromium.launch(headless=True)
 for route in ROUTES:
  issues={};runs=0;keyboard=[]
  for theme in ('light','dark'):
   for width,scale in ((320,1),(360,1),(768,1),(1280,1),(1024,1.25),(1280,1.5),(640,2)):
    context=browser.new_context(viewport={'width':width,'height':1000},device_scale_factor=scale,color_scheme=theme,reduced_motion='reduce',java_script_enabled=False)
    context.route('**/*',serve)
    tab=context.new_page();response=tab.goto(ORIGIN+BASE+route,wait_until='load')
    assert response and response.status==200,(route,response.status if response else None)
    scope=tab.locator('.site-refresh');assert scope.count()==1,(route,scope.count(),tab.url,tab.title(),ROOT,serve.__module__)
    # Reach the first content control using real Tab; verify an actual visible focus outline.
    if width==320:
     target=scope.locator('a,summary,button,[tabindex="0"]').first
     for _ in range(150):
      tab.keyboard.press('Tab')
      if target.evaluate('e=>e===document.activeElement'):break
     keyboard.append({'theme':theme,'reached':target.evaluate('e=>e===document.activeElement'),'outline':target.evaluate('e=>{const c=getComputedStyle(e);return {visible:e.matches(":focus-visible"),width:c.outlineWidth,style:c.outlineStyle}}')})
    for summary in scope.locator('details > summary').all():
     summary.focus()
     if not summary.evaluate('e=>e.parentElement.open'):tab.keyboard.press('Enter')
     assert summary.evaluate('e=>e.parentElement.open'),route
    if width in (320,1280):
     controls=[e for e in scope.locator('a,summary,button,[tabindex="0"]').all() if e.is_visible()]
     traversed=0;unreachable=[]
     if controls:
      controls[0].focus()
      for index,control in enumerate(controls):
       if index:tab.keyboard.press('Tab')
       if not control.evaluate('e=>e===document.activeElement'):
        unreachable.append(control.inner_text()[:80]);break
       traversed+=1
     keyboard.append({'theme':theme,'width':width,'traversed':traversed,'unreachable':unreachable})
    for issue in scope.evaluate(METRICS):
     key=json.dumps({k:v for k,v in issue.items() if k not in ('w','h','width','scroll')},sort_keys=True)
     if key not in issues: issues[key]={'sample':issue,'cases':[]}
     issues[key]['cases'].append(f'{width}@{scale} {theme}')
    runs+=1;context.close()
  normal=browser.new_context(viewport={'width':1280,'height':1000},color_scheme='light',reduced_motion='no-preference',java_script_enabled=False)
  normal.route('**/*',serve);nt=normal.new_page();nt.goto(ORIGIN+BASE+route,wait_until='load')
  animations=[i for i in nt.locator('.site-refresh').evaluate(METRICS) if i['kind']=='animation'];normal.close()
  record={'route':'/'+route,'cases':runs,'issues':list(issues.values()),'keyboard':keyboard,'normal_motion_animations':animations}
  results.append(record);print(json.dumps(record),flush=True)
 browser.close()
# Built output checks cover every generated route, not only browser samples.
from bs4 import BeautifulSoup
static={'html':0,'inline_styles':[],'duplicate_ids':[],'csp_mismatch_vs_main':[],'executable_scripts':[]}
for f in (ROOT/'web/dist').rglob('*.html'):
 static['html']+=1;doc=BeautifulSoup(f.read_text(),'html.parser');relative=str(f.relative_to(ROOT/'web/dist'))
 if doc.select('[style]'):static['inline_styles'].append(relative)
 ids=[n['id'] for n in doc.select('[id]')]
 if len(ids)!=len(set(ids)):static['duplicate_ids'].append(relative)
 baseline=ROOT.parents[1]/'web/dist'/relative
 if baseline.is_file():
  old=BeautifulSoup(baseline.read_text(),'html.parser')
  hashes=lambda d:sorted(re.findall(r"'sha(?:256|384|512)-[^']+'",' '.join(n.get('content','') for n in d.select('meta[http-equiv="Content-Security-Policy"]'))))
  if hashes(doc)!=hashes(old):static['csp_mismatch_vs_main'].append(relative)
 for s in doc.select('script'):
  if s.get('type')!='application/ld+json':static['executable_scripts'].append({'route':relative,'src':s.get('src'),'inline':not bool(s.get('src'))})
print(json.dumps({'static':static}),flush=True)
data={'browser':results,'static':static}
marker = '<!-- ' + 'RESULTS -->'
base=REPORT.read_text().split(marker)[0]
REPORT.write_text(base+marker+'\n\n## Raw audit measurements\n\n```json\n'+json.dumps(data,indent=2)+'\n```\n')

```
<!-- END_AUDIT_RUNNER -->

## Screenshot overview runner

<!-- VISUAL_RUNNER -->
```python
from playwright.sync_api import sync_playwright
from tests.test_web_home_hero_layout import BASE, ORIGIN, serve
from PIL import Image, ImageDraw
import io, base64, json
routes=["", "how-it-works/", "safety/", "download/", "families/", "faq/", "guides/", "developers/", "developers/cli/", "developers/config/"]
with sync_playwright() as d:
 b=d.chromium.launch(headless=True)
 for theme,width in (("light",1280),("dark",320)):
  cellw=480 if width==1280 else 320
  cellh=375 if width==1280 else 780
  sheet=Image.new("RGB",(cellw*2,(cellh+25)*5),"white")
  draw=ImageDraw.Draw(sheet)
  for i,route in enumerate(routes):
   c=b.new_context(viewport={"width":width,"height":1000 if width==1280 else 780},color_scheme=theme,reduced_motion="reduce",java_script_enabled=False)
   c.route("**/*",serve);t=c.new_page();t.goto(ORIGIN+BASE+route,wait_until="load")
   pic=Image.open(io.BytesIO(t.screenshot())).convert("RGB").resize((cellw,cellh))
   x=(i%2)*cellw;y=(i//2)*(cellh+25)
   draw.text((x+5,y+3),"/"+route+" "+theme,fill="black");sheet.paste(pic,(x,y+25));c.close()
  out=io.BytesIO();sheet.save(out,format="JPEG",quality=55)
  print(json.dumps({"image":base64.b64encode(out.getvalue()).decode()}),flush=True)
 b.close()

```
<!-- END_VISUAL_RUNNER -->

<!-- RESULTS -->

## Raw audit measurements

```json
{
  "browser": [
    {
      "route": "/",
      "cases": 14,
      "issues": [
        {
          "sample": {
            "kind": "contrast",
            "tag": "P",
            "id": "",
            "text": "Our promises",
            "ratio": 6.919,
            "threshold": 7
          },
          "cases": [
            "320@1 light",
            "360@1 light",
            "768@1 light",
            "1280@1 light",
            "1024@1.25 light",
            "1280@1.5 light",
            "640@2 light"
          ]
        }
      ],
      "keyboard": [
        {
          "theme": "light",
          "reached": true,
          "outline": {
            "visible": true,
            "width": "3px",
            "style": "solid"
          }
        },
        {
          "theme": "light",
          "width": 320,
          "traversed": 36,
          "unreachable": []
        },
        {
          "theme": "light",
          "width": 1280,
          "traversed": 36,
          "unreachable": []
        },
        {
          "theme": "light",
          "width": 1280,
          "traversed": 36,
          "unreachable": []
        },
        {
          "theme": "dark",
          "reached": true,
          "outline": {
            "visible": true,
            "width": "3px",
            "style": "solid"
          }
        },
        {
          "theme": "dark",
          "width": 320,
          "traversed": 36,
          "unreachable": []
        },
        {
          "theme": "dark",
          "width": 1280,
          "traversed": 36,
          "unreachable": []
        },
        {
          "theme": "dark",
          "width": 1280,
          "traversed": 36,
          "unreachable": []
        }
      ],
      "normal_motion_animations": []
    },
    {
      "route": "/how-it-works/",
      "cases": 14,
      "issues": [
        {
          "sample": {
            "kind": "contrast",
            "tag": "P",
            "id": "",
            "text": "A clear process",
            "ratio": 6.919,
            "threshold": 7
          },
          "cases": [
            "320@1 light",
            "360@1 light",
            "768@1 light",
            "1280@1 light",
            "1024@1.25 light",
            "1280@1.5 light",
            "640@2 light"
          ]
        }
      ],
      "keyboard": [
        {
          "theme": "light",
          "reached": true,
          "outline": {
            "visible": true,
            "width": "3px",
            "style": "solid"
          }
        },
        {
          "theme": "light",
          "width": 320,
          "traversed": 3,
          "unreachable": []
        },
        {
          "theme": "light",
          "width": 1280,
          "traversed": 3,
          "unreachable": []
        },
        {
          "theme": "light",
          "width": 1280,
          "traversed": 3,
          "unreachable": []
        },
        {
          "theme": "dark",
          "reached": true,
          "outline": {
            "visible": true,
            "width": "3px",
            "style": "solid"
          }
        },
        {
          "theme": "dark",
          "width": 320,
          "traversed": 3,
          "unreachable": []
        },
        {
          "theme": "dark",
          "width": 1280,
          "traversed": 3,
          "unreachable": []
        },
        {
          "theme": "dark",
          "width": 1280,
          "traversed": 3,
          "unreachable": []
        }
      ],
      "normal_motion_animations": []
    },
    {
      "route": "/safety/",
      "cases": 14,
      "issues": [
        {
          "sample": {
            "kind": "contrast",
            "tag": "P",
            "id": "",
            "text": "Your choices",
            "ratio": 6.919,
            "threshold": 7
          },
          "cases": [
            "320@1 light",
            "360@1 light",
            "768@1 light",
            "1280@1 light",
            "1024@1.25 light",
            "1280@1.5 light",
            "640@2 light"
          ]
        },
        {
          "sample": {
            "kind": "contrast",
            "tag": "P",
            "id": "",
            "text": "Your choice",
            "ratio": 6.919,
            "threshold": 7
          },
          "cases": [
            "320@1 light",
            "360@1 light",
            "768@1 light",
            "1280@1 light",
            "1024@1.25 light",
            "1280@1.5 light",
            "640@2 light"
          ]
        },
        {
          "sample": {
            "kind": "contrast",
            "tag": "P",
            "id": "",
            "text": "About this site",
            "ratio": 6.919,
            "threshold": 7
          },
          "cases": [
            "320@1 light",
            "360@1 light",
            "768@1 light",
            "1280@1 light",
            "1024@1.25 light",
            "1280@1.5 light",
            "640@2 light"
          ]
        }
      ],
      "keyboard": [
        {
          "theme": "light",
          "reached": true,
          "outline": {
            "visible": true,
            "width": "3px",
            "style": "solid"
          }
        },
        {
          "theme": "light",
          "width": 320,
          "traversed": 5,
          "unreachable": []
        },
        {
          "theme": "light",
          "width": 1280,
          "traversed": 5,
          "unreachable": []
        },
        {
          "theme": "light",
          "width": 1280,
          "traversed": 5,
          "unreachable": []
        },
        {
          "theme": "dark",
          "reached": true,
          "outline": {
            "visible": true,
            "width": "3px",
            "style": "solid"
          }
        },
        {
          "theme": "dark",
          "width": 320,
          "traversed": 5,
          "unreachable": []
        },
        {
          "theme": "dark",
          "width": 1280,
          "traversed": 5,
          "unreachable": []
        },
        {
          "theme": "dark",
          "width": 1280,
          "traversed": 5,
          "unreachable": []
        }
      ],
      "normal_motion_animations": []
    },
    {
      "route": "/download/",
      "cases": 14,
      "issues": [],
      "keyboard": [
        {
          "theme": "light",
          "reached": true,
          "outline": {
            "visible": true,
            "width": "3px",
            "style": "solid"
          }
        },
        {
          "theme": "light",
          "width": 320,
          "traversed": 6,
          "unreachable": []
        },
        {
          "theme": "light",
          "width": 1280,
          "traversed": 6,
          "unreachable": []
        },
        {
          "theme": "light",
          "width": 1280,
          "traversed": 6,
          "unreachable": []
        },
        {
          "theme": "dark",
          "reached": true,
          "outline": {
            "visible": true,
            "width": "3px",
            "style": "solid"
          }
        },
        {
          "theme": "dark",
          "width": 320,
          "traversed": 6,
          "unreachable": []
        },
        {
          "theme": "dark",
          "width": 1280,
          "traversed": 6,
          "unreachable": []
        },
        {
          "theme": "dark",
          "width": 1280,
          "traversed": 6,
          "unreachable": []
        }
      ],
      "normal_motion_animations": []
    },
    {
      "route": "/families/",
      "cases": 14,
      "issues": [],
      "keyboard": [
        {
          "theme": "light",
          "reached": true,
          "outline": {
            "visible": true,
            "width": "3px",
            "style": "solid"
          }
        },
        {
          "theme": "light",
          "width": 320,
          "traversed": 10,
          "unreachable": []
        },
        {
          "theme": "light",
          "width": 1280,
          "traversed": 10,
          "unreachable": []
        },
        {
          "theme": "light",
          "width": 1280,
          "traversed": 10,
          "unreachable": []
        },
        {
          "theme": "dark",
          "reached": true,
          "outline": {
            "visible": true,
            "width": "3px",
            "style": "solid"
          }
        },
        {
          "theme": "dark",
          "width": 320,
          "traversed": 10,
          "unreachable": []
        },
        {
          "theme": "dark",
          "width": 1280,
          "traversed": 10,
          "unreachable": []
        },
        {
          "theme": "dark",
          "width": 1280,
          "traversed": 10,
          "unreachable": []
        }
      ],
      "normal_motion_animations": []
    },
    {
      "route": "/faq/",
      "cases": 14,
      "issues": [],
      "keyboard": [
        {
          "theme": "light",
          "reached": true,
          "outline": {
            "visible": true,
            "width": "3px",
            "style": "solid"
          }
        },
        {
          "theme": "light",
          "width": 320,
          "traversed": 31,
          "unreachable": []
        },
        {
          "theme": "light",
          "width": 1280,
          "traversed": 31,
          "unreachable": []
        },
        {
          "theme": "light",
          "width": 1280,
          "traversed": 31,
          "unreachable": []
        },
        {
          "theme": "dark",
          "reached": true,
          "outline": {
            "visible": true,
            "width": "3px",
            "style": "solid"
          }
        },
        {
          "theme": "dark",
          "width": 320,
          "traversed": 31,
          "unreachable": []
        },
        {
          "theme": "dark",
          "width": 1280,
          "traversed": 31,
          "unreachable": []
        },
        {
          "theme": "dark",
          "width": 1280,
          "traversed": 31,
          "unreachable": []
        }
      ],
      "normal_motion_animations": []
    },
    {
      "route": "/guides/",
      "cases": 14,
      "issues": [],
      "keyboard": [
        {
          "theme": "light",
          "reached": true,
          "outline": {
            "visible": true,
            "width": "3px",
            "style": "solid"
          }
        },
        {
          "theme": "light",
          "width": 320,
          "traversed": 34,
          "unreachable": []
        },
        {
          "theme": "light",
          "width": 1280,
          "traversed": 34,
          "unreachable": []
        },
        {
          "theme": "light",
          "width": 1280,
          "traversed": 34,
          "unreachable": []
        },
        {
          "theme": "dark",
          "reached": true,
          "outline": {
            "visible": true,
            "width": "3px",
            "style": "solid"
          }
        },
        {
          "theme": "dark",
          "width": 320,
          "traversed": 34,
          "unreachable": []
        },
        {
          "theme": "dark",
          "width": 1280,
          "traversed": 34,
          "unreachable": []
        },
        {
          "theme": "dark",
          "width": 1280,
          "traversed": 34,
          "unreachable": []
        }
      ],
      "normal_motion_animations": []
    },
    {
      "route": "/developers/",
      "cases": 14,
      "issues": [],
      "keyboard": [
        {
          "theme": "light",
          "reached": true,
          "outline": {
            "visible": true,
            "width": "3px",
            "style": "solid"
          }
        },
        {
          "theme": "light",
          "width": 320,
          "traversed": 23,
          "unreachable": []
        },
        {
          "theme": "light",
          "width": 1280,
          "traversed": 23,
          "unreachable": []
        },
        {
          "theme": "light",
          "width": 1280,
          "traversed": 23,
          "unreachable": []
        },
        {
          "theme": "dark",
          "reached": true,
          "outline": {
            "visible": true,
            "width": "3px",
            "style": "solid"
          }
        },
        {
          "theme": "dark",
          "width": 320,
          "traversed": 23,
          "unreachable": []
        },
        {
          "theme": "dark",
          "width": 1280,
          "traversed": 23,
          "unreachable": []
        },
        {
          "theme": "dark",
          "width": 1280,
          "traversed": 23,
          "unreachable": []
        }
      ],
      "normal_motion_animations": []
    },
    {
      "route": "/developers/cli/",
      "cases": 14,
      "issues": [],
      "keyboard": [
        {
          "theme": "light",
          "reached": true,
          "outline": {
            "visible": true,
            "width": "3px",
            "style": "solid"
          }
        },
        {
          "theme": "light",
          "width": 320,
          "traversed": 2,
          "unreachable": []
        },
        {
          "theme": "light",
          "width": 1280,
          "traversed": 2,
          "unreachable": []
        },
        {
          "theme": "light",
          "width": 1280,
          "traversed": 2,
          "unreachable": []
        },
        {
          "theme": "dark",
          "reached": true,
          "outline": {
            "visible": true,
            "width": "3px",
            "style": "solid"
          }
        },
        {
          "theme": "dark",
          "width": 320,
          "traversed": 2,
          "unreachable": []
        },
        {
          "theme": "dark",
          "width": 1280,
          "traversed": 2,
          "unreachable": []
        },
        {
          "theme": "dark",
          "width": 1280,
          "traversed": 2,
          "unreachable": []
        }
      ],
      "normal_motion_animations": []
    },
    {
      "route": "/developers/config/",
      "cases": 14,
      "issues": [],
      "keyboard": [
        {
          "theme": "light",
          "reached": true,
          "outline": {
            "visible": true,
            "width": "3px",
            "style": "solid"
          }
        },
        {
          "theme": "light",
          "width": 320,
          "traversed": 7,
          "unreachable": []
        },
        {
          "theme": "light",
          "width": 1280,
          "traversed": 7,
          "unreachable": []
        },
        {
          "theme": "light",
          "width": 1280,
          "traversed": 7,
          "unreachable": []
        },
        {
          "theme": "dark",
          "reached": true,
          "outline": {
            "visible": true,
            "width": "3px",
            "style": "solid"
          }
        },
        {
          "theme": "dark",
          "width": 320,
          "traversed": 7,
          "unreachable": []
        },
        {
          "theme": "dark",
          "width": 1280,
          "traversed": 7,
          "unreachable": []
        },
        {
          "theme": "dark",
          "width": 1280,
          "traversed": 7,
          "unreachable": []
        }
      ],
      "normal_motion_animations": []
    },
    {
      "route": "/guides/spokeo/",
      "cases": 14,
      "issues": [],
      "keyboard": [
        {
          "theme": "light",
          "reached": true,
          "outline": {
            "visible": true,
            "width": "3px",
            "style": "solid"
          }
        },
        {
          "theme": "light",
          "width": 320,
          "traversed": 11,
          "unreachable": []
        },
        {
          "theme": "light",
          "width": 1280,
          "traversed": 11,
          "unreachable": []
        },
        {
          "theme": "light",
          "width": 1280,
          "traversed": 11,
          "unreachable": []
        },
        {
          "theme": "dark",
          "reached": true,
          "outline": {
            "visible": true,
            "width": "3px",
            "style": "solid"
          }
        },
        {
          "theme": "dark",
          "width": 320,
          "traversed": 11,
          "unreachable": []
        },
        {
          "theme": "dark",
          "width": 1280,
          "traversed": 11,
          "unreachable": []
        },
        {
          "theme": "dark",
          "width": 1280,
          "traversed": 11,
          "unreachable": []
        }
      ],
      "normal_motion_animations": []
    },
    {
      "route": "/guides/beenverified/",
      "cases": 14,
      "issues": [],
      "keyboard": [
        {
          "theme": "light",
          "reached": true,
          "outline": {
            "visible": true,
            "width": "3px",
            "style": "solid"
          }
        },
        {
          "theme": "light",
          "width": 320,
          "traversed": 11,
          "unreachable": []
        },
        {
          "theme": "light",
          "width": 1280,
          "traversed": 11,
          "unreachable": []
        },
        {
          "theme": "light",
          "width": 1280,
          "traversed": 11,
          "unreachable": []
        },
        {
          "theme": "dark",
          "reached": true,
          "outline": {
            "visible": true,
            "width": "3px",
            "style": "solid"
          }
        },
        {
          "theme": "dark",
          "width": 320,
          "traversed": 11,
          "unreachable": []
        },
        {
          "theme": "dark",
          "width": 1280,
          "traversed": 11,
          "unreachable": []
        },
        {
          "theme": "dark",
          "width": 1280,
          "traversed": 11,
          "unreachable": []
        }
      ],
      "normal_motion_animations": []
    },
    {
      "route": "/guides/help-a-parent-remove-their-information/",
      "cases": 14,
      "issues": [],
      "keyboard": [
        {
          "theme": "light",
          "reached": true,
          "outline": {
            "visible": true,
            "width": "3px",
            "style": "solid"
          }
        },
        {
          "theme": "light",
          "width": 320,
          "traversed": 9,
          "unreachable": []
        },
        {
          "theme": "light",
          "width": 1280,
          "traversed": 9,
          "unreachable": []
        },
        {
          "theme": "light",
          "width": 1280,
          "traversed": 9,
          "unreachable": []
        },
        {
          "theme": "dark",
          "reached": true,
          "outline": {
            "visible": true,
            "width": "3px",
            "style": "solid"
          }
        },
        {
          "theme": "dark",
          "width": 320,
          "traversed": 9,
          "unreachable": []
        },
        {
          "theme": "dark",
          "width": 1280,
          "traversed": 9,
          "unreachable": []
        },
        {
          "theme": "dark",
          "width": 1280,
          "traversed": 9,
          "unreachable": []
        }
      ],
      "normal_motion_animations": []
    },
    {
      "route": "/guides/get-your-phone-number-off-people-search-sites/",
      "cases": 14,
      "issues": [],
      "keyboard": [
        {
          "theme": "light",
          "reached": true,
          "outline": {
            "visible": true,
            "width": "3px",
            "style": "solid"
          }
        },
        {
          "theme": "light",
          "width": 320,
          "traversed": 10,
          "unreachable": []
        },
        {
          "theme": "light",
          "width": 1280,
          "traversed": 10,
          "unreachable": []
        },
        {
          "theme": "light",
          "width": 1280,
          "traversed": 10,
          "unreachable": []
        },
        {
          "theme": "dark",
          "reached": true,
          "outline": {
            "visible": true,
            "width": "3px",
            "style": "solid"
          }
        },
        {
          "theme": "dark",
          "width": 320,
          "traversed": 10,
          "unreachable": []
        },
        {
          "theme": "dark",
          "width": 1280,
          "traversed": 10,
          "unreachable": []
        },
        {
          "theme": "dark",
          "width": 1280,
          "traversed": 10,
          "unreachable": []
        }
      ],
      "normal_motion_animations": []
    }
  ],
  "static": {
    "html": 67,
    "inline_styles": [],
    "duplicate_ids": [],
    "csp_mismatch_vs_main": [],
    "executable_scripts": [
      {
        "route": "download/index.html",
        "src": "/_assets/CopyHash.astro_astro_type_script_index_0_lang.LjnwmxnC.js",
        "inline": false
      }
    ]
  }
}
```
