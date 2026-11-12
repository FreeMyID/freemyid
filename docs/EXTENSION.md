# Free My ID browser extension

Status: **skeleton only (2026-11-11). Not shipped, not in any store, not installed by any installer.**
Owner: Nina Alvarez (wizard-packager). Architecture decided by Morgan Reyes.

The idea (`docs/ROADMAP.md`, dream list): when a person lands on a site that sells people's
information, a calm message says so and offers to start the removal. One click, and the Free My ID
app on the same computer does the work. The extension is a doorbell for the app. It holds no
personal details and does no removal work itself.

Target user: an older, non-technical person. Large type, plain words, two buttons, no jargon.

## 1. What is in the repository

```
extension/
  manifests/        base.json + chrome.json, edge.json, firefox.json (overrides)
  _locales/en/      messages.json: every word the person sees (i18n-ready)
  assets/icons/     16/32/48/128 px, made from brand/logo/final
  rules/gpc.json    one declarativeNetRequest rule: add "Sec-GPC: 1" (Chrome and Edge, off by default)
  src/
    background/main.js     service worker (Chrome, Edge) and event page (Firefox): same file
    content/banner.js      the banner; runs only on listed people-search hosts
    content/gpc.js         page half of Global Privacy Control; registered on demand, never in the manifest
    content/assisted-fill.js   TODO placeholder for Assisted-tier form help; never packaged
    popup/                 toolbar popup: app connected? is this site a broker? status for this site
    options/               settings page: banner on/off, forget "Not now", Global Privacy Control
    lib/                   browser.js (namespace shim), protocol.js, native.js, brokers.js,
                           settings.js, i18n.js, gpc.js, theme.css
  native-host/      host manifest templates, Windows registry template, install-locations.json
tools/build_extension.py   build script (Python standard library only)
src/freemyid/native_host.py   the app side: stub native messaging host
tests/test_extension_build.py, tests/test_native_host.py
```

Rules for this code, all held by tests:

- One Manifest V3 codebase. Plain JavaScript ES modules with JSDoc types.
- No npm, no bundler, no minifier, no third-party code, no remote code. What is in `extension/`
  is what ships, file for file. A store reviewer or an auditor can read all of it.
- The namespace shim is ours (`src/lib/browser.js`, one line), not webextension-polyfill.
- The extension makes no network request of its own. No analytics, no telemetry, no remote
  configuration, no update check beyond the store's own.

## 2. How the parts talk

```
 people-search page                       extension                         this computer
+--------------------+   internal    +------------------+   native     +---------------------+
| content/banner.js  | <-----------> | background/      | <----------> | freemyid.native_host |
| (hostname only)    |   messages    | main.js          |  messaging   | (stdin/stdout)       |
+--------------------+               |                  |  org.freemyid| -> the Free My ID    |
+--------------------+               |  lib/brokers.js  |  .host       |    app does the work |
| popup, options     | <-----------> |  lib/native.js   |              +---------------------+
+--------------------+               +------------------+
```

- Only the background talks to the app. The banner and the popup ask the background.
- The background takes the page's hostname from what the browser reports about the sender
  (`sender.url`, top frame only), never from anything the page could write.
- A content script may act only on the broker whose site it is running on. The popup may act on
  any broker in the bundled list.
- The app is asked about a site only when the hostname is already on the bundled broker list,
  so the app is never told about ordinary browsing.
- Both banner buttons need a real click (`event.isTrusted`). The banner lives in a closed shadow
  root so the page cannot reach into it or restyle it.

### Banner behaviour

- Text: "This site sells people's information. Free My ID can ask them to remove you."
  Buttons: **Remove me** and **Not now**.
- Shown only on hosts of `people_search`, `background_check`, `phone_lookup` and `family_tree`
  brokers. Marketing data brokers and credit bureaus are named in the popup but get no banner:
  their sites do not show the visitor's listing, and a banner on a bank-like site would alarm
  people. Government portals and search engines (`category: other`) are never listed at all.
- "Not now" hides the banner on that broker's sites for 30 days (stored on this computer only).
- No banner when the app says a request is already on its way (`submitted`,
  `awaiting_verification`, `confirmed`, `removed`).
- After "Remove me" the banner says what happened in plain words: the app has it, the app did
  not answer, or (today, with the stub host) the button is not ready yet.
- Honesty copy: "This covers this site only, and listings can come back, so the app keeps
  checking." No promise that a listing is gone.

