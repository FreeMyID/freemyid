# Leverage playbook: making obstruction cost more than compliance

Source: an outside draft (Gemini, owner 2026-11-11) titled "Asymmetric Warfare", edited by Morgan. The draft proposed four vectors. This file keeps what is lawful and good for the people we serve, reframes what can be saved, and rejects what would hurt them or us.

**Goal (edited).** We are not out to "dismantle" brokers or "bankrupt" anyone. The goal is narrower and much harder to attack: **make honoring a person's legal rights the cheapest option a broker has.** Every vector below has to be something a person may lawfully do for themselves, done honestly, for their own benefit. A tactic whose main purpose is to hurt the broker is abuse of process, and an attorney or regulator will see it that way, so it is out.

Every legal point marked *verify* goes to Priya (WO-625) and then to the attorney (decision D6) before any user-facing wording uses it.

## The think-tank pass

| Vector | Architect | Law professor | Data scientist / economist | Verdict |
|---|---|---|---|---|
| 1. Right-to-know before deletion | A new ingestion pipeline; the broker's export becomes evidence | A real right, but the law caps how often it can be used (CCPA: twice per 12 months, *verify*) and lets a business refuse "manifestly unfounded or excessive" requests (*verify*). Used to learn what's held: strong. Used to impose cost: refusable, and it looks like harassment | The real value is ground truth: what they held, proof of deletion, and a before/after diff | **ADOPT, reframed** as an audit for the person (V1) |
| 2. Synthetic data "corrections" | Easy to build | The right to correct is for *inaccurate* data. Knowingly false corrections are false statements to a business under a legal process, and possibly fraud (*verify*). The polluted records feed background and tenant checks, where false data can hurt the person (FCRA settings) | Noise aimed at a broker also lands on the person: wrong data in a background check costs them the job or the apartment | **REJECT** |
| 3. Automated mass arbitration | Templated filings are easy | The people a people-search site lists usually never agreed to its terms, so there is no contract to arbitrate (*verify*). Software that files legal claims for people raises unauthorized-practice-of-law risk. Claims filed without an individual basis are frivolous, and arbitration providers have changed their mass-filing fee rules (*verify*) | Effective when real lawyers run it for real claimants; ruinous if done wrong | **REFRAME**: an attorney handoff, opt-in, per person (V3) |
| 4. Zero-knowledge identity proof | A new protocol: build on existing standards, not a new crypto stack | It strips away the "we can't verify you / you're a bot" excuse. Brokers don't have to accept it yet; regulators could require it | It shrinks the data sent for verification to almost nothing | **ADOPT** as a long-term standard effort (V4) |

## V1. Access-then-delete audit (adopted)

The person's right to know becomes a **proof** tool, not a load generator:
1. Send one right-to-know request through the person's own mailbox (or as their authorized agent, where `authorized_agent_allowed` allows it), within the legal frequency cap.
2. Ingest the export on the person's own computer: PDF, CSV, JSON, HTML or zip. Parsing is local: deterministic parsers first, with an optional on-device model (for example a local Ollama model) for messy PDFs. No cloud calls, ever.
3. Show the person, in plain words, what the broker held: addresses, relatives, phone numbers, inferred traits, and who it was sold to, where disclosed.
4. Then the deletion request, which cites exactly what to delete.
5. Re-scan, and request access again after the next allowed window: **proof of deletion**, or evidence of a false claim (it feeds `ObstructionRecord`, `REQUEST_DENIED` / `DEADLINE_MISSED`, EVIDENCE_ENGINE.md).
6. A "manifestly excessive" refusal or a missed access deadline is itself an obstruction record.

The export holds the most sensitive data in the whole app. It lives only in the encrypted evidence store and is never in logs or events. The person can delete it.

## V2. Synthetic data injection (rejected), and what we do instead

We will not submit false data as "corrections".

