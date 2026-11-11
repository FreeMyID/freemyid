# Free My ID: Android and iOS plan

Owner/PM: Morgan Reyes. Written 2026-11-11, at v0.3.1. Release numbers refer to `ROADMAP_TO_1.0.md`.
Policy facts were read from the official pages on 2026-11-11 and are cited by URL. Store rules change often: re-read every cited page at each milestone before building on it.

Nothing in this file exists yet. There is no mobile code in the repository.

---

## 1. Recommendation in short

1. **Phones come after desktop 1.0.** Only a time-boxed spike runs earlier, alongside the 0.6 helper relay.
2. **First a companion, then a limited standalone app. No PWA.**
3. **Companion:** the phone pairs with a desktop install and shows progress, "needs you" items and approvals. It talks through the same zero-knowledge relay the 0.6 helper feature uses; the relay only ever holds ciphertext. It is the helper's view for Dana and the "approve from the sofa" view for Pat.
4. **Standalone (later):** Email tier through the phone's own mail app, an Assisted tier in a guided in-app browser where the person taps Submit, the identity-safety checklists, and reminders. Personal details live only on the phone, encrypted. It does not run by itself in the background and the store text must say so.
5. **No Automatic browser tier on phones, ever, unless the platforms change.** iOS does not allow it and on Android it would mean either misusing the accessibility service or hiding an automated web view, both against our rules.
6. **Android first** (we can build it on our Linux machines, F-Droid suits the open-source audience), **iOS second** (needs the Apple account and a Mac build runner).
7. **Stack:** native user interface on each platform (Kotlin with Jetpack Compose, Swift with SwiftUI) over one small shared Rust core (pairing, encryption, message formats; later registry reading and letter rendering). The Python engine is not ported; its data (registry, state laws, checklists, letter templates, JSON schemas) is reused, and one conformance test suite keeps the two implementations in step.
8. **No account, no personal data on our servers, no analytics kit, no advertising identifier.** The phone apps follow the same seven principles as the desktop app.
9. **Paid tiers on phones are an open question**, because Apple forbids unlocking features with a licence key. Until the owner decides, the phone apps are free and sell nothing.
10. **Owner costs to decide:** Apple Developer Program 99 USD a year, Google Play 25 USD once, a business entity with a D-U-N-S number for organisation accounts, test phones.

---

## 2. What a phone cannot do (platform limits)

The desktop app's value is that it runs by itself every day: it drives a real browser, reads the removal mailbox and sends follow-ups. Most of that is not possible on a phone.

