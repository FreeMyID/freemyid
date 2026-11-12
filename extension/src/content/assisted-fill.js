// TODO (FUTURE, NOT BUILT, NOT SHIPPED): form help for the Assisted tier.
//
// This file is a placeholder. tools/build_extension.py leaves it out of every package
// (EXCLUDED_FILES) and no manifest names it. Nothing here runs today.
//
// If and when it is built, these rules are fixed (shared rules 5 and 6, docs/EXTENSION.md):
//
//   1. It runs only after the person clicks a button in the banner or the popup, for the tab
//      they are looking at. Never on page load, never on a schedule, never in the background.
//   2. It fills only the fields the person allowed for THIS broker, and only the fields the
//      broker's listing already shows (Listing.shown_fields) plus the removal mailbox. The
//      values come from the desktop app for that one click; the extension never stores them.
//      That needs a new, reviewed protocol message, because today's messages carry no
//      personal details at all.
//   3. It never touches a CAPTCHA or any "are you human" check: it does not tick the box, does
//      not solve anything, does not hide or move it, and does not press Submit. The person
//      does those steps.
//   4. It never pretends to be something else: no changed user agent, no fake events dressed
//      up as typing, no stealth of any kind.
//   5. It never pays, never creates an account, never uploads an ID and never gives a phone
//      number unless the matching permission is on in the person's profile.
//   6. If the page does not look like the expected form, it stops and tells the person; the
//      Assisted card in the desktop app is the fallback.
//
// It will also need the "scripting" permission (with activeTab), which is NOT in the manifest
// today. Adding it needs a written rationale in docs/EXTENSION.md and a security review.

/**
 * @typedef {Object} AllowedField
 * @property {string} name   field key from the broker registry, e.g. "full_name"
 * @property {string} value  the value the person allowed for this broker, for this click
 */

/**
 * Not implemented.
 * @param {AllowedField[]} _allowedFields
 * @returns {never}
 */
function fillAllowedFields(_allowedFields) {
  throw new Error("assisted-fill is not built yet");
}

void fillAllowedFields;