## 3. Message protocol (extension and app)

Transport: browser native messaging, host name **`org.freemyid.host`**. Each message is a 4-byte
length in the machine's byte order followed by UTF-8 JSON. The extension uses
`runtime.sendNativeMessage` (one short-lived host process per request), which suits a service
worker that the browser may stop at any moment.

Every request is a versioned envelope. The reply repeats `v` and `id`, echoes `type`, and has
`ok` (true or false). When `ok` is false there is an `error` code.

| `type` | Extra request field | Reply fields (when `ok`) | Today |
|---|---|---|---|
| `ping` | none | `pong: true` | works |
| `status` | none | `connected: true`, `app_version` | works |
| `site_check` | `hostname` (lower-case host, no path) | `broker_id` (or null), `listing_state` | stub: always `null` / `unknown`, plus `stub: true` |
| `start_removal` | `broker_id` | `accepted: true` | stub: `ok: false`, `error: "not_implemented"` |

```json
{"v": 1, "type": "site_check", "id": "6f1c…", "hostname": "www.spokeo.com"}
{"v": 1, "type": "site_check", "id": "6f1c…", "ok": true, "broker_id": null, "listing_state": "unknown", "stub": true}
```

`listing_state` uses the words of `freemyid.models.ListingState`.

Error codes from the host: `bad_request`, `unsupported_version`, `unknown_type`,
`not_implemented`, `internal_error`. From the extension itself: `app_not_connected`,
`bad_reply`, `unknown_broker`, `not_allowed`.

Rules of the protocol:

1. **No personal details, ever.** A request may hold `v`, `type`, `id` and the one field in the
   table. The host refuses any other field, so there is no room to carry a name or an address.
   Replies carry ids, state words and a version number. The host enforces that on the way out
   too: a `site_check` reply may add only `broker_id`, `listing_state` and `stub`, a
   `start_removal` reply only `accepted`, and a failed reply an `error` code. Each value must be
   null, true/false or one short lower-case word (letters, digits, `_`, 64 at most). Anything
   else the app code hands back is dropped, so a name or a sentence cannot ride along.
