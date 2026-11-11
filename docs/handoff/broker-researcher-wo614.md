# broker-researcher handoff: WO-614 / WO-615 (Priya Shah, 2026-11-11)

Deliverable: `docs/research/AUTOMATION_ROUTES.md` (Part A = WO-614 per broker, Part B = WO-615 routes with go/no-go and proposed WOs).
Tools this run: Read, Write, WebFetch, WebSearch only (no shell, no git, no grep, no registry validate). Registry and code untouched. Nothing committed: Morgan, commit both files as Priya Shah [freemyid] with explicit paths:
`docs/research/AUTOMATION_ROUTES.md docs/handoff/broker-researcher-wo614.md`

## Done
- WO-614 task 1 (research part): 25 broker ids plus 8 sibling sites covered, grouped into parent families. Every value carries an evidence label (PRIMARY / REGISTRY / SECONDARY) and a check date of 2026-11-11.
- WO-615 deliverable: 12 routes, 6 GO (or GO as handoff/checklist), 4 NO-GO, 2 WATCH; one proposed WO per GO (WO-A..F in the doc).
- I could not grep the private registry, so ids come from `docs/research/exposure_scan_patterns.yaml`. Map them to the real 20 WO-601 ids before adding values.

## Proposed Broker fields (contract review, Morgan)
WO-614 names two fields. Acceptance criterion 1 ("every value has a citation") needs somewhere to put the citation, so I propose four more small ones:

```yaml
optout_needs_listing_url: false        # bool | null (null = unknown). true = no removal without the listing URL.
optout_parent: mtalley                 # str | null. Group id; brokers with the same value get ONE search-free request.
search_free_route: email               # enum | null: email | form_name_state | portal | law_form | postal | phone_only | none
optout_route_evidence: registry        # enum: primary | registry | secondary
optout_route_sources: [https://cppa.ca.gov/data_broker_registry/registry2025.csv]   # list[HttpUrl], at least 1 when the fields above are set
optout_route_checked: 2026-11-11       # date
```
Validator ideas: if `optout_needs_listing_url` is false then `search_free_route` and `optout_route_sources` must be set; `optout_parent` must equal some broker id or a declared group id; `optout_route_evidence: secondary` must never coexist with `verification_status: verified` for the same route.
Runner rule I suggest: Email tier only when `search_free_route: email` AND evidence is `registry` or `primary`. `portal` goes to Assisted (WO-612 window). `secondary`-only routes stay a hand-check until a person confirms.

Also wanted (separate CR, WO-E): a site-status value for seized domains (radaris, peekyou now show Atlas Data Privacy Corporation notices). Today the only option is `enabled: false` plus notes.

Parent group ids I used: `mtalley` (9 sites), `spokeo`, `whitepages`, `beenverified`, `peopleconnect`, `atlas` (seized, not a removal group).

## Per-broker field proposals (copy after id mapping)
| id | optout_needs_listing_url | optout_parent | search_free_route | evidence | key source |
|---|---|---|---|---|---|
| fastpeoplesearch | false | mtalley | email (privacy@mtalley.zendesk.com) | registry | CPPA CSV 2025 |
| peoplesearchnow | false | mtalley | law_form (/privacy-rights; listing URL optional, phone required) | primary | peoplesearchnow.com/privacy-rights |
| usphonebook | false | mtalley | email | registry | CPPA CSV |
| searchpeoplefree | false | mtalley | email | registry | CPPA CSV |
| smartbackgroundchecks | false | mtalley | email | registry | CPPA CSV |
| advancedbackgroundchecks | false | mtalley | email | registry | CPPA CSV |
| cyberbackgroundchecks / fastbackgroundcheck / usapeoplesearch (if in registry) | false | mtalley | email | registry | CPPA CSV |
| truepeoplesearch | false | null | email (support@truepeoplesearch.com) | registry | CPPA CSV |
| familytreenow | false | null | email (support@familytreenow.com) | registry | CPPA CSV |
| spokeo | true | spokeo | null | primary (2026-11-07 browser) | spokeo.com/optout |
| thatsthem | false | spokeo (company only; do NOT set covered_by: spokeo) | form_name_state | secondary | thatsthem.com/optout (403) |
| whitepages | true | whitepages | null | secondary | guides; CPPA CSV contact legal@whitepages.com |
| 411 | true | whitepages | null (covered_by whitepages) | secondary | guides |
| beenverified | false | beenverified | portal (email fallback privacy@moneybot5000.com) | registry + secondary | CPPA CSV |
| peoplelooker | false | beenverified | portal | registry + secondary | CPPA CSV |
| intelius / truthfinder / instantcheckmate / ussearch | false | peopleconnect | portal | secondary | guides; portal shows title only |
| peoplefinders | false | null | portal (email fallback customercare@peoplefinders.com) | registry + secondary | CPPA CSV |
| nuwber | true | null | email (support@nuwber.com) | registry | CPPA CSV |
| mylife | true | null | email (membersupport@mylife.com) | registry | CPPA CSV |
| radaris | n/a | atlas | none | primary | radaris.com notice |
| peekyou | n/a | atlas | none | primary | peekyou.com notice |
| clustrmaps | null | null | none for now | DNS failure | recheck |
| cocofinder, veripages | null | null | null | none | pages 403 |
Note: "needs_url true" brokers can still get an email (nuwber, mylife): the field says the FORM needs a URL; `search_free_route` says what works without one.

## Open questions
1. mtalley: the registry promise ("applied across all of these sites") is worded for the opt-out of sale. Does one removal clear all nine sites? WO-616 should measure it. Until then: one request per group, recheck every site.
2. Do brokers act on email at all when they have a web form? Untested for every group. Track replies; WO-602 wording ("not checked, we asked anyway") fits.
3. PeopleSearchNow /privacy-rights requires a phone number; PeopleConnect requires DOB. Both are outside rule 6 defaults. Owner/Morgan: use only with the permission flag, or skip?
4. PeopleConnect reportedly refuses requests from services acting for a customer (DeleteMe help centre, secondary). Free My ID acts from the person's own mailbox and PC; does Morgan agree that is the person acting, not an agent?
5. Law-state vs non-law-state wording: NC/SC/AZ have no deletion right. PeopleFinders reportedly honours only law states (unconfirmed). Letters for family states must be courtesy requests.
6. ClustrMaps DNS failure may be local to the research host. Someone with a normal connection should try it.
7. PeopleConnect, Intelius, TruthFinder, Instant Checkmate rows were not found in my chunked reads of the CPPA CSV; a local grep of the CSV would settle it.
8. ThatsThem: the registry lists it under Spokeo, Inc. If our registry has `covered_by: spokeo` for thatsthem, that is wrong (separate form).

## Needs a human with a browser
fastpeoplesearch.com/removal vs /optout; truepeoplesearch.com/removal; thatsthem.com/optout fields; beenverified opt-out fields (2026 guide says age/street/ZIP added); suppression.peopleconnect.us fields; whitepages email fallback address.
