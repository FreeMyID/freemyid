# Broker registry sources

Registry: `brokers/registry.yaml`. Each broker entry cites its own `source_urls`; this file lists the shared sources and the access dates. Nothing in the registry is invented: every URL, email, phone and postal address was seen in a fetched page, a search result, the California CPPA registry CSV, or BADBOOL.

## Shared sources

| Source | URL | Accessed | Used for |
|---|---|---|---|
| BADBOOL (Big-Ass Data Broker Opt-Out List, third party) | https://github.com/yaelwrites/Big-Ass-Data-Broker-Opt-Out-List | 2026-11-05 | Opt-out URLs for most people-search sites (not primary; entries marked unverified) |
| Legacy seed list | `zzz_legacy/family-privacy-sweep-kit/family-privacy-sweep/data/brokers.json` | 2026-11-05 | Seed URLs only; re-checked |
| California CPPA data broker registry (2025 CSV) | https://cppa.ca.gov/data_broker_registry/registry2025.csv | 2026-11-06 | "Data broker primary contact email address", websites and CCPA request URLs for about 30 registered brokers; operator/ownership (Mississippi Tornado Alley LLC, BeenVerified subsidiaries, Spokeo sites). Only the file's first ~100k and last ~236k characters were scanned per name list; a broker absent from this note may still be in the file |
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
