# Suppression lists and credit-freeze extras (BL-IN-71), researched 2026-11-08

Author: Priya Shah. For Morgan to wire. The checklist file `brokers/checklists.yaml` already holds the entries for
Innovis, ChexSystems, NCTUE, LexisNexis, OptOutPrescreen, DMAchoice and the National Do Not Call Registry
(all re-read 2026-11-07/08, see that file). They are NOT repeated here. This note adds what was missing:
the protected-consumer (minor) freeze, plus two corrections for the existing entries.

No Social Security number guidance goes beyond what each official page states. Free My ID never collects or stores these.

## 1. New checklist entries (same schema as brokers/checklists.yaml)

The checklist format is data (`brokers/checklists.yaml`, `ChecklistFile` in models.py), so these are ready to paste.
I could not edit that file or commit: this session has no shell or edit tool (only Read/Write), and a full-file
rewrite of a shared file is unsafe. Paste under "credit freezes".

```yaml
  - id: freeze_child_equifax
    title: "Freeze your child's credit at Equifax (child under 16)"
    why: "A child's clean credit file is a target for thieves. A freeze stops anyone opening new credit in the child's name."
    url: https://www.equifax.com/personal/education/identity-theft/articles/-/learn/freezing-your-childs-credit-report-faq/
    cost: "Free. Equifax says freezes are free."
    time_needed: "About 20 minutes to gather papers, plus mailing. Equifax says up to 3 business days after it gets everything."
    need_on_hand: ["The Equifax Minor Freeze form (from the web address above)", "Copy of ONE ID for you: driver's license or other government ID, Social Security card, or birth certificate", "Proof you are the parent or guardian (one): the child's birth certificate, a court order, a valid power of attorney or a foster care certification", "Copies of BOTH the child's Social Security card and the child's birth certificate", "An envelope and a stamp"]
    steps:
      - "Open the Equifax web address above and download the Minor Freeze form. Fill it in."
      - "Make copies of the papers listed. Send copies, never the originals."
      - "Mail the form and copies to: Equifax Information Services LLC, P.O. Box 105788, Atlanta, GA 30348."
      - "Equifax makes a credit file for the child and freezes it. You get a confirmation letter, or a request for more information."
    how_to_undo: "A parent or guardian sends a written request by mail with the same kind of proof."
    tips:
      - "A freeze must be placed at each bureau separately. Do the child at Experian and TransUnion too."
      - "Teens aged 16 and 17 can ask for their own freeze by phone or mail."
      - "Equifax's page says minors cannot make a myEquifax online account. This is a mail request."
    source_urls: [https://www.equifax.com/personal/education/identity-theft/articles/-/learn/freezing-your-childs-credit-report-faq/, https://www.equifax.com/personal/credit-report-services/credit-freeze/, https://consumer.ftc.gov/articles/credit-freezes-and-fraud-alerts]
    date_checked: 2026-11-08
    verification: official_page
    notes: "Both Equifax pages opened and read 2026-11-08. The page lists mail only for a minor and no phone number for it."

  - id: freeze_child_experian
    title: "Freeze your child's credit at Experian (child under 16)"
    why: "Same reason as Equifax. Each bureau is separate."
    url: https://www.experian.com/help/minor-request.html
    cost: "Not stated on the Experian page we read. The FTC calls a child freeze free."
    time_needed: "About 20 minutes to gather papers, plus mailing."
    need_on_hand: ["The request form with the child's details", "Your government photo ID (copy)", "Proof of your address: a bank statement, utility bill or insurance statement (copy)", "The child's birth certificate (copy)", "Proof of guardianship if you are not named on the birth certificate", "The child's Social Security card (copy)"]
    steps:
      - "Open the Experian web address above and choose to add a security freeze for a minor."
      - "Gather the papers listed. Send copies."
      - "Mail them to Experian, PO Box 9554, Allen, TX 75013."
      - "Or upload them at experian.com/upload: choose 'Other' as the reason and say you want a freeze for a minor."
    how_to_undo: "Experian's page does not describe removing a child freeze. Use the contact form at experian.com/help/contact/."
    tips:
      - "Overnight mail goes to 701 Experian Parkway, Allen, TX 75013 (not the PO box). Experian's page mentions a possible fee for overnight handling. Standard mail is fine."
    source_urls: [https://www.experian.com/help/minor-request.html, https://consumer.ftc.gov/articles/credit-freezes-and-fraud-alerts]
    date_checked: 2026-11-08
    verification: partial
    notes: "Experian page read 2026-11-08. It lists documents, mail and upload but gives no steps, fee or phone for a freeze itself (its heading is 'minor request'). Public cost is therefore hedged. Re-read before showing as certain."

  - id: freeze_child_transunion
    title: "Freeze your child's credit at TransUnion (child under 16)"
    why: "Same reason as the other bureaus."
    url: https://www.transunion.com/credit-freeze/credit-freeze-faq
    cost: "The FTC says a child freeze is free. A 2017 California AG leaflet listed $10, so check TransUnion's page before sending any payment."
    time_needed: "About 20 minutes plus mailing."
    need_on_hand: ["Proof you are the parent or guardian, such as a copy of the child's birth certificate", "Copies of identifying documents for you and the child, such as each Social Security card"]
    steps:
      - "Read TransUnion's instructions for minors on the web address above (look for the 'freeze for a minor' section)."
      - "TransUnion takes this by mail only, because of the papers needed. Send copies, never originals, to TransUnion, P.O. Box 380, Woodlyn, PA 19094."
      - "Certified mail is a sensible choice because the papers are sensitive."
    how_to_undo: "Mail a request to the same address. A protected person aged 16 or older can mail their own request."
    tips:
      - "Never pay anyone else to do this for you."
    source_urls: [https://consumer.ftc.gov/articles/credit-freezes-and-fraud-alerts, https://transunion.com/credit-freeze/mail-or-phone, https://oag.ca.gov/idtheft/facts/freeze-child-credit]
    date_checked: 2026-11-08
    verification: partial
    notes: "transunion.com pages return HTTP 403 to our fetcher (2026-11-08), so TransUnion's own wording was NOT read. The FTC page (read) links transunion.com/credit-freeze/credit-freeze-faq#freeze-other-minor. The P.O. Box 380 Woodlyn address, mail-only and document list come from a search-result summary of transunion.com/credit-freeze/mail-or-phone, and the $10 from the 2017 CA AG PDF (a search result, not opened). Keep partial until a person reads TransUnion's page in a browser."
```

