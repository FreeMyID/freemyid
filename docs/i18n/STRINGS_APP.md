# App string inventory: broker pages, protection steps and reports

This inventory adds fixed English copy to [STRINGS.md](STRINGS.md) and
[STRINGS_CLI.md](STRINGS_CLI.md). It records current source wording, not a translation.
No Spanish interface ships yet; Spanish UI is coming in the roadmap
(`docs/ROADMAP.md:70,208`). The CLI inventory is delivered in WO-232 (issue pending)
and may be absent until the in-house team integrates that work.

Braces such as `{person}`, `{date}` and `{count}` name runtime placeholders, never
example personal values. Keep whole sentences together when translating count-dependent
grammar. Notes marked **owner review before translation** apply to legal, consent,
privacy and security meaning; recording the English does not approve a translation.

## Broker details and activity

| Source | Visible string(s) | Context | Plural / variable notes |
|---|---|---|---|
| `src/freemyid/wizard/views.py:27-36` | “Not checked yet”; “Not listed there”; “Listed. A request has not gone out yet”; “We asked them to delete it”; “We asked. They need to confirm”; “They confirmed”; “No longer listed”; “It came back. We are asking again”; “Needs a step from you”; “We hit a problem. We will try again” | Plain status explanations used on broker and summary pages | These differ from the short shared status chips. Preserve requested versus confirmed and the individual-site scope; **owner review before translation**. |
| `src/freemyid/wizard/views.py:40-42` | “Sent a request”; “Checked the site”; “Found a listing”; “Listing gone”; “Listing came back”; “Ticked a safety step”; “Un-ticked a safety step” | Fixed activity words on a broker timeline | Both submitted-action keys share the first label; action keys are not translated. Sending is distinct from finding; **owner review before translation**. |
| `src/freemyid/wizard/views.py:89-90` | “Deletion request”; “Second request”; “Follow-up”; “Formal demand” | Request-kind labels | Preserve the difference between a request and a formal demand; **owner review before translation**. |
| `src/freemyid/wizard/views.py:96` | “Not found” | Refused broker-detail lookup | Fixed error detail, not a finding that a person's listing was absent. |
| `src/freemyid/wizard/views.py:98,104` | “All sites for {person}”; “This site needs a step from you.”; “Go to Today” | Broker-page return link and pending-step notice | `{person}` is the on-screen label. The notice requests a human action. |
| `src/freemyid/wizard/views.py:106-108` | “What this site shows about you”; “Nothing found yet.” | Listing details and empty state | Absence of saved details is not confirmation of removal. |
| `src/freemyid/wizard/views.py:112-121` | “Name: {name}”; “Age: {age}”; “Places: {places}”; “Relatives listed: {count}”; “First seen {date}.”; “ Gone since {date}.” | Labels around saved listing values | Values are dynamic and not copied into this inventory. The optional gone-since sentence begins with a space. Dates use the page's formatter. |
| `src/freemyid/wizard/views.py:122-123` | “This is only what the site itself shows. Free My ID sends a site nothing more than that.” | Listing-disclosure note | This is the current source claim, not newly approved wording; **owner review before translation**. |
| `src/freemyid/wizard/views.py:125-129` | “What we sent”; “No request has gone to this site yet.”; “When”; “What”; “How” | Request history heading, empty state and new column labels | The remaining shared column label is already inventoried in STRINGS.md. Preserve the individual-site/no-request scope; **owner review before translation**. |
| `src/freemyid/wizard/views.py:133-134` | “ (practice)”; “Reference {reference}” | Optional request-history suffix and reference | Request method/status values are dynamic interface data. The practice suffix starts with a space; **owner review before translation**. |
| `src/freemyid/wizard/views.py:141,145,147` | “What came back”; “Reply received {date}”; “No reply yet. Many sites never reply. Free My ID checks the listing itself.” | Reply history and empty state | A reply is distinct from a confirmed removal. |
| `src/freemyid/wizard/views.py:150,152-154` | “not planned yet”; “Last checked {date}. Last request {date}. Sites can put details back up, so Free My ID looks again.” | Next-check fallback and history note | The two `{date}` values come from different timestamps; preserve that distinction. The shared section heading is already inventoried. |
| `src/freemyid/wizard/views.py:160-161` | “What the site showed and replied, kept encrypted on this computer.” | Receipt gallery note | Fixed privacy statement; **owner review before translation**. Captions and dates are dynamic. |
| `src/freemyid/wizard/views.py:175,296-297` | “What happened”; “Date” | Timeline heading and summary-table column label | The activity heading is also a summary column label; inventory it once. Shared site labels are in STRINGS.md. |