| Desktop capability | iOS | Android |
|---|---|---|
| Daily background run | The system decides when, and whether, a background task runs; refresh tasks get seconds and are not promised (BackgroundTasks framework, https://developer.apple.com/documentation/backgroundtasks/bgtaskscheduler; the page could not be machine-read on the day of writing, confirm in the spike). Background modes may only be used for their intended purposes (guideline 2.5.4). | Periodic work has a 15-minute minimum interval and "the exact time that the worker is going to be executed depends on the constraints ... and on the optimizations performed by the system" (https://developer.android.com/develop/background-work/background-tasks/persistent/getting-started/define-work). Battery savers on many phones delay it further. |
| Automatic browser tier (Playwright) | Not possible. Apps that browse the web must use WebKit (guideline 2.5.6); there is no headless browser and no background web view. | No Playwright. Driving the user's Chrome needs the accessibility service, which Play restricts (section 6). An invisible in-app web view would be automation dressed up as a person, which our rule against stealth forbids. |
| "Fill it in for me" in a visible browser | Possible in the foreground in an in-app web view: the app fills fields, the person ticks the box and taps Submit. How many broker sites accept an in-app web view is unknown. | Same. |
| Mailbox watching (IMAP) | Only while the app is open, plus rare background refreshes. | While the app is open, plus deferred periodic work. |
| Sending letters | Yes: through the system mail composer (the person taps Send), or SMTP while the app is open. | Yes: a `mailto:` handoff to the mail app, or SMTP. |
| Evidence screenshots of web pages | Only of the in-app web view. | Same. |
| Encrypted local store | Yes: Keychain and file protection. | Yes: Keystore. |
| Scheduled reminders | Yes: local notifications need no server. | Yes. |

Conclusion: a phone can be a good **window onto** the desktop engine and a good **guided, do-it-in-sessions** tool. It cannot be the hands-off engine.

---

## 3. Our principles on a phone

| Principle (`docs/ROADMAP.md`) | What it means here |
|---|---|
| Local-first, no PII on our servers | Personal details are stored only on the person's own devices. Anything that passes through our infrastructure is end-to-end encrypted and, by default, free of personal details even inside the ciphertext. |
| No account | No sign-up, no email address, no phone number, no Apple or Google sign-in. Devices pair with a QR code. This also matches Apple's guideline 5.1.1(v): "If your app doesn't include significant account-based features, let people use it without a login." |
| Honest by default | Store text says what the phone app does not do: it does not run by itself, and removal is requested, not promised. |
| The user is in charge | Consent stays on the protected person's own device. A helper's phone can remind and can approve only what was delegated. |
| Backups | Phone backups go to Apple or Google clouds. The encrypted store is excluded from cloud backup by default, with a plain explanation and an encrypted export file for moving to a new phone. |

---

## 4. The three options

| | (a) Companion to the desktop app | (b) Standalone phone app | (c) PWA |
|---|---|---|---|
| What the person gets | Progress, "needs you" items, approvals, helper view for family. The desktop does the work. | Email and Assisted tiers, checklists, reminders, on the phone alone. | A web app on a phone home screen. |
| Who it serves | Pat (approve from the phone), Dana (help parents remotely) | People with no computer; tablet users | Anyone with a browser |
| Engineering size | Small: pairing, encryption, a few screens | Large: registry, tiers, letters, storage, guided browser, twice | Medium, one codebase |
| Reuse | The 0.6 relay and its audited protocol | Registry data and letter templates; the shared core from (a) | Little: the engine is Python |
| Fits "no PII on our servers" | Yes, if the relay holds only ciphertext | Yes, everything is on the phone | Weak: the code is served by us on every visit, so a server compromise could read what the person types; this undoes the "open, checkable build" promise |
| Fits "no account" | Yes | Yes | Yes |
| Background work | Not needed on the phone | Reminders only | None. No mail sockets from a browser at all |
| Storage safety | Phone keystore | Phone keystore | Browser storage. Safari deletes script-writable storage "after seven days of Safari use without user interaction on the site" unless the web app is added to the home screen (https://webkit.org/blog/10218/full-third-party-cookie-blocking-and-more/) |
| Store risk | Low to medium (reviewers need a demo mode; paid-tier question in section 7) | Medium (in-app browser, personal-data rules, payments) | None, but no store presence either |
| Conflicts with our own rules | None | None | freemyid.org is script-free; a PWA needs scripts and a service worker, so it would have to live on another origin |
| Verdict | **Build first** | **Build second, with a narrow scope** | **Do not build** for anything that holds personal details. The static site's guides already work on phones. |

Why companion before standalone, even though part of our audience mostly uses a phone (`docs/POSITIONING.md`): the companion is small, reuses audited work, strengthens the Family plan, and cannot disappoint, because the desktop still does the real work. The standalone app is a second implementation of the core and delivers less than the desktop promise. If feedback mail shows that many people who want Free My ID have no computer at all, move the standalone app forward (decision M-7).

---

## 5. Recommended architecture

### 5.1 Pairing and transport
- **Pairing:** the desktop shows a QR code; the phone scans it. The code carries the desktop's public key, a random mailbox id and the relay address. Both screens then show a short code to compare, so a swapped QR code is caught. No account, no email.
- **Transport: zero-knowledge relay first, local network later.** Both sides make outgoing HTTPS connections to a relay that stores small encrypted messages for a limited time. This is the same service as the 0.6 desktop helper relay (`ROADMAP_TO_1.0.md`), so the phone adds no new server.
  - Why not local network only: the main helper (Dana) is not in her parents' house; a per-user Windows install cannot open the firewall for incoming connections without an administrator; and iOS shows a local-network permission prompt. Direct local delivery can be added later as a speed-up, never as the only path.
- **What the relay can see:** network addresses, times, message sizes, random mailbox ids. It cannot read messages and has no names or email addresses. It keeps no request logs with addresses. The site's safety page must say exactly this.
- **Encryption:** key agreement at pairing and authenticated encryption per message, from a reviewed library, never hand-written primitives. The protocol document and its test vectors live in the repository. The relay and the protocol are in the 0.9 audit scope.
- **Payloads:** PII-free by default, even inside the ciphertext: counts, site ids, to-do types, approve and decline. Sending details (for example the listing a person must confirm) is a separate switch (decision D10 in `ROADMAP_TO_1.0.md`).

### 5.2 Two kinds of paired phone
| | My own phone | A helper's phone |
|---|---|---|
| Sees | Status, to-dos, and (my choice) the details needed to finish a to-do on the phone | Counts and to-do types only, unless the protected person switched on more |
| May do | Approve the first email, say "go", finish an Assisted to-do in the phone's browser | Remind, and approve only what the protected person delegated |
| Never | | Give consent for the other person, switch off practice mode for them |

### 5.3 Notifications
- **Start without a push server.** The phone checks the relay when opened and in whatever background time the system grants. Be honest in the app: a notice may arrive hours late.
- **Optional later (decision M-5): content-free push** ("Free My ID has something for you", no names, no sites). This puts a push token on the relay and brings Apple's and Google's push services into the path. It must then be declared in the store privacy forms (section 8), and the F-Droid build must work without it.

### 5.4 Technology
| Layer | Choice | Why |
|---|---|---|
| Android UI | Kotlin, Jetpack Compose | Best accessibility (TalkBack, font scaling), builds on Linux, plain Gradle build that F-Droid can reproduce, no Google Play Services needed |
| iOS UI | Swift, SwiftUI | Best accessibility (VoiceOver, Dynamic Type), smallest review risk |
| Shared core | Rust, exposed to Kotlin and Swift through generated bindings (UniFFI) | One implementation of pairing, encryption and message formats for both phones; memory-safe; a pattern used by other privacy apps |
| Desktop side of the protocol | Python, using the `cryptography` package the app already ships | No new build chain in the desktop installers before 1.0. Shared test vectors keep Python and Rust in agreement. Moving the desktop onto the Rust core is a question for after 1.0. |
| Data reuse for the standalone app | Registry, state laws, checklists and JSON schemas exported as JSON at build time; the existing Jinja letter templates rendered by a Jinja-compatible Rust library | Reuse the knowledge, not the Python code |
| Parity | A conformance suite: input fixtures and the expected tier, letter text and minimised field list, generated from the Python engine and run against the Rust core in CI | Two implementations of privacy-critical rules must not drift |
| Local store | SQLite with app-level AES-GCM (as on desktop), key in the Android Keystore or iOS Keychain, optional biometric unlock | Same model as the desktop store |

Options looked at and not chosen:
- **React Native or Flutter:** one UI codebase, but the core logic would still be rewritten, the dependency tree is large (a supply-chain cost we avoid elsewhere), accessibility is weaker than native for our audience, and F-Droid builds are harder.
- **Kotlin Multiplatform core:** workable, but Rust gives one core that the desktop could also adopt later.
- **Embedding Python in the apps** (the same FastAPI pages in a web view): tempting, because it reuses the wizard. Not chosen as the default because the parts worth reusing on a phone are small, binary wheels for iOS and Android are not available for every dependency, the app becomes large, and a web view over a local server is closer to Apple's "repackaged website" line (guideline 4.2). The spike checks it once so the decision rests on facts.
- **PWA:** see section 4.

### 5.5 The standalone app's scope (when we build it)
| Tier | On the phone |
|---|---|
| **Email** | Default: the app writes the letter and opens the phone's mail composer; the person taps Send. No mailbox password is stored. Letters go out in small batches per session. Optional: SMTP and IMAP with an app password, checked while the app is open. |
| **Assisted** | Guided in-app browser on the opt-out page: numbered steps, the app fills the fields the listing already shows, the person ticks any box and taps Submit, the app records the result. Falls back to the phone's own browser with one Copy button per field. |
| **Automatic browser** | Not offered. |
| **Checklists** | Credit freezes and the other identity-safety lists: they are already "open the page, follow the steps". |
| **Re-checks** | Local reminders ("time for your monthly check, about 5 minutes"). |
| **Moving between devices** | The encrypted setup file format from 0.4, with its version byte. |
| **Not in scope** | Exposure scan across the registry, relist detection in the background, proof vault beyond what the person did in the app. |

The store text and the first screen say plainly: "This app helps you do it in a few minutes at a time. It does not run by itself. For that, use Free My ID on a computer."

---

## 6. Store rules that shape the design

| Rule | Text or summary | Effect on us |
|---|---|---|
| Apple 2.5.6 | "Apps that browse the web must use the appropriate WebKit framework" | In-app browser is a WKWebView; no other engine |
| Apple 2.5.2 | Apps may not "download, install, or execute code which introduces or changes features or functionality" | The registry feed must stay data (selectors, field names, steps), never script |
| Apple 4.2 | The app must be more than "a repackaged website" | Rules out a web wrapper; native screens |
| Apple 4.2.3(i) | "Your app should work on its own without requiring installation of another app" | A companion needs a real demo or practice mode so a reviewer, and a curious user, can use it without a desktop |
| Apple 5.1.1(viii) | "Apps that compile personal information from any source that is not directly from the user or without the user's explicit consent, even public databases, are not permitted" | We act only on the person's own details with their typed consent; each extra profile has its own consent. Explain this in the review notes. A listing search on the phone is the riskiest feature here. |
| Apple 5.1.1(v) | No login unless the app has significant account features | Fits us |
| Apple 5.1.2 | Disclose where personal data is shared and get permission | Our consent screen and per-request approval already do this; a removal request sends details to that one site |
| Apple 3.1.1 | "Apps may not use their own mechanisms to unlock content or functionality, such as license keys" | See section 7 |
| Google Play accessibility policy | Only apps whose primary purpose is helping people with disabilities may declare themselves accessibility tools; "automation tools" are named as not qualifying; other uses need a declaration, a prominent in-app disclosure and a video | We do not use the accessibility service at all |
| Google Play data safety | "'Collect' means transmitting data from your app off a user's device"; data processed only on the device, and data that is end-to-end encrypted and unreadable by us, is not "collected"; a privacy policy link is required even when nothing is collected | Our planned answer is "no data collected", as long as there is no push token and no crash reporting |
| Google Play payments | Features unlocked inside the app must use Play billing, and apps "may not lead users to a payment method other than Google Play's billing system", with programme exceptions | See section 7 |
| Google Play testing | Personal accounts created after 13 November 2023 must run a closed test with at least 12 testers for 14 days before production | Plan the beta around it, or use an organisation account |
| Android developer verification | From 30 September 2026 in Brazil, Indonesia, Singapore and Thailand, with a wider rollout planned for 2027, apps on certified devices must come from a verified developer, including apps installed outside Play; a preview "advanced flow" for power users exists | Direct APK and F-Droid installs will need us to register an identity too |
| F-Droid | Free software only, built from source with a free toolchain, no Google Play Services, Firebase or proprietary tracking; undisclosed anti-features lead to rejection | The Android app must build with no proprietary parts. The licence of the bundled registry sample (CC BY-NC) may earn an anti-feature label or a request for free-licensed data: ask F-Droid before building for it. |

Sources: https://developer.apple.com/app-store/review/guidelines/ ; https://support.google.com/googleplay/android-developer/answer/10964491 ; https://support.google.com/googleplay/android-developer/answer/10787469 ; https://support.google.com/googleplay/android-developer/answer/9858738 ; https://support.google.com/googleplay/android-developer/answer/14151465 ; https://developer.android.com/developer-verification ; https://f-droid.org/docs/Inclusion_Policy/

Nothing in Apple's guidelines names data brokers or opt-out tools, for or against. The risks above are our reading; only a real submission settles them.

---

## 7. Paid tiers on phones

Our model is a licence key bought on the web without an account. That collides with the stores:

- **Apple:** licence keys may not unlock features (3.1.1). Features bought elsewhere may be used in the app only if they are "also available as in-app purchases within the app" (3.1.3(b)). In the United States storefront, apps may currently include links to buy outside (3.1.1(a)).
- **Google Play:** unlocking features needs Play billing, with exceptions that depend on programme and region.

| Option | Effect |
|---|---|
| **A. Phone apps are free and sell nothing** (recommended to start) | No in-app purchase, no key entry on the phone. The companion shows whatever the paired desktop is entitled to. Risk: a reviewer may still see the helper view as a paid feature bought elsewhere. |
| B. Offer Plus and Family as in-app purchases too | Allowed by both stores. The purchase is tied to the Apple or Google account, not to an account with us, so "no account" still holds. The stores take a commission (Apple's small-business rate is 15 percent, https://developer.apple.com/app-store/small-business-program/). We need a way to turn a store receipt into our PII-free licence token. |
| C. Link out to the website for purchase | Allowed in the US App Store at the time of writing; restricted on Play. Fragile, because these rules are changing under court orders. |

Decision M-4. It does not block the companion beta; it blocks the store launch of anything tied to a paid plan.

---

## 8. Privacy labels and data-safety answers (planned)

| Form | Our planned answer | Holds only if |
|---|---|---|
| Apple privacy details (https://developer.apple.com/app-store/app-privacy-details/) | "Data not collected". Apple: "'Collect' refers to transmitting data off the device in a way that allows you and/or your third-party partners to access it for a period longer than what is necessary to service the transmitted request in real time", and "Data that is processed only on device is not 'collected'". | The relay keeps only ciphertext it cannot read, no logs with addresses, no analytics kit, no crash reporter, no push token |
| Google Play data safety | "No data collected, no data shared" | Same conditions |
| If content-free push is added | Declare a device identifier, used for app functionality, not linked to identity | Decision M-5 |
| If opt-in crash reports are added | Declare diagnostics, optional, user-initiated | Follows desktop decision D15 |
| Privacy policy link | Required by both stores even with nothing collected | The site's privacy policy page (0.8, `WEBSITE.md`) |

A test in CI should fail the build if an analytics, advertising or crash-reporting library appears in the dependency list.

---

## 9. Distribution and costs

| Channel | Cost | Notes |
|---|---|---|
| **F-Droid** (Android) | free | Fits our open-source audience (Sam). F-Droid builds from source and normally signs with its own key. Expect a review of the data licence. |
| **Direct APK from freemyid.org** | free today | For people who avoid stores. From the 2027 rollout it needs developer verification. The site must give the checksum and plain install steps. |
| **Google Play** | 25 USD once ("There is a US$25 one-time registration fee", https://support.google.com/googleplay/android-developer/answer/6112435) | Where Pat and Dana will look. An organisation account needs a D-U-N-S number (https://support.google.com/googleplay/android-developer/answer/13634885); a personal account needs the 12-tester closed test. |
| **Apple App Store** | 99 USD a year, the same membership as macOS notarization | The only practical channel on iOS in the United States. TestFlight for the beta. The fee waiver is for nonprofits, schools and government bodies that sell nothing (https://developer.apple.com/help/account/membership/fee-waivers/). |

No account is needed with us for any channel. Store accounts (Apple ID, Google account) belong to the person and are outside our control; the website keeps a direct APK path so that Android users are not forced through a store.

---

## 10. Milestones

Mobile is not on the 1.0 path. Only M0 runs before 1.0.

| Milestone | When | Scope | Exit criteria |
|---|---|---|---|
| **M0 Spike** | During 0.6, time-boxed | Protocol document and test vectors for the relay. An Android prototype pairs with a development desktop build by QR code and shows status. The Rust core builds for Android and iOS. One check of "Python inside the app" (do the binary wheels exist). On fixture pages only: can an in-app web view fill a form and detect success. | A decision memo: stack confirmed or changed, in-app browser viable or not, effort estimate for M1 to M5. No store account needed. |
| **M1 Companion alpha, Android** | After 1.0 | Pairing, status, "needs you" list, approvals for "my own phone", practice mode with a made-up person, large text, TalkBack. Installed from an APK by family testers. | Threat model reviewed by qa-security. Privacy proof tests: no personal value in any relay payload by default. Pat test on a phone. |
| **M2 Companion beta, both platforms** | After M1 | iOS app on TestFlight. Helper's-phone role. Play closed test (12 testers, 14 days if on a personal account). F-Droid submission started. | Works on the two newest OS versions of each platform. VoiceOver and TalkBack pass. Review notes and demo mode ready. |
| **M3 Companion in the stores** | After M2 | Store listings, privacy forms, the site's mobile page and help pages. | Accepted by both stores and F-Droid, or a written list of what each asked us to change. Support process covers phones. |
| **M4 Standalone beta, Android** | After M3 | Scope in section 5.5. Shared core grows to registry, tiers, letters, with the conformance suite. | Conformance suite green against the Python engine. Encrypted store reviewed. Honest store text approved against `docs/POSITIONING.md`. |
| **M5 Standalone in the stores, then iOS** | After M4 | iPhone and iPad version; paid-tier decision applied. | Same as M3, plus the payment path tested if option B was chosen. |

Why after 1.0:
1. The relay and its protocol ship in 0.6 and are audited in 0.9. The phone should build on the audited version.
2. 0.5 to 0.9 already carry three desktop installers, the feed, payments and the audit. A fourth and fifth platform would starve them.
3. Store accounts need the business entity (decision D3) and the Apple account (D2).
4. A phone cannot replace the desktop engine, so it cannot make 1.0 better; it can only make it later.

---

## 11. Who builds it

| Work | Team |
|---|---|
| Protocol, crypto core, threat model, review | In-house (security core stays in-house), qa-security |
| Android and iOS apps | In-house, with a new mobile engineer role under the orchestrator; design by the web and graphic design crew so the phone looks like the app and the site |
| Conformance vectors, protocol fuzz and property tests | Codex team |
| Relay client retry and queue behaviour on the desktop side, user pages for phones | Grok team |
| Relay service, mobile CI (Android on Linux runners with an emulator; iOS on macOS runners), signing, store uploads | Dana (devops) |
| Real-phone checks | The owner and family testers; agents cannot hold a phone |

---

## 12. Risks

| Risk | What we do |
|---|---|
| App Review reads the app as "compiling personal information" (5.1.1(viii)) | Consent-first design, review notes, practice mode with a made-up person; keep listing search off the phone at first |
| The helper view is treated as a paid feature that needs in-app purchase | Start with a free companion; decide M-4 before store launch |
| Broker sites refuse in-app web views | Measure in M0 and M4; fall back to the phone's own browser with Copy buttons; never disguise the web view |
| Background limits make notices late | Say so in the app; offer content-free push only by owner decision |
| A second implementation drifts from the Python engine | Conformance suite in CI; registry data is the single source |
| Android developer verification reaches the United States | Register early enough to keep direct APK and F-Droid installs working |
| Phone backups copy the encrypted store to a cloud | Exclude it by default; explain; offer the encrypted export file |
| Small team, two more platforms | Android first; iOS only after the Android companion is steady |

---

## Decisions the owner must make

| # | Decision | Options | Recommendation | Blocks |
|---|---|---|---|---|
| M-1 | Build phone apps at all, and when | After desktop 1.0; in parallel with 0.x; never | After 1.0, with the M0 spike during 0.6 | Everything below |
| M-2 | Google Play account, 25 USD once | Organisation account (needs the entity and a D-U-N-S number); personal account (12-tester closed test); F-Droid and APK only | Organisation account once the entity exists | M2 Play beta, M3 |
| M-3 | Apple Developer Program, 99 USD a year (same as desktop D2) | Join for macOS and reuse; skip iOS | Join; iOS follows Android | M2 on iOS, M3 |
| M-4 | Paid tiers on phones | A: phones free, sell nothing; B: in-app purchase as well; C: link out where allowed | A to start, revisit before M5 | M3 for anything paid, M5 |
| M-5 | Push notifications | None (poll only); content-free push through Apple and Google | None at first | A feature of M2 |
| M-6 | Developer identity for Android verification and store listings | Register the business entity; register the owner personally | The entity | Direct APK and F-Droid from the 2027 rollout; M3 |
| M-7 | Order of companion and standalone | Companion first; standalone first | Companion first, unless feedback shows most interested people have no computer | M1 to M5 order |
| M-8 | F-Droid data licence | Accept an anti-feature label; ship a free-licensed core data set; skip F-Droid | Ask F-Droid first, then decide | F-Droid in M2 |
| M-9 | Test phones | Family phones; buy one Android phone and one used iPhone | One of each, plus family testers | M1, M2 |
| M-10 | Tablets (iPad, Android tablets) | Phone layout only; tablet layout in the standalone app | Tablet layout with the standalone app, since many older people use a tablet as their computer | M4, M5 |
