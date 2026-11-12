// Global Privacy Control (GPC): STUB. Off by default; the person turns it on in Settings.
//
// GPC tells every website "do not sell or share my information". It has two halves:
//   1. a request header, "Sec-GPC: 1"   -> rules/gpc.json, a static declarativeNetRequest
//                                          ruleset that ships disabled;
//   2. navigator.globalPrivacyControl   -> src/content/gpc.js, registered on demand.
//
// It is a signal, not a removal: it does not take a listing down, and whether a site must
// honour it depends on the law where the person lives (docs/EXTENSION.md has the list).
//
// Chrome and Edge: this file switches both halves on and off. Turning it on needs the
// browser's "all websites" permission, which the browser asks the person for at that moment;
// nothing is asked at install time.
// Firefox: has GPC built in (Settings > Privacy & Security), so the Firefox package carries no
// rule file and no extra permission; Settings points the person at Firefox's own switch.
//
// One rule holds everywhere in this file: the signal is either fully on or fully off. If any
// step of switching it on fails, everything is switched off again and the permission is handed
// back, and the Settings page is told the truth. Switching off always hands the permission
// back, whatever else goes wrong, because without that permission nothing is sent.
//
// TODO before this leaves stub status:
//   - test on real Chrome and Edge (the permission prompt, the header on the wire, the page
//     property, switching it off again, and taking the permission back in the browser);
//   - decide the wording of the permission explanation with Jordan and Marcus.

import { api } from "./browser.js";

/** Id of the static ruleset in the manifest. */
export const GPC_RULESET_ID = "gpc";
/** Id of the dynamically registered page script. */
export const GPC_SCRIPT_ID = "fmid-gpc";

const GPC_SCRIPT_FILE = "src/content/gpc.js";
const GPC_GRANT = Object.freeze({ permissions: ["scripting"], origins: ["*://*/*"] });

/** True when this package can send the signal itself (Chrome and Edge packages only). */
function canSend() {
  const declared = /** @type {any} */ (api.runtime.getManifest()).declarative_net_request;
  return Boolean(declared && api.declarativeNetRequest);
}

/**
 * Run one step. A step that fails must not stop the steps after it.
 * @param {() => unknown} step
 * @returns {Promise<boolean>} true when the step finished without an error
 */
async function attempt(step) {
  try {
    await step();
    return true;
  } catch {
    return false;
  }
}

/**
 * Ask the browser itself. Throws when the browser cannot say.
 * @returns {Promise<boolean>} true when the permission is held and the header rule is enabled
 */
async function readGpcOn() {
  const [granted, enabled] = await Promise.all([
    api.permissions.contains(GPC_GRANT),
    api.declarativeNetRequest.getEnabledRulesets(),
  ]);
  return granted === true && enabled.includes(GPC_RULESET_ID);
}

/**
 * How GPC can be switched on in this browser.
 *   "on_already": the browser itself already sends it (Firefox or Brave with the setting on)
 *   "extension":  this extension can send it (Chrome, Edge)
 *   "browser":    only the browser's own setting can (Firefox)
 * @returns {"on_already"|"extension"|"browser"}
 */
export function gpcSupport() {
  if (/** @type {any} */ (navigator).globalPrivacyControl === true) return "on_already";
  return canSend() ? "extension" : "browser";
}

/** @returns {Promise<boolean>} true when this extension is sending the signal */
export async function isGpcOn() {
  if (!canSend()) return false;
  try {
    return await readGpcOn();
  } catch {
    return false;
  }
}

/**
 * Switch GPC on. MUST be called straight from a click: the browser shows its permission
 * question only in answer to a real action by the person.
 *
 * Never throws. When it returns false nothing is left on: not the permission, not the header
 * rule, not the page script.
 * @returns {Promise<boolean>} true only when every part is on; false when the person said no,
 *   the browser cannot do it, or any step failed
 */
export async function turnGpcOn() {
  if (gpcSupport() !== "extension") return false;
  try {
    const granted = await api.permissions.request(GPC_GRANT);
    if (granted !== true) throw new Error("permission not given");
    await api.declarativeNetRequest.updateEnabledRulesets({ enableRulesetIds: [GPC_RULESET_ID] });
    await attempt(() => api.scripting.unregisterContentScripts({ ids: [GPC_SCRIPT_ID] }));
    await api.scripting.registerContentScripts([
      {
        id: GPC_SCRIPT_ID,
        js: [GPC_SCRIPT_FILE],
        matches: [...GPC_GRANT.origins],
        runAt: "document_start",
        world: "MAIN",
        allFrames: true,
        persistAcrossSessions: true,
      },
    ]);
    if (!(await readGpcOn())) throw new Error("not on after all steps");
    return true;
  } catch {
    await turnGpcOff(); // never leave half of it on
    return false;
  }
}

/**
 * Switch GPC off and hand the extra permission back to the browser. Never throws.
 *
 * The permission is handed back even when another step fails: without it the browser sends
 * no header and runs no page script for this extension.
 * @returns {Promise<boolean>} true only when the browser confirms afterwards that it is off
 */
export async function turnGpcOff() {
  if (!canSend()) return true; // this package never sends the signal
  try {
    await attempt(() =>
      api.declarativeNetRequest.updateEnabledRulesets({ disableRulesetIds: [GPC_RULESET_ID] }),
    );
    // api.scripting is missing once the permission is gone; attempt() covers that too.
    await attempt(() => api.scripting.unregisterContentScripts({ ids: [GPC_SCRIPT_ID] }));
  } finally {
    await attempt(() => api.permissions.remove(GPC_GRANT));
  }
  try {
    return !(await readGpcOn());
  } catch {
    return false; // the browser could not say, so "off" is not claimed
  }
}

/**
 * For the background script: the person can take the "all websites" permission back in the
 * browser's own settings. When it is gone, switch the rest off too.
 */
export async function turnGpcOffIfGrantGone() {
  if (!canSend()) return;
  let granted = false;
  try {
    granted = (await api.permissions.contains(GPC_GRANT)) === true;
  } catch {
    granted = false;
  }
  if (!granted) await turnGpcOff();
}