## Protection steps

| Source | Visible string(s) | Context | Plural / variable notes |
|---|---|---|---|
| `src/freemyid/wizard/views.py:185-188` | “We could not read this company's own page when we prepared these steps, so some details come from trusted consumer-help sites. This is still a good thing to do. Before you type anything in or call a number, check the address and the phone number on the company's own page.” | Partially verified checklist notice | Preserve the verification limit and instruction to check the company page; **owner review before translation**. |
| `src/freemyid/wizard/views.py:195,204` | “done”; “to do” | Screen-reader checklist state next to the title | Fixed state words, distinct from action buttons and data keys. |
| `src/freemyid/wizard/views.py:206,208-212` | “Cost: {cost}”; “Time: {time}”; “Have these ready”; “Steps”; “Good to know”; “To undo it:”; “Checked on {date}.” | Checklist metadata and instruction headings | Checklist values and bodies come from data and are not reproduced. `{date}` is the checklist verification date. |
| `src/freemyid/wizard/views.py:215,218,247` | “Open the web page”; “I have not done this”; “I did this” | Checklist/open and completion controls | Completion controls are shared by ordinary and search-engine steps. Opening is distinct from recording completion; the CLI inventory contains the guided-step explanations. |
| `src/freemyid/wizard/views.py:228,233-235,242-244` | “Google and Bing”; “ Done on {date}.”; “ Opened on {date}.”; “Open the page for me”; “Or open the link yourself” | Guided search-engine group, dates and controls | The date suffixes start with a space. Opening a page is not completion. The imported introduction/status messages belong to STRINGS_CLI.md. |
| `src/freemyid/wizard/views.py:254-257` | “Removing your details from people-search sites is one part. These steps help stop someone using them. Each one is optional, most are free, and you can tick them off as you go. The ticks stay on this computer.” | Protection-page introduction | Preserve optional steps, qualified cost and local ticks; **owner review before translation**. Shared page title is already inventoried. |
| `src/freemyid/wizard/views.py:259-260` | “The list is not available right now.” | Missing checklist/person fallback | An unavailable list does not mean all steps were completed. |
| `src/freemyid/wizard/views.py:268-270` | “{done} of {total} done for {person}”; “Safety steps done”; “{done} of {total}” | Visible progress sentence, accessible progress name and fallback text | Keep separate completed and total counts; `{person}` is an on-screen label. |
| `src/freemyid/wizard/views.py:273-274` | “Free My ID never pays for you and never asks for your Social Security number. These steps happen on the real company websites, in your own browser.” | Protection-page safety note | Preserve the refusal and location of the steps; **owner review before translation**. |

## On-screen summary and exported report

