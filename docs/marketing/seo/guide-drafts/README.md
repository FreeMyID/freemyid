# Guide drafts: 10 uncovered people-search brokers (BL-IN-81)

Owner: seo-growth (Sam Okafor). Written 2026-11-08. Drafts only, for the web team; nothing here is live. Page building happens later.

## 1. Already covered (do not duplicate)
Public guides come from the public sample registry (`brokers/registry.sample.yaml`, loaded by `web/src/lib/site.ts`): Spokeo, FreePeopleDirectory, Whitepages, Whitepages 411, BeenVerified, PeopleLooker, PeopleConnect Suppression Center (Intelius, Instant Checkmate, TruthFinder, US Search, ZabaSearch), Intelius, TruthFinder, PeopleFinders, TruePeopleSearch, FastPeopleSearch, Radaris, MyLife, Nuwber, ThatsThem, FamilyTreeNow, SearchPeopleFree, PeopleSearchNow; data-broker and official-tool guides (Acxiom, Oracle, LiveRamp, Cotality, Experian, Equifax, TransUnion, OptOutPrescreen, Google results about you, California DROP, Explorium, People Data Labs). Hand-built hub pages: `web/src/pages/guides/` (phone-number, parent guides). Query map: `keywords.md` rows 3-9, 21-23.

Not re-drafted because the PeopleConnect guide already names them: Instant Checkmate, US Search, ZabaSearch. Web team: consider short alias pages or redirects, since people search these names.

## 2. Ranking method (rough)
No keyword-volume tool is available to us (see `semrush-lookups.md`). Proxy: Similarweb's public per-domain page, "Global Rank" as seen 2026-11-08 (lower number = more traffic; Similarweb estimates, September 2026 snapshot; Similarweb's page labels are inconsistent so we use rank, not visit counts). Traffic is not the same as opt-out searches, so this is a ROUGH guess. Second signal: competitors (DeleteMe, Incogni, Optery) each publish a guide for the site, which shows they think people search for it (seen in a web search 2026-11-08). Replace with Search Console data once available.

## 3. Ranking table

| # | Broker | Slug | Similarweb global rank (US rank) | Competitor guides seen | Opt-out source quality | Asks for |
|---|---|---|---|---|---|---|
| 1 | USPhoneBook | `usphonebook` | 6,118 (1,474) | DeleteMe, Incogni, OneRep, Aura, others | UNVERIFIED (broker page blocked to us) | Email, own phone number (to find listing) |
| 2 | Social Catfish | `social-catfish` | 20,548 (6,530) | not checked | Broker page read | Name, email; optional phone/photos; possible ID check later |
| 3 | CyberBackgroundChecks | `cyberbackgroundchecks` | 25,607 (5,625) | DeleteMe, Optery, Incogni | UNVERIFIED (403) | Name, email; optional phone, DOB, address |
| 4 | AnyWho | `anywho` | 33,975 (7,197) | DeleteMe, Incogni, others | UNVERIFIED; route disputed (Intelius vs Spokeo) | Possibly DOB and a phone/email code |
| 5 | CheckPeople | `checkpeople` | 34,604 (7,041) | not checked | Broker page read (first step only) | Email |
| 6 | SmartBackgroundChecks | `smartbackgroundchecks` | 73,798 (15,088) | none found in our search | Broker page read | Name, email |
| 7 | InfoTracer | `infotracer` | 92,576 (20,325) | not checked | Broker page read | Request form; possible extra identity questions |
| 8 | USA People Search | `usa-people-search` | 110,946 (23,521) | Optery | Broker page read | Name, email |
| 9 | PeopleSmart | `peoplesmart` | 127,474 (27,814) | DeleteMe, Optery, Incogni | UNVERIFIED; site status disputed | Name, state, email |
| 10 | Addresses.com | `addresses-com` | 212,013 (45,459) | DeleteMe | UNVERIFIED (403) | Unknown |

Why these ten and not others (all ranks same method, same date): ClustrMaps 407,021; PeekYou 392,172; Advanced Background Checks 237,649 (just below #10; next in line); PeopleWhiz 1.8M; Neighbor Report 5.6M. PublicRecordsNow showed no data. Instant Checkmate (23,710), US Search and ZabaSearch (220,795) would rank high but are covered by the PeopleConnect guide.

Sources for ranks: https://www.similarweb.com/website/<domain>/ , each fetched 2026-11-08. For Whitepages, BeenVerified, TruePeopleSearch, FastPeopleSearch being top Public Records sites in the US, Sept 2026: https://www.similarweb.com/top-websites/united-states/reference-materials/public-records-and-directories/ (fetched 2026-11-08). Competitor guide evidence: web search 2026-11-08 plus the DeleteMe guide pages cited in each draft.

## 4. Status and what the web team needs
- Ready after a light check (broker's own page read 2026-11-08): `smartbackgroundchecks`, `usa-people-search`, `social-catfish`.
- Partial (broker page read, but gaps): `checkpeople` (only step 1), `infotracer` (no single flow).
- NOT ready, broker page blocked to us; broker-researcher must open each in a real browser first: `usphonebook`, `cyberbackgroundchecks`, `anywho`, `peoplesmart`, `addresses-com`.
- Never publish a draft's time-to-removal unless marked as the broker's own words.
- All drafts follow the never-asks list in `/safety/` (no SSN, bank or card, payment; never a full birthday from Free My ID). Where the broker's own form asks for a date of birth or phone, the draft flags it.
- Copy rules: POSITIONING rules 1-3 (no "guaranteed"/"erased", calm tone); every draft avoids mocking and avoids telling readers to pay.
- Suggest `<updated>` / "last checked" date on each page, matching `PLAN.md`.

## 5. Open requests
- broker-researcher: verify the ten (esp. #1, 3, 4, 9, 10) and add them to the public sample registry if wanted, since the site builds guides from it.
