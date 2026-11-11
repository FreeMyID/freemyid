# How listing matches are decided

This guide describes the source snapshot reviewed for WO-289. A parsed `Candidate`
is scored without I/O, and the result carries a level, numeric score and signal
names. The matcher does not itself send a request. See [Architecture](ARCHITECTURE.md)
for the wider application (`src/freemyid/engine/matcher.py:1-9,69-87,207-257`).

## Inputs and name handling

A candidate can contain a name, single age, locations, relatives, phones and emails;
its address/DOB flags record what the page displays rather than adding independent
matching signals (`src/freemyid/engine/matcher.py:69-80,313-328`).

Names are normalized with Unicode decomposition, accent removal, lowercase ASCII
letters/digits and collapsed whitespace. Candidate names are compared with current
and previous profile names, the person's own nicknames and common nickname groups.
Every collected first name is tried with every current/previous last name; this is
not a label identifying which historical name matched
(`src/freemyid/engine/matcher.py:90-96,127-143`).

Name similarity uses the best RapidFuzz token-sort ratio, also trying the shown name
without single-letter initials. A recognized suffix that belongs to the person is
removed before scoring; other shown suffixes are retained. An exact-name check
uses the same comparison with common nickname-group expansion disabled
(`src/freemyid/engine/matcher.py:146-173`).

The nickname index unions only groups containing the supplied first name, then
caches that index; expansion does not recursively expand every discovered alias.
The separate group index helps distinguish ambiguous shared nicknames
(`src/freemyid/engine/nicknames.py:97-127`).

## Fields, thresholds and numeric contributions

The name threshold is 88; below it the result immediately becomes `no_match` with
half the name similarity and no reasons. Once the name passes, each distinct
supporting reason contributes 12.5 to a score whose name component is half the name
similarity. The final score is rounded to one decimal and capped at 100. A high
numeric score does not override the safety caps on the level
(`src/freemyid/engine/matcher.py:33-42,210-212,242-257`).

| Field | Evidence required in this snapshot | Contribution after the name gate |
| --- | --- | --- |
| Name | Best normalized similarity at least 88 | Similarity × 0.5; `matcher.py` does not add a `name` reason (`src/freemyid/engine/matcher.py:210-213,256-257`) |
| Location | Candidate city matches an address city; its state must match when present. Any profile address is considered. | One `city` reason, 12.5 points (`src/freemyid/engine/matcher.py:215-221,256`) |
| Age | Estimated profile age and shown single age differ by at most two years | One `age` reason, 12.5 points (`src/freemyid/engine/matcher.py:223-225,256`) |
| Relative | At least one normalized pair has token-sort similarity at least 85 | One `relative` reason, 12.5 points (`src/freemyid/engine/matcher.py:34,227-231,256`) |
| Phone | A digit-normalized value matches; normalization keeps the last ten digits when there are at least ten | One `phone` reason, 12.5 points (`src/freemyid/engine/matcher.py:99-101,233-235,256`) |
| Email | A stripped, lowercase value matches | One `email` reason, 12.5 points (`src/freemyid/engine/matcher.py:237-240,256`) |

Estimated age comes from DOB when present, otherwise the profile's supplied age.
The parser here extracts one integer: `Age 45-49` reads as 45, while `In their 40s`
is not recognized as a span. Age-range support is coming in a separate work order;
this snapshot has no `age_max` candidate field. Do not infer decade support from
the parser's name (`src/freemyid/models.py:386-390`,
`src/freemyid/engine/matcher.py:69-80,104-112`).

## Levels and household safety caps

After the name gate, zero supporting signals gives `no_match`, one gives
`possible`, and two or more provisionally gives `confirmed`. Each field adds at
most one reason even if several values match. Reasons contain signal labels,
not the actual matching values (`src/freemyid/engine/matcher.py:8-9,215-244`).

A provisional confirmation is reduced to `possible` in any of these cases:

- The shown age differs from estimated age by more than five years.
- The name is only fuzzy or common-group based and no age, phone or email signal
  supports it.
- The shown first name may belong to another person under the nickname-group
  rules, and neither phone nor email supports it.

These are level caps; the numeric score is calculated afterward. The last rule
prevents a close age alone from confirming an ambiguous household name
(`src/freemyid/engine/matcher.py:35-42,176-204,245-257`).

## Worked examples: fake people only

Use the synthetic Jane Q Testperson in Springfield, IL, age 46 on 2026-11-08.
For the final row, the profile and candidate also name synthetic relative Kim
Testperson. Every candidate shows `Jane Q Testperson`, so name similarity is 100.
The following outputs were evaluated with `score(..., today=date(2026, 11, 8))`;
they follow the field checks, count rule and age-conflict cap
(`src/freemyid/engine/matcher.py:207-257`).

| Other shown evidence | Reasons | Level | Score |
| --- | --- | --- | --- |
| Nothing | `[]` | `no_match` | 50.0 |
| Springfield, IL | `['city']` | `possible` | 62.5 |
| Springfield, IL; age 46 | `['city', 'age']` | `confirmed` | 75.0 |
| Springfield, IL; matching relative; age 60 | `['city', 'relative']` | `possible` | 75.0 |

The last two rows have the same numeric score but different levels: the 14-year
age conflict caps the latter. Name alone never supplies the two supporting
signals required for a confirmation (`src/freemyid/engine/matcher.py:242-257`).

## Stored listings and reverse lookups

`rescore` preserves the person's explicit confirmations/rejections and reverse
lookup hits. Otherwise it reconstructs a candidate from stored fields, carries
only previously established phone/email labels, and can lower a stored level
but never raise it (`src/freemyid/engine/matcher.py:43-50,260-275`).

Phone/email-only lookup scoring follows another path: conflicting shown contact
values give `no_match`; otherwise the lookup is `possible` at 50 with a lookup
reason. It never produces an automatic confirmation. Ordinary `score_all` drops
`no_match` results, keeps the highest score per exact URL and sorts by descending
score (`src/freemyid/engine/matcher.py:278-310,343-354`).

## What to change and what to test

- [ ] For name rules, inspect normalization, variants, suffix handling and the
  household caps together. Keep exact, common-group and ambiguous-name cases
  separate (`src/freemyid/engine/matcher.py:90-96,127-204,245-255`).
- [ ] For a new supporting field, inspect reason de-duplication, the count-based
  level and score formula; do not treat a numeric increase as permission to
  remove a safety cap (`src/freemyid/engine/matcher.py:215-257`).
- [ ] Run current/previous-name, nickname, suffix and household regression cases;
  include both a positive control and a nearby mismatch
  (`tests/test_matcher_variants.py:29-70,88-179`).
- [ ] For saved-listing changes, test user decisions, carried contact signals and
  downgrade-only behavior (`src/freemyid/engine/matcher.py:260-275`).
- [ ] For age spans, update parsing, candidate population and scoring together;
  preserve existing single-age behavior rather than documenting planned fields
  as already present (`src/freemyid/engine/matcher.py:69-80,104-112,223-225`).

## What this guide does not cover

This describes matching decisions, not delivery authorization, registry maintenance
or personal-data storage. Displayed-field metadata and candidate-to-listing
conversion are separate from the matching reasons; do not use the scoring table
as a list of fields to send (`src/freemyid/engine/matcher.py:313-340`).
