# Broker registry sources

Registry: `brokers/registry.yaml`. Each broker entry cites its own `source_urls`; this file lists the shared sources and the access dates. Nothing in the registry is invented: every URL, email, phone and postal address was seen in a fetched page, a search result, the California CPPA registry CSV, or BADBOOL.

## Shared sources

| Source | URL | Accessed | Used for |
|---|---|---|---|
| BADBOOL (Big-Ass Data Broker Opt-Out List, third party) | https://github.com/yaelwrites/Big-Ass-Data-Broker-Opt-Out-List | 2026-11-05 | Opt-out URLs for most people-search sites (not primary; entries marked unverified) |
| Legacy seed list | `zzz_legacy/family-privacy-sweep-kit/family-privacy-sweep/data/brokers.json` | 2026-11-05 | Seed URLs only; re-checked |
| California CPPA data broker registry (2025 CSV) | https://cppa.ca.gov/data_broker_registry/registry2025.csv | 2026-11-06 | "Data broker primary contact email address", websites and CCPA request URLs for about 30 registered brokers; operator/ownership (Mississippi Tornado Alley LLC, BeenVerified subsidiaries, Spokeo sites). Only the file's first ~100k and last ~236k characters were scanned per name list; a broker absent from this note may still be in the file. The D8 bulk import (below) later covered the whole file |
| California CPPA registry page | https://cppa.ca.gov/data_broker_registry/ | 2026-11-06 | Registry structure; links to the CSV files (the current-year file listed 0 brokers) |
| California DROP | https://privacy.ca.gov/drop/ | 2026-11-05 | `ca_drop` |
| Spokeo privacy policy | https://www.spokeo.com/privacy-policy | 2026-11-06 | Spokeo contact addresses and request routes |
| Spokeo privacy page | https://www.spokeo.com/privacy | 2026-11-06 | Points to /optout |
| Cotality privacy policy | https://www.cotality.com/legal/privacy-policy | 2026-11-06 | Phone, portal, privacy@cotality.com |
| LiveRamp privacy choices | https://liveramp.com/privacy/my-privacy-choices | 2026-11-06 | Request types, phone, consumercare@liveramp.com |
| LiveRamp opt-out index | https://liveramp.com/opt_out/ | 2026-11-05 | Portal URL |
| ZoomInfo trust center | https://www.zoominfo.com/trust-center/your-privacy/ | 2026-11-06 | Removal URL; stateremoval@ is covered-persons only |
| Acxiom opt-out / privacy | https://www.acxiom.com/optout/ , https://www.acxiom.com/privacy/ | 2026-11-06 / 2026-11-05 | Opt-out options, phone, postal |
| LexisNexis consumer opt-out | https://consumer.risk.lexisnexis.com/opt | 2026-11-06 | Options, phone |
| Innovis opt-out | https://www.innovis.com/personal/lc_optOut | 2026-11-06 | Prescreen routing, DMAchoice |
| SearchPeopleFree opt-out | https://www.searchpeoplefree.com/opt-out | 2026-11-06 | Visible fields and button text |
| PeopleSearchNow opt-out | https://www.peoplesearchnow.com/opt-out | 2026-11-06 | Visible fields and button text |
| Experian, Equifax, Epsilon, Apollo, Lusha, RocketReach pages | see each entry's `source_urls` | 2026-11-05 | Opt-out routes |
| Radaris privacy page, PeekYou contact page | https://radaris.com/control/privacy , https://www.peekyou.com/contact/ | 2026-11-05 | Domains now controlled by Atlas Data Privacy Corporation; entries disabled |
| Third-party opt-out guides (Optery, DeleteMe, Incogni, offlist.me, etc.) | web search results | 2026-11-06 | Leads only (e.g. InfoTracer privacy@, confirmation-email senders); never sole support for an unmarked claim |

## Wave 2 (v1 email tier + plain-language steps), 2026-11-06

Progress notes (checkpointed once; the editing tool available to this run could only rewrite the file in one pass):
- Batch 1 (ca_drop through usphonebook): email channels added or confirmed; steps rewritten.
- Batch 2 (familytreenow through peekyou): same.
- Batch 3 (acxiom through google_results_about_you): same, plus `ca_registered` set from the registry CSV.

