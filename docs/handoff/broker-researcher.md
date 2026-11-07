# broker-researcher handoff (post-v0.1.0 wave, 2026-11-07)

## What changed
No data files were changed. This run had only read, write and fetch tools, with no in-place edit and no shell. Rewriting the 675-line sample or the private full registry by hand risked corrupting them, so I left them alone. The findings below are ready to apply.

## Task 1: re-verify registry.sample.yaml (fetched 2026-11-07)
- Reloaded and matched the stored entry, so nothing stale found: acxiom (opt-out, phone 1-877-774-2094, Conway AR address, 2-week processing), liveramp (portal; phone (844) 678-0045 code 4; consumercare@liveramp.com appears only for proof-of-residency documents, not as a deletion intake), experian (opting_out page: direct mail, telemarketing, email, targeted advertising, preapproved offers), cotality (policy text unchanged; portal URL still not shown), radaris (still the Atlas Data Privacy transfer notice, judgment 2026-08-27, contact support@atlas.net), ca_drop (privacy.ca.gov/drop: portal consumer.drop.privacy.ca.gov; brokers must check DROP every 45 days from 2026-08-01; status updates up to 90 days).
- searchpeoplefree: page still loads. The fields and button match. The page also shows a success string, "You have successfully validated your email and started the record removal process." That is the post-email-link step, not final confirmation, so I did not add it to success_text.
- peoplesearchnow: page still loads and the button matches. It also has Agent First Name, Agent Last Name and Agent Email fields, shown when "authorized agent" is chosen. Free My ID should always pick "The subject of the request". Suggest adding this to verification_notes.
- Suggested edit: bump last_verified to 2026-11-07 on acxiom, liveramp, cotality, searchpeoplefree, peoplesearchnow, ca_drop.
- Could not fetch (blocked, 403 or tool policy), so they stay unverified: spokeo, whitepages, beenverified, truepeoplesearch, fastpeoplesearch. The peopleconnect page returns only its title because it is a JS app.
- Not re-fetched this run: equifax, transunion, optoutprescreen, mylife, nuwber, thatsthem, familytreenow, peoplefinders, google_results_about_you, oracle, explorium, peopledatalabs.

## Task 2: success signals
- brokers/success_signals.yaml does not exist on disk. In this repo the signals are Broker fields (`success_text`, `listing_url_pattern`) inside the registry file, so there is nothing to add to a separate file. I did not read models.py or registry.py to confirm the loader.
- The sample already carries success_text for spokeo, beenverified, truepeoplesearch, fastpeoplesearch, searchpeoplefree, peoplesearchnow, acxiom and liveramp, and listing_url_pattern for spokeo.
- I did not read the full private registry, so no new signals were added. Most automatic-browser targets are behind bot protection and cannot be confirmed by fetch. New signals need a live run or fixture.
- Open item for the orchestrator or automation engineer: should success_signals.yaml be created, and with what schema?

## Task 3: state and federal law
- NC, SC and AZ entries in brokers/state_laws.yaml are still correct as of 2026-11-07. No comprehensive law has been enacted in any of the three.
  - NC: S 1022 (filed 2026-04-30) and S 757 are stuck in committee.
  - SC: only the minors-only Age-Appropriate Code Design Act, signed Feb 2026.
  - AZ: one tracker listed no comprehensive law as of May 2026. SB 1815 died. SB 1790 has no evidence of enactment.
- Alabama: one secondary source says the Alabama Personal Data Protection Act was signed 2026-04-17, making it the 21st comprehensive state. Check the AL entry in state_laws.yaml, which I did not re-read this run.
- Federal, new:
  - DOJ Data Security Program (28 CFR Part 202, bulk sensitive data to countries of concern) took effect 2025-04-08, with enforcement stayed to 2025-07-08. It bars data brokerage of bulk US sensitive data to countries of concern. It is not a consumer deletion right.
  - PADFAA (Protecting Americans' Data from Foreign Adversaries Act): the FTC sent warning letters to 13 data brokers on 2026-02-09. See https://ftc.gov/news-events/news/press-releases/2026/02/ftc-reminds-data-brokers-their-obligations-comply-padfaa. Penalties are up to $53,088 per violation. I found no penalty case yet.
  - FTC and Kochava final order, 2026-05-04, under general FTC Act authority.
- Sources are mostly law-firm alerts and trackers, not statute text. Nothing here gives an individual a deletion right, so templates are unchanged.

## Uncertain
- Whether Whitepages uses `suppression_requests` or `suppression-requests`.
- Whether BeenVerified's live path is `/app/optout/search` or `/svc/optout/search/comprehensive_optouts`.
- Whether FastPeopleSearch uses `/removal` or `/optout`.
- Cotality's portal URL.
