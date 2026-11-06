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
