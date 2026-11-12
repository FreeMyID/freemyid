// Toolbar popup: is the app connected, is this site a broker, and the status for this site.
//
// The popup learns the active tab's address through activeTab (granted by the click that opened
// it) and keeps only the hostname. Everything else goes through the background.

import { api } from "../lib/browser.js";
import { localize, t } from "../lib/i18n.js";
import { Internal, LISTING_STATES, cleanHostname } from "../lib/protocol.js";

/**
 * @param {string} id
 * @returns {HTMLElement}
 */
const $ = (id) => /** @type {HTMLElement} */ (document.getElementById(id));

/**
 * Ask the background. Never throws.
 * @param {Record<string, unknown>} message
 * @returns {Promise<any>}
 */
async function ask(message) {
  try {
    return await api.runtime.sendMessage(message);
  } catch {
    return undefined;
  }
}

/** @returns {Promise<string>} hostname of the active tab, or "" when it is not a web page */
async function activeHostname() {
  try {
    const [tab] = await api.tabs.query({ active: true, currentWindow: true });
    const url = new URL(tab?.url ?? "");
    return url.protocol === "https:" || url.protocol === "http:" ? cleanHostname(url.hostname) : "";
  } catch {
    return "";
  }
}

async function showAppStatus() {
  const status = await ask({ type: Internal.STATUS });
  $("app-status").textContent = status?.connected
    ? t("popupAppConnected", status.appVersion || "?")
    : t("popupAppNotConnected");
}

/** @param {string} brokerId */
async function removeMe(brokerId) {
  const button = /** @type {HTMLButtonElement} */ ($("remove"));
  button.disabled = true;
  $("result").textContent = t("bannerWorking");
  const reply = await ask({ type: Internal.START_REMOVAL, brokerId });
  if (reply?.ok) $("result").textContent = t("bannerStarted");
  else if (!reply || reply.error === "app_not_connected") $("result").textContent = t("bannerNoApp");
  else $("result").textContent = t("bannerNotReady");
  button.disabled = false;
}

async function showSiteStatus() {
  const hostname = await activeHostname();
  if (!hostname) {
    $("site-status").textContent = t("popupSiteUnknown");
    return;
  }
  const check = await ask({ type: Internal.SITE_CHECK, hostname });
  if (!check?.ok) {
    $("site-status").textContent = t("popupSiteUnknown");
    return;
  }
  if (!check.broker) {
    $("site-status").textContent = t("popupSiteNotBroker");
    return;
  }
  $("site-status").textContent = t("popupSiteBroker", check.broker.name);
  if (check.appConnected) {
    const state = LISTING_STATES.includes(check.listingState) ? check.listingState : "unknown";
    $("state-status").textContent = t(`state_${state}`);
    $("state-row").hidden = false;
  }
  const button = $("remove");
  button.hidden = false;
  button.addEventListener("click", () => removeMe(check.broker.id));
}

localize(document);
$("open-options").addEventListener("click", () => api.runtime.openOptionsPage());
showAppStatus();
showSiteStatus();
