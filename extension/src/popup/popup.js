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

/** @returns {Promise<{hostname: string, tabId: number|null}>} the active tab, if a web page */
async function activeTab() {
  try {
    const [tab] = await api.tabs.query({ active: true, currentWindow: true });
    const url = new URL(tab?.url ?? "");
    const web = url.protocol === "https:" || url.protocol === "http:";
    return { hostname: web ? cleanHostname(url.hostname) : "", tabId: typeof tab?.id === "number" ? tab.id : null };
  } catch {
    return { hostname: "", tabId: null };
  }
}

/** @type {boolean} */
let paired = false;

async function showAppStatus() {
  const status = await ask({ type: Internal.STATUS });
  paired = status?.paired === true;
  if (!status?.connected) $("app-status").textContent = t("popupAppNotConnected");
  else if (!paired) $("app-status").textContent = t("popupAppNotPaired");
  else $("app-status").textContent = t("popupAppConnected", status.appVersion || "?");
  $("pair-box").hidden = !status?.connected || paired;
  return paired;
}

async function pair() {
  const button = /** @type {HTMLButtonElement} */ ($("pair"));
  button.disabled = true;
  const reply = await ask({ type: Internal.PAIR_START });
  const out = $("pair-code");
  out.hidden = false;
  out.textContent = reply?.ok
    ? t("popupPairCode", `${reply.code.slice(0, 3)} ${reply.code.slice(3)}`)
    : t("popupPairFailed");
  button.disabled = false;
}

/** @param {number} tabId */
async function fillForm(tabId) {
  const button = /** @type {HTMLButtonElement} */ ($("fill"));
  button.disabled = true;
  $("result").textContent = t("bannerFillWorking");
  const reply = await ask({ type: Internal.FILL, tabId });
  const messages = /** @type {Record<string, string>} */ ({
    app_closed: "bannerFillOpenApp",
    choose_person: "bannerFillChoosePerson",
    not_paired: "bannerFillNotPaired",
    no_permission: "bannerFillNoPermission",
    no_form: "bannerFillNothing",
    app_not_connected: "bannerNoApp",
  });
  if (reply?.ok) {
    $("result").textContent = reply.filled ? t("bannerFilled", String(reply.filled)) : t("bannerFillNothing");
  } else {
    $("result").textContent = t(messages[reply?.error] ?? "bannerFillFailed");
  }
  button.disabled = false;
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
  const { hostname, tabId } = await activeTab();
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
  if ((await appReady) && tabId !== null) {
    const fill = $("fill");
    fill.hidden = false;
    fill.addEventListener("click", () => fillForm(tabId));
  }
}

localize(document);
$("open-options").addEventListener("click", () => api.runtime.openOptionsPage());
$("pair").addEventListener("click", pair);
const appReady = showAppStatus();
showSiteStatus();