## 2. Corrections for existing entries

- `dmachoice` fee conflict. The checklist says $8 online / $9 mail, re-confirmed on dmachoice.org's own register page
  on 2026-11-08. The FTC page read today (consumer.ftc.gov/articles/prescreened-credit-insurance-offers) mentions a
  "$6 processing fee" for DMAchoice. The official page wins; the FTC figure is older. Leave as is. Fetched 2026-11-08:
  https://www.dmachoice.org/ loads (login/register, deceased and caretaker opt-out tools, an email opt-out service).
- `optoutprescreen` is still `partial`: optoutprescreen.com returns 403. The FTC page re-read 2026-11-08 confirms
  website, 1-888-5-OPT-OUT (1-888-567-8688), five-year by web or phone, permanent by signing and returning the
  Permanent Opt-Out Election form, name, address, SSN and date of birth requested, "confidential and may be used only
  to process your request", and no fee stated. This supports the existing need_on_hand wording, which is now
  FTC-sourced rather than unread.
- Equifax adult freeze phone (888) 298-0045 re-confirmed on the Equifax freeze page 2026-11-08.

## 3. Not changed
Innovis, ChexSystems (still partial, phone conflict), NCTUE, LexisNexis, National Do Not Call: no new reading this
pass beyond what the file already records. Protected-consumer freezes at Innovis, ChexSystems, NCTUE and LexisNexis
were not researched (those pages were not read); do not claim them.

## Sources and access dates (all 2026-11-08)
- https://consumer.ftc.gov/articles/credit-freezes-and-fraud-alerts (read: child under 16, free, bureau links)
- https://www.experian.com/help/minor-request.html (read)
- https://www.equifax.com/personal/education/identity-theft/articles/-/learn/freezing-your-childs-credit-report-faq/ (read)
- https://www.equifax.com/personal/credit-report-services/credit-freeze/ (read)
- https://consumer.ftc.gov/articles/prescreened-credit-insurance-offers (read)
- https://www.dmachoice.org/ (read)
- https://www.transunion.com/credit-freeze/credit-freeze-faq and /credit-freeze/mail-or-phone (HTTP 403; search summaries only)
- https://oag.ca.gov/idtheft/facts/freeze-child-credit (search result only)