| Source | Visible string(s) | Context | Plural / variable notes |
|---|---|---|---|
| `src/freemyid/wizard/views.py:298,303-304` | “No site has needed a request so far.”; “What Free My ID did for {person}”; “Written on {date}.” | Summary empty state, heading and written date | Person/date are placeholders. Shared print/back controls and browser-title template are already inventoried in STRINGS.md. |
| `src/freemyid/wizard/views.py:305-311` | “Free My ID has sent {sent} request(s) asking people-search sites to delete {person}'s details. {good} site(s) has/have confirmed or no longer list them. {waiting} is/are still waiting to reply. {needs_action} needs/need a step from a person. {not_listed} site(s) was/were checked and did not list them.” | Main summary paragraph | Parentheses/slashes describe the source's singular/plural branches; they are not displayed literally. Each count selects its own grammar. Preserve requested, confirmed and checked-but-not-listed distinctions; **owner review before translation**. |
| `src/freemyid/wizard/views.py:312-316` | “The list”; “Please remember”; “Free My ID keeps checking and asks again if details come back. This page holds only a name and site names. It has no address, phone number or date of birth, so it is safe to hand to a family member.” | Summary sections and sharing note | The inserted shared honesty note is already inventoried. Preserve the page-specific data limit; **owner review before translation**. |
| `src/freemyid/wizard/report.py:43` | “covers: {sites}” | Exported report's covered-site detail | `{sites}` is a sorted, comma-separated list of site names. |
| `src/freemyid/wizard/report.py:63-64` | “Free My ID report”; “{person}: what Free My ID has asked, and what came back” | Exported report title and heading | `{person}` is the on-screen label; retain asked versus confirmed meaning. |
| `src/freemyid/wizard/report.py:65-68` | “As of {date}, Free My ID has asked {asked} people-search sites to delete this person's details. {good} have confirmed or no longer list them. {waiting} are still waiting. {needs_action} need a person to do one step. Sites can put details back up, so Free My ID checks again.” | Exported report summary | Source uses the shown wording for all counts, without singular/plural branches. Preserve separate dates/counts and individual-site outcomes; **owner review before translation**. |
| `src/freemyid/wizard/report.py:69-70` | “Status”; “Last checked”; “Last request” | Exported report column labels | The shared site column, status chips and honesty paragraph are already inventoried in STRINGS.md; do not add duplicate entries. |

## Tray and first run

| Source | Visible string(s) | Context | Plural / variable notes |
|---|---|---|---|
| `src/freemyid/wizard/tray.py:40,42-43` | “Open Free My ID”; “Checking now...”; “Check now”; “Quit Free My ID” | Tray/menu-bar actions | The checking variant is disabled while running. The separate dashboard-derived status sentence is already inventoried in STRINGS.md. |
| `src/freemyid/wizard/firstrun.py:37-38` | “Free My ID needs a web browser to fill in forms and none was found. Download a small extra browser just for Free My ID (about 150 MB)? [y/N] ” | Browser-download confirmation question | Preserve the approximate size, question, default-no hint and trailing space; **owner review before translation**. |

## Coverage boundaries and shared entries

- The exposure card is already inventoried in STRINGS.md; do not repeat its rows
  (`src/freemyid/wizard/views.py:47-84`). Shared receipt, navigation, status-chip and
  site headings also stay there; their uses here add no new wording
  (`src/freemyid/wizard/views.py:129,151,156-158,259,296,301-302,317`;
  `src/freemyid/wizard/report.py:12,58,69-71`).
- The protection helper module adds no fixed visible English; its functions delegate
  loading and tick operations. The rendered protection copy is inventoried above
  (`src/freemyid/wizard/protect.py:16-33`; `src/freemyid/wizard/views.py:184-275`).
- The desktop window uses the shared product-name title from STRINGS.md
  (`src/freemyid/wizard/desktop.py:32,140`). This module contains no fixed splash or
  error-dialog copy to add: its native-window failure message is logged, and its splash
  hooks are callbacks rather than text (`src/freemyid/wizard/desktop.py:145,164-168,201-205`).
  Packaging/launcher text is outside this inventory's six-module scope.
- The tray's product-name tooltip is the existing shared brand; its status sentence is
  delegated to the dashboard (`src/freemyid/wizard/tray.py:29-35,118,125`).
- Checklist bodies, names, listing values, receipt captions and unknown fallback action
  tokens remain runtime data. Do not turn these into fixed catalog entries
  (`src/freemyid/wizard/views.py:97-102,109-121,163-179,196-201,238-240`).
- Report status chips and the honesty paragraph are imports, not new strings in the
  report module (`src/freemyid/wizard/report.py:12,58,71`). Developer exception messages
  and log output are excluded from visible-copy rows (`src/freemyid/wizard/report.py:29-31`;
  `src/freemyid/wizard/desktop.py:145`).
