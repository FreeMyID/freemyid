# Spanish translation handoff

This guide prepares future translation work; it is not a translation or a claim that Spanish UI is available. The glossary and string inventory are drafts, and the inventory is partial. (See `docs/i18n/STRINGS.md:1-5,66-71` and `docs/i18n/GLOSSARY_ES.md:1-3`.)

## Before translating

- Start with `STRINGS.md` for the fixed English wording, screen context, source location and variable notes. Check the cited source again when a string changes; the inventory itself says line references can move (`docs/i18n/STRINGS.md:3`).
- Use `GLOSSARY_ES.md` for Latin-American Spanish. Address the reader with **usted**, keep terms consistent, and treat glossary entries as suggestions until reviewed (`docs/i18n/GLOSSARY_ES.md:1-3`).
- This inventory does not include mailbox credentials, security warnings, message bodies, addresses, or data-sourced listing instructions. Ask the in-house team to scope and translate protected security or credential wording; do not fill these gaps by inference (`docs/i18n/STRINGS.md:64-71,75`).

## Keep meaning and variables intact

- Preserve each `{placeholder}` exactly as written, including its spelling and braces. It is filled at runtime; never replace it with a real person's details. Make the surrounding sentence natural in Spanish (`docs/i18n/STRINGS.md:38,64`).
- Counts and singular/plural forms need Spanish grammar. Translate the whole message or use the approved catalogue plural rules; do not translate English suffix patterns such as “site(s)” literally (`docs/i18n/STRINGS.md:18,64`).
- A **possible match** remains uncertain and asks the person to review it. Do not write as if Free My ID knows the listing belongs to them (`docs/i18n/STRINGS.md:81`; `docs/i18n/GLOSSARY_ES.md:21,25`).
- Practice mode still searches sites. It holds removal requests; it does not mean that no information is sent anywhere or that requests are simply waiting for approval (`docs/i18n/STRINGS.md:82`; `docs/i18n/GLOSSARY_ES.md:63-64`).
- Keep claims limited to the individual site and retain conditions such as “may,” “if,” “unless,” and the user's settings. A site’s response is not a promise about every site or a guarantee of removal (`docs/i18n/STRINGS.md:27,82`; `docs/i18n/GLOSSARY_ES.md:13,50-51`).

## Review before release

1. Ask a native Latin-American Spanish speaker to review readability, usted forms, regional terms, placeholders, and plural behavior.
2. Ask the product owner to review safety, privacy, consent, and legal meaning. The glossary specifically reserves consent terms for owner review (`docs/i18n/GLOSSARY_ES.md:50-51`).
3. Keep Spanish UI labelled as **not shipped** until the owner approves and the product actually includes it (`docs/i18n/STRINGS.md:5,71`; `docs/i18n/GLOSSARY_ES.md:3`).

Do not treat this guide or a translated document as approval to change app strings, consent wording, legal claims, or protected credential/security guidance.