Email channels: 29 brokers now carry `opt_out_email` (10 before). Origin of each address:
- Broker's own page: spokeo (CustomerCare@, policy), liveramp (consumercare@, page), cotality (privacy@, policy), zoominfo (policy names only stateremoval@; see below).
- Broker-owned help article via search result: rocketreach, oracle (EOL FAQ via search; PDF not fetched).
- BADBOOL only: mylife, usphonebook.
- CA registry "primary contact email" (a registered contact; the broker has not stated that it accepts requests by email): whitepages, intelius, instantcheckmate, truthfinder, peoplefinders, truepeoplesearch, nuwber, familytreenow, checkpeople, socialcatfish, unmask, spyfly, epsilon, zoominfo (privacy@), apollo, lusha, pipl, verisk, experian, equifax, transunion.
- Third-party guides only (unconfirmed): infotracer (privacy@infotracer.com).

Not recorded because the address is not on the broker's own domains (the `Broker` validator requires this): BeenVerified (registry contact privacy@moneybot5000.com), Mississippi Tornado Alley LLC sites (privacy@mtalley.zendesk.com), Radaris and PeekYou (support@atlas.net), US Search/Intelius cross-domain, That's Them (legal@spokeo.com), LexisNexis (consumer.documents@lexisnexisrisk.com, also looks like a document intake mailbox). Acxiom's registry contact is a named individual, not recorded.

## D8 bulk import from state data broker registries, 2026-11-06

Goal: give every registered broker with an on-domain contact email an `email`-method entry so Free My ID can send it a deletion request (the Incogni model).

Sources attempted:
| Registry | URL | Result |
|---|---|---|
| California CPPA (2025 CSV, newest; `registry2026.csv` returned 404) | https://cppa.ca.gov/data_broker_registry/registry2025.csv | Fetched whole file in four overlapping 100,000-character windows (offsets 0, 95000, 195000, 290000 of 336,849 chars). Source of all imports |
| Vermont Secretary of State | https://sos.vermont.gov/data-brokers/ | HTTP 404. Search results say the registry is a searchable portal (no bulk file seen). Not imported |
| Texas Secretary of State | https://www.sos.texas.gov/statdoc/data-brokers.shtml | Page loads; registry is an Appian portal (https://texas-sos.appianportalsgov.com/data-broker-registry), JS search, no list or download visible. Not imported |
| Oregon DFR/DCBS | https://dfr.oregon.gov/business/licensing/data-broker-registry | Page loads; only links to licence-search portals (www4.cbs.state.or.us, ordcbs.mylicense.com), no list. Contact for a full list: dfr.ndp.licensing@dcbs.oregon.gov. Not imported |

Method and limits: the fetch tool summarises pages through a small model, so rows were extracted by prompt, not parsed by script. Overlapping windows were used so boundary rows were not lost. Treat the extraction as high-confidence but not byte-exact; the CSV should be re-parsed by script when a shell is available (check each `opt_out_email` against the CSV).

Rules applied: keep only rows whose email host is on the broker's own website domain; skip rows already in the registry (matched by domain or name); one entry per registrable domain (e.g. Deep Sync, Deloitte, Nielsen/eXelate, Ziff Davis, FinThrive, Precisely/PlaceIQ each appear once); skip addresses that look like a named individual's mailbox (not a privacy desk). Fields per entry: method `email`, priority 20, `verification_status: unverified`, `ca_registered: true`, `recheck_interval_days: 90`, `typical_processing_days: 45`, source_urls = the CSV.

Output location: superseded. The orchestrator re-did the import deterministically with `tools/import_ca_registry.py`, which reads the CSV directly, because the fetch-tool extraction above was model-summarized. Result: 365 imported into the generated block at the end of `registry.yaml`. Skipped: 57 off-domain, 79 non-role (personal-looking) mailboxes, 41 already curated, 1 with no email. Vermont, Texas and Oregon have no downloadable list (see above).

Progress note for a later run: California CSV fully covered (all four windows done). Remaining work: re-check emails by script; fetch Vermont/Texas/Oregon if a bulk export or accessible listing is found.

## Website claims

Checked 2026-11-06.

**(a) "Google usually drops the page over the following weeks" — verdict: reword.** No Google source gives a timeline. Google says only that if the site owner removes the info it "will eventually be removed from Google Search as part of our regular updating process", and offers the Outdated content refresh tool to speed this up. Proposed wording: "Once the site has removed your listing, Google drops the page on its own schedule, which can take a while. Google's 'Refresh outdated content' tool can speed it up." Sources: https://support.google.com/websearch/answer/12719076 (accessed via search summary, 2026-11-06); https://support.google.com/websearch/answer/6349986 (fetched 2026-11-06; says stale results are fixed via a refresh request, gives no timeframe); https://support.google.com/websearch/answer/9673730 (search summary only).

