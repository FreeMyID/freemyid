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
// TODO before this leaves stub status:
//   - test on real Chrome and Edge (the permission prompt, the header on the wire, the page
//     property, and switching it off again);
//   - react to permissions.onRemoved (the person can take the permission back in the browser);
//   - decide the wording of the permission explanation with Jordan and Marcus.

import { api } from "./browser.js";

/** Id of the static ruleset in the manifest. */
export const GPC_RULESET_ID = "gpc";
/** Id of the dynamically registered page script. */
export const GPC_SCRIPT_ID = "fmid-gpc";

const GPC_SCRIPT_FILE = "src/content/gpc.js";
const GPC_GRANT = Object.freeze({ permissions: ["scripting"], origins: ["*://*/*"] });

/**
 * How GPC can be switched on in this browser.
 *   "on_already": the browser itself already sends it (Firefox or Brave with the setting on)
 *   "extension":  this extension can send it (Chrome, Edge)
 *   "browser":    only the browser's own setting can (Firefox)
 * @returns {"on_already"|"extension"|"browser"}
 */
export function gpcSupport() {
  if (/** @type {any} */ (navigator).globalPrivacyControl === true) return "on_already";
  const declared = /** @type {any} */ (api.runtime.getManifest()).declarative_net_request;
  return declared && api.declarativeNetRequest ? "extension" : "browser";
}

/** @returns {Promise<boolean>} true when this extension is sending the signal */
export async function isGpcOn() {
  if (gpcSupport() !== "extension") return false;
  try {
    const [granted, enabled] = await Promise.all([
      api.permissions.contains(GPC_GRANT),
      api.declarativeNetRequest.getEnabledRulesets(),
    ]);
    return granted && enabled.includes(GPC_RULESET_ID);
  } catch {
    return false;
  }
}

/**
 * Switch GPC on. MUST be called straight from a click: the browser shows its permission
 * question only in answer to a real action by the person.
 * @returns {Promise<boolean>} false when the person said no or the browser cannot do it
 */
export async function turnGpcOn() {
  if (gpcSupport() !== "extension") return false;
  const granted = await api.permissions.request(GPC_GRANT);
  if (!granted) return false;
  await api.declarativeNetRequest.updateEnabledRulesets({ enableRulesetIds: [GPC_RULESET_ID] });
  await api.scripting.unregisterContentScripts({ ids: [GPC_SCRIPT_ID] }).catch(() => {});
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
  return true;
}

/** Switch GPC off and hand the extra permission back to the browser. */
export async function turnGpcOff() {
  if (!api.declarativeNetRequest) return;
  await api.declarativeNetRequest.updateEnabledRulesets({ disableRulesetIds: [GPC_RULESET_ID] });
  if (api.scripting) {
    await api.scripting.unregisterContentScripts({ ids: [GPC_SCRIPT_ID] }).catch(() => {});
  }
  await api.permissions.remove(GPC_GRANT).catch(() => {});
}