2. `hostname` is a bare host. A path or a full address is refused (a people-search path often
   contains a person's name).
3. `start_removal` is a request, not a command. The app applies all its usual rules before
   anything is sent: consent on file, confirmed matches only (rule 7), data minimisation
   (rule 6), no CAPTCHA solving (rule 5).
4. The host logs nothing about a message and opens no file, database or network connection.
5. Requests over 64 KiB and replies over 1 MiB are refused. So is JSON nested more than 4
   levels deep (a request is one flat object). Ids, hostnames and broker ids must match in full;
   a trailing newline is refused. A reply that cannot be encoded is replaced by `internal_error`
   and the host keeps running.
6. **The host checks who started it** before it reads anything. Chrome and Edge pass the
   caller's origin (`chrome-extension://<id>/`) as the first argument; Firefox passes the host
   manifest's path and then the add-on id. A caller that is not on the list gets no answer
   (exit code 2, one fixed sentence on stderr). The allowed Chrome and Edge ids are
   `CHROME_EXTENSION_IDS` in `native_host.py`, **empty until the extension has store ids**, so
   today Chrome and Edge are answered only when a developer names an id in the
   `FREEMYID_EXTENSION_IDS` environment variable (section 9). The browser's own check of the
   host manifest still applies; this is a second one.
7. A change to the envelope means a new `v`, changed in `src/lib/protocol.js`,
   `src/freemyid/native_host.py` and this page together. A test compares the constants.

Internal messages (inside the extension only): `fmid.site_check`, `fmid.start_removal`,
`fmid.dismiss`, `fmid.status`.

## 4. Permissions and why each one is there

Install-time permissions on **every** browser:

| Permission | Why | What it does not allow |
|---|---|---|
| `nativeMessaging` | The only way the extension reaches the Free My ID app on the same computer. | No network. It can start one named program (`org.freemyid.host`) that the app's installer registered, and nothing else. |
| `storage` | Remembers two things in `storage.local`: banner on/off, and which brokers got "Not now" and until when. | `storage.sync` is never used, so nothing is copied to the browser vendor's servers. |
| `activeTab` | When the person opens the popup, the extension may learn the address of that one tab, to say whether it is a listed site. It keeps the hostname only. | No access to other tabs, no access without a click, no history. |
| Content script on listed hosts (`content_scripts.matches`) | Shows the banner. One exact `https://host/*` pattern per people-search host, generated at build time from the public broker list. | No wildcard hosts, no `<all_urls>`, top frame only, isolated world. The build fails otherwise. |

Not requested: `tabs`, `webRequest`, `cookies`, `history`, `scripting` (at install),
`host_permissions`, `externally_connectable`, `web_accessible_resources`. The build refuses a
manifest that contains them.

Extra, **Chrome and Edge only**, for the Global Privacy Control stub (section 6). This is wider
than the three-permission set the skeleton started with, and it needs a security review before
it ships:

| Permission | When it is granted | Why |
|---|---|---|
| `declarativeNetRequestWithHostAccess` | Install time. It shows no warning and can do nothing by itself: its rules act only on sites the extension has host access to. | Carries the one static rule that adds `Sec-GPC: 1`. The ruleset ships disabled. |
| `scripting` (optional) | Only when the person switches GPC on in Settings. | Registers `src/content/gpc.js` so pages can read `navigator.globalPrivacyControl`. |
| `*://*/*` (optional host permission) | Same moment. The browser asks the person, in its own words ("read and change all your data on all websites"). | The header rule and the page script need host access to every site the signal goes to. Switching GPC off hands the permission back. |

Content security policy for extension pages (all browsers):

```
default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self'; connect-src 'self';
object-src 'none'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'
```

No inline script, no inline style, no remote source, no `eval`.

## 5. Privacy guarantees

What we can promise, because tests and the design hold it:

- The extension sends nothing over the internet. It has no network code. The single `fetch` in
  the code reads `data/broker_domains.json` from inside the extension package.
- The extension never holds a person's name, address, phone, email or date of birth. Those stay
  in the app. The protocol has no field that could carry them.
- On listed sites the extension looks at the hostname and nothing else. It does not read page
  text, forms, cookies or the address path. On other sites it does nothing (unless the person
  switched GPC on, which adds a header and one page property and reads nothing).
- The broker list is bundled and comes from the **public** `brokers/registry.sample.yaml`. The
  private registry is never read by the build (a test checks this), and the list is never
  updated remotely.
- Rule 5: the extension never touches a CAPTCHA or any "are you human" check, never changes how
  the browser identifies itself, and never automates a step a site reserves for a person.

What we must not promise:

- That a site obeys. "Removed" always means removed from that one site, and listings can come
  back.
- That nobody can tell the extension is installed. A listed site can notice the banner element
  in its page, and any site can read `navigator.globalPrivacyControl` when GPC is on (that is
  the point of the signal).
- That the list is complete. The popup says so: "Not on our list. That does not mean it is safe."

Known risks to review before shipping (for Marcus):

- A hostile listed page could try to trick the person into clicking "Remove me" (overlay or
  misdirection). The worst result is a removal request to that same broker, and the app still
  applies its own checks.
- `site_check` tells the local app that a listed site is open. The app must not keep that as a
  visit log.
- Optional all-sites access for GPC is a large grant. Keep the rule validator
  (`validate_gpc_rules`) strict: one rule, one header, no redirect, no block.

## 6. Global Privacy Control (stub, off by default)

Global Privacy Control (GPC) is a browser signal that says "do not sell or share my
information". It has two halves, and a site may look at either:

1. the request header `Sec-GPC: 1` (here: `extension/rules/gpc.json`, a static
   declarativeNetRequest ruleset that ships disabled);
2. the page property `navigator.globalPrivacyControl === true` (here:
   `extension/src/content/gpc.js`, registered in the page's own world only while GPC is on).

The person turns it on under Settings ("Send the Global Privacy Control signal to every website
I visit"). The checkbox is not pre-ticked. `src/lib/gpc.js` then asks the browser for the two
optional permissions, enables the ruleset and registers the page script. Turning it off undoes
all three.

The signal is either fully on or fully off, never half:

- **Switching on.** If any step after the browser's permission question fails, everything is
  switched off again, the permission is handed back, and Settings says "Not turned on".
- **Switching off.** The permission is always handed back, whatever else fails (without it the
  browser sends no header and runs no page script for this extension). Settings says "Off" only
  after the browser confirms it; otherwise the box stays ticked and it says "Still on".
- **Taken back in the browser.** The person can remove the "all websites" permission in the
  browser's own settings. The background script hears that (`permissions.onRemoved`) and
  switches the rest off. It makes the same check each time it starts. The background can only
  switch the signal off; switching it on always needs the person's click in Settings.

Per browser:

- **Chrome, Edge:** as above.
- **Firefox:** has GPC built in (Settings, Privacy & Security, "Tell websites not to sell or
  share my data"). The Firefox package therefore carries no rule file, no page script and no
  extra permission, and Settings shows where Firefox's own switch is. If the browser already
  sends the signal (Firefox with the setting on, Brave), Settings says there is nothing to turn on.

Stub status. Built and tested by the Python tests: the manifest shape, the rule file, that it
ships off, that only the options page can switch it on. `tests/test_extension_gpc_browser.py`
runs the real `gpc.js`, `options.js` and `background/main.js` in Playwright's Chromium against
a stand-in for the browser's extension API, makes each step fail in turn and checks what is
left switched on. **Not tested, because it needs a real Chrome or Edge with the extension
installed:** the browser's own permission question, the errors the real API raises, the header
on the wire, the page property on a real site, and `permissions.onRemoved` fired by the
browser's settings page.

Honest limits, which the Settings text states: GPC is a signal, not a removal. It does not take
a listing down. Whether a site must honor it depends on where the person lives.

### Which state laws treat the signal as a valid opt-out of sale

> **Not verified.** The table below was written from the team's working knowledge on
> 2026-11-11 and has **not** been checked against the statutes or the regulators' pages.
> Same rule as for letters (`docs/PLAN_V1.md`, state-law citations): nothing from this table
> goes into user-facing copy, a letter or the website until Priya has verified each row against
> a primary source and recorded the date. Until then the app says only "some state laws".

States whose comprehensive privacy law requires covered businesses to treat a universal opt-out
signal (such as GPC) as a valid request to opt out of the sale of personal data, and usually of
targeted advertising too:

| State | Law | Signal duty in force from (to verify) | Notes (to verify) |
|---|---|---|---|
| California | CCPA as amended by CPRA; regulations, 11 CCR § 7025 | In force | Covers sale and "sharing". The Attorney General names GPC, and the 2022 Sephora settlement turned on ignoring it. |
| Colorado | Colorado Privacy Act | 1 July 2024 | The Attorney General keeps a list of recognized universal opt-out mechanisms; GPC is on it. |
| Connecticut | Connecticut Data Privacy Act | 1 January 2025 | |
| Texas | Texas Data Privacy and Security Act | 1 January 2025 | |
| Montana | Montana Consumer Data Privacy Act | 1 January 2025 | |
| Nebraska | Nebraska Data Privacy Act | 1 January 2025 | |
| New Hampshire | New Hampshire privacy act (SB 255) | 1 January 2025 | |
| New Jersey | New Jersey Data Privacy Act | 15 July 2025 | Six months after the law took effect. |
| Minnesota | Minnesota Consumer Data Privacy Act | 31 July 2025 | |
| Maryland | Maryland Online Data Privacy Act | 1 October 2025 | |
| Delaware | Delaware Personal Data Privacy Act | 1 January 2026 | |
| Oregon | Oregon Consumer Privacy Act | 1 January 2026 | |

States with a comprehensive privacy law that, to our knowledge, does **not** require businesses
to honor such a signal: Virginia, Utah, Iowa, Indiana, Tennessee, Kentucky, Rhode Island.
In states with no comprehensive privacy law a site may ignore the signal.

Also to verify: California AB 566 (signed 2025) requires browsers themselves to offer an opt-out
preference signal setting from 1 January 2027. If that holds, Chrome and Edge will get a built-in
switch and this stub should then point at it, as it does for Firefox today.

Things the table does not say, and copy must not imply:

- These laws apply to businesses over certain size thresholds, and several exempt publicly
  available information. A people-search listing built from public records may be outside them.
- The signal is tied to the browser. It opts that browser (and an account the person is signed
  in to) out of sale. It is not a deletion request and does not replace the app's removal
  requests.
- Most of the statutes describe an "opt-out preference signal" in general terms. Only
  California and Colorado are known to us to name GPC.

## 7. Differences between browsers

| | Chrome | Edge | Firefox |
|---|---|---|---|
| Background | service worker (`background.service_worker`, module) | same as Chrome | event page (`background.scripts`, module) |
| Namespace | `chrome` | `chrome` | `browser` (the shim picks whichever exists) |
| Extension id | given by the Chrome Web Store (or derived from the folder when loaded unpacked) | given by Edge Add-ons, different from Chrome's | fixed in the manifest: `extension@freemyid.org` |
| Host manifest key | `allowed_origins` (`chrome-extension://<id>/`) | same | `allowed_extensions` (the fixed id) |
| Host manifest location | per-user registry key or file, see `extension/native-host/install-locations.json` | own key and folder | own key and folder |
| GPC | extension stub (section 6) | extension stub | built into the browser; nothing shipped |
| Extra manifest keys | `minimum_chrome_version: 120` | same | `browser_specific_settings.gecko` with `strict_min_version: 128.0` and `data_collection_permissions: none` |
| Unpacked loading | stays until removed | stays until removed | temporary: gone when Firefox closes |

`chrome.json` and `edge.json` are identical today, so the two packages are byte-for-byte the
same. They stay separate files because the stores give different ids and may need different
keys later.

Written for both background models: listeners are registered at the top level, nothing
important is kept in memory, and there is no DOM use in the background.

## 8. Build

```
python tools/build_extension.py                    # chrome, edge and firefox
python tools/build_extension.py --browser firefox
python tools/build_extension.py --out /some/folder
```

Output (ignored by git): `dist/extension/<browser>/` and
`dist/extension/freemyid-extension-<browser>-<version>.zip`.

The script merges `manifests/base.json` with the browser's override, checks the result against
the rules in section 4, writes `data/broker_domains.json` and the content-script match list
from `brokers/registry.sample.yaml`, copies the files and zips them. It uses the Python
standard library only, including a small reader for the five registry keys it needs (compared
with PyYAML in a test). The same inputs give the same bytes: sorted names, fixed dates in the
zip, no timestamps.

Which registry file is read is decided by where the path really leads, not by its name. The
script reads `brokers/registry.sample.yaml`, or with `--registry` a `*.sample.yaml` test file
under `tests/`. It refuses symlinks, a second name (hard link) for the private registry, and
any other place. `brokers/registry.yaml` can never be picked up.

A host is put on the list only when it belongs to the broker's own site, so a shared opt-out
host or a parent company's host is not pinned on the wrong broker.

## 9. Try it unpacked (developers)

Build first. Then:

- **Chrome:** open `chrome://extensions`, switch on "Developer mode", press "Load unpacked",
  choose `dist/extension/chrome`.
- **Edge:** open `edge://extensions`, switch on "Developer mode", press "Load unpacked", choose
  `dist/extension/edge`.
- **Firefox:** open `about:debugging#/runtime/this-firefox`, press "Load Temporary Add-on",
  choose `dist/extension/firefox/manifest.json`. It is removed when Firefox closes.

Without the native host the popup says "Not connected" and "Remove me" answers "The Free My ID
app did not answer". That is the expected state today.

To connect the stub host on a developer machine (this writes a per-user file or registry key,
so by rule 9 agents do not do it during development; a person may on their own machine):

1. Make a small launcher the browser can start, because the host manifest's `path` must be one
   program with no arguments. On macOS and Linux a short shell script that runs
   `python -m freemyid.native_host "$@"` from the project's virtual environment; on Windows a
   `.bat` file doing the same with `%*`. The launcher must pass its arguments on: the browser
   puts the caller's origin there and the host refuses to answer without it. For Chrome and
   Edge the launcher must also set `FREEMYID_EXTENSION_IDS` to the id shown on the extensions
   page (an unpacked extension's id differs from machine to machine). Firefox needs no
   variable; its id is fixed.
2. Fill in a template from `extension/native-host/`: `HOST_PATH` is the launcher's full path,
   `CHROME_EXTENSION_ID` is the id shown on the extensions page.
3. Put the file (or the registry key) where `install-locations.json` says for your system and
   browser, then reload the extension.

Checked on 2026-11-11: the Chrome package loads in Playwright's Chromium with every web request
answered locally; the service worker starts, the banner appears on a listed host and not on an
unlisted one or a marketing data broker, the popup and options pages render with no console
errors, and "Remove me" reports that the app did not answer. **Not checked:** real Chrome, real
Edge, any Firefox, a connected native host, the GPC switch in a real browser (section 6 says
what the automated browser test does cover).

## 10. What the installer has to do later (not built)

Nothing in `packaging/` or the installers was changed. When the extension is ready to be tried
by family testers, the installer for each system needs one more step:

1. Ship a host program next to the app: a third PyInstaller executable,
   `freemyid-native-host` (entry point `freemyid.native_host:main`).
2. Write the two host manifest files (Chrome/Edge and Firefox) into the app's folder, filled
   from the templates, with the real store ids in `allowed_origins`. The same ids go into
   `CHROME_EXTENSION_IDS` in `native_host.py`, or the host refuses Chrome and Edge.
3. Register them per user, without admin rights:
   - Windows: three `HKEY_CURRENT_USER` keys (`windows-registry.reg.template`), written by Inno
     Setup; the uninstaller deletes them.
   - macOS and Linux: copy the files to the paths in `install-locations.json`; uninstall removes
     them.
4. `freemyid doctor` should report whether the host is registered for each installed browser.

`native_host.host_manifest()` renders the JSON for step 2 and is tested against the templates.

## 11. Store publishing (TODO, owner decisions needed)

Not started. Nothing has been submitted anywhere.

- [ ] Decide whether the extension is published at all before the app's own audit (it is new
      attack surface).
- [ ] Chrome Web Store: developer account (one-time fee, owner's decision and identity; never a
      made-up identity), single-purpose statement, a written justification for each permission
      (section 4 is the draft), privacy practices form ("does not collect or use data"), listing
      text and screenshots from Jordan and Iris. `nativeMessaging` and the optional all-sites
      access are likely to mean a slower, closer review.
- [ ] Microsoft Edge Add-ons: Partner Center account, same package content, separate id.
- [ ] Firefox Add-ons (AMO): account, listing; the package needs no source upload because
      nothing is bundled or minified. Family testing on Firefox before a public listing needs
      AMO's "unlisted" signing, because unsigned add-ons load only temporarily.
- [ ] Put the store ids into the host manifests (`allowed_origins`) and into
      `CHROME_EXTENSION_IDS` in `native_host.py` (the host's own caller check), and, for stable
      development ids on Chrome and Edge, decide whether to pin a `key` in the manifest.
- [ ] Add the build and its tests to CI (`.github/workflows`), and attach the three zips to
      releases with checksums.
- [ ] Marcus: threat-model review (section 5 risks, the GPC permissions).
- [ ] Priya: verify the state-law table in section 6.
- [ ] Spanish strings (`_locales/es/messages.json`) with the rest of the Spanish work.
- [ ] Per the "no accounts" rule, the website must offer the store links directly; nobody is
      sent to github.com to get the extension.

## 12. Roadmap phase (proposal, for Morgan and the owner)

The extension was a dream-list item (`docs/ROADMAP.md`, section 7). It is not needed for any
current release gate.

Where it fits the hands-off goal (`docs/roadmap/ROADMAP_TO_1.0.md`, bar 9 and section 7a: no
person actions after setup, no staff). Be plain about this: the zero-touch engine does not need
an extension, and a banner that asks for a click is itself a person action. The extension earns
its place in three narrower ways:

- **The residual human step gets cheaper.** Section 7a ends with "a batched human click" for
  steps a site reserves for people. Those happen in the person's own browser, which is where
  the extension lives. Phase 3 lets the app pre-fill what the person allowed, so the click
  costs seconds. The human check itself stays with the person (rule 5).
- **Sites met outside the schedule.** When a person runs into a listed site on their own, one
  click hands the broker id to the app instead of "open the app and find it".
- **Set once, then silent.** Global Privacy Control is a signal the person switches on once.

It adds no staff and no server: nothing here needs a human operator or a service of ours.

Proposed phases:

| Phase | What | When (proposed) |
|---|---|---|
| 0. Bones | This skeleton, the stub host, tests, this page. Nothing ships. | now |
| 1. Real answers | `site_check` and `start_removal` wired to the app (change requests in `docs/handoff/wizard-packager.md`); installers register the host; family testers load it by hand. | after the three desktop installers (0.5), since each installer must register the host |
| 2. Public | Store listings for Chrome, Edge and Firefox; Spanish; GPC out of stub status after real-browser tests and review. | with or after the hardening release (0.9), so it is inside the audit |
| 3. Assisted form help | After a click, fill only the fields the person allowed for that site; the person does every human check and presses Submit (`src/content/assisted-fill.js` lists the fixed rules). Needs a new protocol message that carries those values for one click, plus the `scripting` permission. | 1.x |

Out of scope at every phase: solving or bypassing CAPTCHAs, any disguise of the browser, any
network call from the extension, paying, creating accounts.