**(b) "registered as a data broker in California" where `ca_registered: true` — verdict: confirmed, with a caveat.** The field was set in Wave 2 batch 3 and by `tools/import_ca_registry.py` from the CPPA 2025 CSV (https://cppa.ca.gov/data_broker_registry/registry2025.csv); it means "listed in the 2025 registration year". The 2026 file does not exist (404), so a broker could have registered for 2026 or lapsed since. Spot checks against the CSV (fetched 2026-11-06): Spokeo, Inc. (www.spokeo.com; also freepeopledirectory.com, peoplewin.com, thatsthem.com), Whitepages, Inc (www.whitepages.com), Intelius, LLC (www.intelius.com) and BeenVerified, Inc. (beenverified.com, peoplelooker.com and others) are all listed. Safer wording if desired: "listed on California's data broker registry". Registry background: https://cppa.ca.gov/data_brokers/ (search result, 2026-11-06). Not independently re-checked here: peoplefinders, truepeoplesearch, nuwber (earlier notes cite the same CSV).

## Website claims: comparison (R5)

Board row R5, decision D4. Checked 2026-11-07. Column: "Paid removal services (typical)", no company named on the site. Services checked: DeleteMe, Optery, Incogni, Kanary, EasyOptOuts, Privacy Bee, Aura. Method: public pages fetched through the summarising fetch tool (not byte-exact), so every cell is limited to what the pages plainly state. The fetch tool could not read some pages (404): incogni.com/how-it-works, optery.com/how-it-works, joindeleteme.com/privacy-policy, joindeleteme.com/privacy, kanary.com/privacy, easyoptouts.com/faq (400). Aura was checked but is a broader identity-protection bundle; it does not state who sends the broker requests, so it is not counted as support for any row. Plan prices and features change often; re-check before launch.

Verdict table (SUPPORTED = at least 4 services state it; the approved cell wording is the only wording to use):

| # | Row | Verdict | Approved cell (max 8 words) |
|---|---|---|---|
| 1 | Price model | SUPPORTED | "Yearly or monthly fee" |
| 2 | Where your details go | SOFTEN | "Sent to the company" |
| 3 | Account required | SUPPORTED | "Account required" |
| 4 | Who sends the requests | SUPPORTED | "The company, on your behalf" |
| 5 | Open to inspection | DROP | none (no page states closed source; absence is not evidence) |
| 6 | Keeps checking | SUPPORTED | "Yes, on a schedule" |
| 7 | Works on (any device / browser) | DROP | none (pages are silent; not a differentiator) |
| 8 | Staff handle hard cases | SOFTEN | "Often, on higher plans" |

Notes on the cells:
- Row 2: only Incogni's policy says it stores your data (name, address, email, date of birth; account password; support call recordings). DeleteMe, Optery, Kanary and Privacy Bee all require you to hand over name, locations and similar details, but no page we could read says "uploaded to our servers". "Uploaded" and "on their servers" are therefore not approved; "sent to the company" is true of all six.
- Row 5: none of the services' pages say whether the code is open or closed. We did not search for public code repositories of each service. Do not write "closed source" or "not open source" about them. If the table needs the point, state it only on the Free My ID side ("Open source, you can read it").
- Row 7: no service page lists supported devices or browsers (Aura lists device counts for its security bundle only; Privacy Bee and Kanary link to iOS/Android apps and a web dashboard). The services are web-based, so "works on any device" would be a plausible but unsupported claim, and it would not favour Free My ID, which is Windows-only in v1 (macOS and Linux are roadmap). Recommend dropping the row.
- Row 8: Optery Core has no human agent (Extended and Ultimate do); Incogni's custom removals are on Unlimited plans; Privacy Bee Essentials is automated (Pro adds human analysts); EasyOptOuts is "100% automated" with no stated staff handling of hard cases. So "often" with "on higher plans" is the supportable form; plain "yes" is not.
- Row 6: true, but Free My ID also re-checks, so it is a parity row, not a differentiator. EasyOptOuts re-scans only every four months, Optery Free Basic gives quarterly reports; do not write "monthly" or "continuous".
- Row 4: Optery's Free Basic tier is self-service, so the wording is "typical", not "all". Aura does not state who submits.
- Row 1: Aura and Privacy Bee are monthly-billed subscriptions, the others yearly (EasyOptOuts yearly only, Kanary Core yearly); "Yearly or monthly fee" holds in aggregate. Do not state a price figure; Incogni's own pricing page and FAQ disagree about the monthly price.

Citations, one per service per row (access date 2026-11-07). "n/s" = page fetched but did not state it (does not count as support); "n/r" = not read (404).

Row 1, price model (yearly/monthly fee):
- DeleteMe: https://joindeleteme.com/pricing/ (annual plans, 1- or 2-year terms, auto-renew)
- Optery: https://www.optery.com/pricing/ (monthly or yearly billing)
- Incogni: https://incogni.com/pricing (monthly or annual)
- Kanary: https://www.kanary.com/pricing ($250 or $500 per year; monthly for teams)
- EasyOptOuts: https://easyoptouts.com/ ($19.99 per year)
- Privacy Bee: https://www.privacybee.com/pricing (monthly subscription, annual discount)
- Aura: https://www.aura.com/pricing (monthly or annual; bundle)

Row 2, where your details go (sent to the company):
- DeleteMe: https://joindeleteme.com/pricing/ ("tell us exactly what information you want deleted")
- Optery: https://www.optery.com/pricing/ (name variations, past cities, phone and email preferences)
- Incogni: https://incogni.com/privacy-policy (collects and stores name, address, email, date of birth; the only explicit "stores")
- Kanary: https://www.kanary.com/pricing (name, city/state, birth year); https://www.kanary.com/faq (identity verification)
- EasyOptOuts: https://easyoptouts.com/ ("some basic information"; fields not listed, n/s on storage)
- Privacy Bee: https://www.privacybee.com/pricing (profile fields; optional Limited Power of Attorney)
- Aura: n/s (https://www.aura.com/pricing mentions identity verification only)

Row 3, account required:
- DeleteMe: https://joindeleteme.com/pricing/ (FAQ: log in to "your DeleteMe personal profile page"; implied)
- Optery: https://www.optery.com/pricing/ (signup required, even for Free Basic)
- Incogni: https://incogni.com/privacy-policy (email "used for account creation"); https://incogni.com/pricing (dashboard)
- Kanary: https://www.kanary.com/pricing (registration page); https://www.kanary.com/faq (web dashboard, apps, SSO)
- EasyOptOuts: https://easyoptouts.com/ (must sign up)
- Privacy Bee: https://www.privacybee.com/pricing (free account, dashboard)
- Aura: https://www.aura.com/pricing (sign-in at my.aura.com; implied)

Row 4, who sends the requests (the company, on your behalf):
- DeleteMe: https://joindeleteme.com/pricing/ ("our privacy experts take it from there")
- Optery: https://www.optery.com/pricing/ (Core and up automated by Optery); https://www.optery.com/privacy/ (submits Delete My Data / Do Not Sell "on your behalf"). Free Basic is self-service
- Incogni: https://incogni.com/pricing ("handles opt-out requests for you"); https://incogni.com/privacy-policy ("authorize us to act as your agent")
- Kanary: https://www.kanary.com/faq (Kanary's team submits; approve/deny check for unfamiliar sites)
- EasyOptOuts: https://easyoptouts.com/ ("100% Automated", bot-driven; the company's software sends)
- Privacy Bee: https://www.privacybee.com/pricing (Privacy Bee handles; Essentials mostly automated)
- Aura: n/s (https://www.aura.com/pricing says it "helps remove", not who submits)

Row 5, open to inspection (DROP, nothing stated):
- DeleteMe: https://joindeleteme.com/pricing/ (n/s; "built and run by Abine, Inc.")
- Optery: https://www.optery.com/pricing/ (n/s)
- Incogni: https://incogni.com/pricing (n/s)
- Kanary: https://www.kanary.com/faq (n/s)
- EasyOptOuts: https://easyoptouts.com/ (n/s)
- Privacy Bee: https://www.privacybee.com/pricing (n/s)
- Aura: https://www.aura.com/pricing (n/s)

Row 6, keeps checking:
- DeleteMe: https://joindeleteme.com/pricing/ (quarterly privacy reports, new opt-outs added all year)
- Optery: https://www.optery.com/pricing/ (Core: monthly automated scans and removals; Free Basic: quarterly reports)
- Incogni: https://incogni.com/pricing ("recurring removals", year-round monitoring on annual plans)
- Kanary: https://www.kanary.com/pricing (monthly scans); https://www.kanary.com/faq (adds new sites, monitoring)
- EasyOptOuts: https://easyoptouts.com/ (another scan every four months)
- Privacy Bee: https://www.privacybee.com/pricing (continuous monitoring, monthly reports)
- Aura: https://www.aura.com/pricing (credit and dark-web monitoring; not broker re-checks, so no support)

Row 7, works on any device / browser (DROP, nothing stated):
- DeleteMe: https://joindeleteme.com/pricing/ (n/s)
- Optery: https://www.optery.com/pricing/ (n/s)
- Incogni: https://incogni.com/pricing (n/s)
- Kanary: https://www.kanary.com/pricing (mobile app mentioned; no device list)
- EasyOptOuts: https://easyoptouts.com/ (n/s)
- Privacy Bee: https://www.privacybee.com/pricing (links to iOS and Android apps; no requirements)
- Aura: https://www.aura.com/pricing (device counts per plan; security bundle, not removal)

Row 8, staff handle hard cases (often, on higher plans):
- DeleteMe: https://joindeleteme.com/pricing/ ("Personal DeleteMe Expert", email, chat and phone support)
- Optery: https://www.optery.com/pricing/ (human Privacy Agent on Extended and Ultimate only)
- Incogni: https://incogni.com/pricing (privacy specialists for custom removals on Unlimited plans)
- Kanary: https://www.kanary.com/faq (escalation and expert support; Advanced adds priority support)
- EasyOptOuts: https://easyoptouts.com/ (fully automated; staff role for hard cases n/s)
- Privacy Bee: https://www.privacybee.com/pricing (human analysts on Pro and Signature; Essentials automated)
- Aura: https://www.aura.com/pricing (24/7 support and fraud remediation team; not stated for broker removal)

## Wave 3 (verified-coverage growth), 2026-11-12

Method: plain `curl` fetch (generic User-Agent, 1 request per second, no retries around bot protection) of each opt-out or privacy-rights page; an entry is `verified` only when the page loaded (HTTP 200, no challenge) and its text matches the route recorded. Pages behind Cloudflare, Radware or similar checks stay `unverified` with the reason in `verification_notes`. No request was submitted and no email was sent.

| Source | URL | Accessed | Used for |
|---|---|---|---|
| California CPPA data broker registry CSV ("Last Updated 10/30/2026") | https://cppa.ca.gov/data_broker_registry/registry.csv | 2026-11-12 | Broker names, DBAs, websites, contact emails and the "how to exercise rights" page for batch 1 |
| BADBOOL (yaelwrites) | https://raw.githubusercontent.com/yaelwrites/Big-Ass-Data-Broker-Opt-Out-List/master/README.md | 2026-11-12 | Re-read for people-search opt-out pages (updated 2026-10-31) |
| InfoPay / Intermedia / Globicom "Your Privacy Choices" pages | https://staterecords.org/optout , https://courtrecords.us/optout/ , https://californiacourtrecords.us/optout/ , https://recordsfinder.com/optout/ , https://propertychecker.com/optout , https://www.statecourts.org/optout/ , https://courtcasefinder.com/optout , https://entitycheck.com/optout , https://sentinex.com/optout , https://goodcar.com/optout , https://members.idstrong.com/opt-out/ , https://infotracer.com/optout/ | 2026-11-12 | Eleven sister-site entries and the InfoTracer upgrade |
| Digital Safety Products / Scalable Commerce help-center requests | https://www.publicinfoservices.com/help-center/privacy-requests , https://www.searchpublicrecords.com/help-center/privacy-requests , https://www.quickpublicrecords.com/help-center/privacy-requests , https://www.publicdatacheck.com/help-center/privacy-requests | 2026-11-12 | Form fields and identity-verification step |
| Spy Dialer, BIGDBM, LocateSmarter opt-out pages | https://www.spydialer.com/optout , https://optout.bigdbm.com/ , https://locatesmarter.com/optout-form/ | 2026-11-12 | Form fields and routes |
| SmartBackgroundChecks, USA People Search, Archives.com, Social Catfish, Pipl, CheckPeople, SearchQuarry opt-out pages | see each entry's `source_urls` | 2026-11-12 | Upgraded from unverified |
| Radaris and PeekYou notices | https://radaris.com/control/privacy , https://www.peekyou.com/contact/ | 2026-11-12 | Both domains show a court-ordered transfer to Atlas Data Privacy Corporation; entries marked broken and disabled |
| 35 marketing / data-broker privacy pages | see each entry's `source_urls` | 2026-11-12 | Email routes (generated CA-registry entries replaced by curated, page-checked entries) |

Batch 2-3 additions (2026-11-12):

| Source | URL | Accessed | Used for |
|---|---|---|---|
| Privacy Shield opt-out manual 2026 (third party, leads only) | https://github.com/thumpersecure/opt-out-manual-2026 (docs/data.js) | 2026-11-12 | Opt-out page leads for Sync.me, TennHelp, Wyty, Glad I Know, Locate Family, National Cellular Directory, AddressSearch, Absolute People Search; each page was fetched and checked before an entry was written |
| Broker privacy pages and request forms (OneTrust, datasubject.com, own forms) | see each entry's `source_urls` | 2026-11-12 | 22 form-route entries and 21 more email-route entries (generated CA entries replaced by page-checked ones) |
| Court-transfer notices (Atlas Data Privacy Corporation) | pub360.com, revealname.com, telephonedirectories.us, veriforia.com, dataveria.com, newenglandfacts.com, golookup.com, centeda.com, corporationwiki.com (each /control/privacy or equivalent), grey-pages.com (seized notice) | 2026-11-12 | Not added to the registry; listed in the wave report as dead domains |

Batch 4-5 additions (2026-11-12):

| Source | URL | Accessed | Used for |
|---|---|---|---|
| Opt-out manual 2026, data-broker list (domains only, third party) | https://github.com/thumpersecure/opt-out-manual-2026 (docs/data.js, dataBrokerSites) | 2026-11-12 | 17 marketing/B2B broker domains; each site's own privacy pages were found from its home page and fetched |
| Broker privacy pages and do-not-sell forms for 47 CA-registry brokers | see each entry's `source_urls` | 2026-11-12 | Generated email entries replaced by curated, page-checked entries (email or form route) |
| DeepSync privacy portal | https://privacy.deepsync.com/request/data | 2026-11-12 | DeepSync, CompactLists, Accudata |

Wave 4 batch 1 (2026-11-12 and 2026-11-13):

| Source | URL | Accessed | Used for |
|---|---|---|---|
| Each broker's own privacy or opt-out page (plain fetch, 1 request/sec, no bot protection worked around) | see each entry's `source_urls` | 2026-11-12 / 2026-11-13 | 49 generated entries and 36 older entries upgraded to verified; new verified entries CallerSmart, Public Record Reports, SignalHire, Searchbug, RealtyTrac, PhoneLookup, FastBackgroundCheck, Truecaller |
| DeleteMe opt-out guide index and per-site guides (third party, leads only) | https://joindeleteme.com/opt-out-guides/ | 2026-11-13 | Site names and opt-out URLs for people-search and background-check sites; every URL was fetched before use |
| Court-transfer notices (Atlas Data Privacy Corporation) | pub360.com, revealname.com, golookup.com, kwold.com, rehold.com (home pages) | 2026-11-12 | Five entries marked broken and disabled |

Wave 4 batch 2 (2026-11-13):

| Source | URL | Accessed | Used for |
|---|---|---|---|
| DeleteMe opt-out guides (third party, leads only: site name and privacy-page link) | https://joindeleteme.com/opt-out-guides/ (668 guides) | 2026-11-13 | 125 new entries (B2B, marketing, analytics and a few people-search brokers); each site's home page and privacy or opt-out page was fetched; 62 verified, the rest unverified with the reason in `verification_notes` |
| Each broker's own pages | see each entry's `source_urls` | 2026-11-13 | FastBackgroundCheck /optout, Truecaller /unlisting, hibu CCPA page (Yellow Book), BlockShopper /donotsell, Hiya privacy page; Datafinder marked broken (retired notice) |
| Company home pages (names only) | consumercanvas.net, fideo.ai, censia.com, melissa.com, bestpickreports.com, 33mileradius.com, remodeling.com, keywordconnects.com | 2026-11-13 | Corrected display names |

Wave 4 audit (2026-11-13): the DeleteMe-index batch was checked against the California CPPA data broker registry (https://cppa.ca.gov/data_broker_registry/registry.csv and registry2025.csv, accessed 2026-11-13) and each site's own home page. 46 entries that are not data brokers or have no evidence of selling personal data were removed, and 14 same-company pairs were merged. The DeleteMe "feed" RSS link had been read as a guide and produced a bogus wordpress entry.