The lawful version is better anyway: **correct what is really wrong** (an old address shown as current, a wrong relative, a mixed-up identity) using the person's own true information, and otherwise **delete**. A mixed-up identity (someone else's record merged into yours) is a real harm. Fixing it is a correction worth automating, inside V1's audit.

## V3. Attorney handoff (reframed from mass arbitration)

Software doesn't file legal claims. What it can do lawfully, and what no competitor offers:
- When a confirmed obstruction exists (a deadline missed, a denial, a blocked request), the person may choose to send their **evidence bundle** (EVIDENCE_ENGINE.md section 4) to a privacy attorney of their choice. Opt-in, per person, per case.
- In states with a private right of action, or where an arbitration agreement really does bind the broker and the person (for example the person once bought a report), the attorney decides whether a claim exists. Lawyers who run mass arbitration for real claimants exist; our tamper-evident bundles make their intake cheap.
- Free My ID takes no fee for referrals unless the attorney (D6) clears it; no referral fees otherwise.

## V4. Privacy-preserving identity proof (adopted, long term)

Brokers ask for ID scans and phone calls "to verify". The answer is an open standard that proves **only** what the law lets them ask, without giving them more:
- Build on existing standards rather than new cryptography: ISO/IEC 18013-5 mobile driver's licences (mDL) with selective disclosure, W3C Verifiable Credentials 2.0, and OpenID for Verifiable Presentations (*verify current versions*). Several states already issue mobile IDs; Arizona, one of the family states, does in Apple Wallet (*verify*).
- The proof says "a real person, resident of state X, named the same as the request", and nothing about the device, the browser or any other attribute.
- Pair it with item 4 of the earlier plan: a machine-readable "privacy request" endpoint (think `security.txt` for privacy) that accepts these proofs. The first goal is to get regulators (the CPPA) or privacy organisations to endorse it, not to force brokers.
- When a broker turns down a request backed by a valid proof, "bot defense" is no longer an excuse: that's an `EXCESS_VERIFICATION` obstruction with strong evidence.

## Roadmap placement

| Item | Release | Work order |
|---|---|---|
| V1 access-then-delete audit: request, local export ingestion, plain report, deletion diff | 0.6 (after the evidence engine in 0.5) | WO-627 (research and design), WO-628 (build) |
| V2 correction of genuinely wrong data (mixed-up identities) | 0.7, inside V1 | part of WO-628 |
| V3 attorney handoff (opt-in bundle export to an attorney the person chooses) | 0.8, after the D6 attorney review | WO-629 (research and design) |
| V4 privacy-preserving identity proof plus the privacy-request endpoint standard | 1.x, research starts now | WO-630 (research) |

## Owner decisions

- **L1.** V1 access requests are on by default, or opt-in per broker (recommended: opt-in at first; the exports are very sensitive)?
- **L2.** Is an on-device model allowed for parsing exports (recommended: yes, local only, deterministic parsers first)?
- **L3.** Attorney handoff partners and any fee arrangement go to the attorney (D6) before anything is built.
- **L4.** Spend effort on a public standards push (V4) before 1.0 (recommended: research only before 1.0)?

## Appendix: the edited think-tank prompt for future agents

```
<role>
Principal Systems Architect for Free My ID, consulting a Privacy Law Professor, a Game
Theorist and a Data Scientist before proposing components.
</role>
<goal>
Make honoring a person's legal privacy rights the cheapest option a broker has, using only
what the person may lawfully do for themselves, honestly and for their own benefit.
</goal>
<boundaries>
1. No evasion: no CAPTCHA solving, stealth, UA/fingerprint spoofing, proxies (shared rule 5).
2. No false data: never submit untrue information under any legal right.
3. No load for its own sake: a request must serve the person; harm to the broker is never the
   goal, and staying inside statutory frequency caps is required.
4. No unauthorized practice of law: the app prepares evidence and drafts; people and their
   attorneys decide and file.
5. Local-first: personal data and broker exports stay encrypted on the person's computer.
6. For each component, state the three perspectives in two lines each, then the design.
</boundaries>
```
