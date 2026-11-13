// Background script.
//
// Chrome and Edge run this file as a Manifest V3 service worker; Firefox runs the same file as
// an event page (background.scripts). Both can stop it at any time, so:
//   - listeners are registered at the top level, synchronously;
//   - nothing is kept in memory that matters (settings live in storage.local);
//   - no DOM, no window, no timers that must survive.
//
// The background is the only part that talks to the desktop app. The content script and the
// popup ask it, and it decides what they are allowed to ask for.

import { api } from "../lib/browser.js";
import { isKnownBroker, lookupHost } from "../lib/brokers.js";
import { turnGpcOffIfGrantGone } from "../lib/gpc.js";
import { checkSite, fillPlan, getAppStatus, startPairing, startRemoval } from "../lib/native.js";
import {
  ErrorCode,
  Internal,
  LISTING_STATES,
  QUIET_STATES,
  cleanHostname,
  isBrokerId,
} from "../lib/protocol.js";
import { dismissBroker, isBannerEnabled, isDismissed } from "../lib/settings.js";

/**
 * @typedef {Object} Sender
 * @property {string} [id]
 * @property {string} [url]
 * @property {number} [frameId]
 * @property {{id?: number}} [tab]
 */

/**
 * True when the message came from one of this extension's own pages (popup, options).
 * @param {Sender} sender
 */
function isExtensionPage(sender) {
  return typeof sender.url === "string" && sender.url.startsWith(api.runtime.getURL(""));
}

/**
 * Hostname of the page a content script runs in, taken from what the browser reports about
 * the sender and not from anything the page could have written. Top frame only.
 * @param {Sender} sender
 * @returns {string} "" when unknown
 */
function contentScriptHost(sender) {
  if (isExtensionPage(sender) || sender.frameId !== 0 || typeof sender.url !== "string") return "";
  try {
    const url = new URL(sender.url);
    return url.protocol === "https:" ? cleanHostname(url.hostname) : "";
  } catch {
    return "";
  }
}

/**
 * Is this site a known broker, and what does the app know about it?
 * The app is asked only when the hostname is on the bundled list.
 * @param {string} hostname
 * @param {boolean} forBanner true when a content script asks whether to show the banner
 */
async function siteCheck(hostname, forBanner) {
  const broker = await lookupHost(hostname);
  if (!broker) return { ok: true, broker: null, showBanner: false };
  const summary = { id: broker.id, name: broker.name };
  if (forBanner) {
    const allowed = broker.banner && (await isBannerEnabled()) && !(await isDismissed(broker.id));
    if (!allowed) return { ok: true, broker: summary, showBanner: false };
  }
  const reply = await checkSite(cleanHostname(hostname));
  const appConnected = reply.ok || (reply.error !== ErrorCode.APP_NOT_CONNECTED && reply.error !== ErrorCode.BAD_REPLY);
  const listingState =
    reply.ok && typeof reply.listing_state === "string" && LISTING_STATES.includes(reply.listing_state)
      ? reply.listing_state
      : "unknown";
  const paired = reply.ok || reply.error !== ErrorCode.NOT_PAIRED;
  return {
    ok: true,
    broker: summary,
    appConnected,
    paired: appConnected && paired,
    listingState,
    showBanner: forBanner && !QUIET_STATES.includes(listingState),
  };
}

/**
 * Ask the form-help content script in one tab (top frame only). Never throws.
 * @param {number} tabId
 * @param {Record<string, unknown>} message
 * @returns {Promise<any>}
 */
async function askTab(tabId, message) {
  try {
    return await api.tabs.sendMessage(tabId, message, { frameId: 0 });
  } catch {
    return undefined;
  }
}

/**
 * "Fill in the form for me": scan the form in that tab, ask the app what may go where, fill.
 * The values pass through this function once and are not kept anywhere.
 * @param {string} brokerId
 * @param {number} tabId
 */
async function fillTab(brokerId, tabId) {
  const scan = await askTab(tabId, { type: Internal.SCAN });
  if (!scan?.ok || !Array.isArray(scan.controls) || scan.controls.length === 0) {
    return { ok: false, error: ErrorCode.NO_FORM };
  }
  const plan = await fillPlan(brokerId, scan.controls);
  if (!plan.ok) return { ok: false, error: plan.error ?? ErrorCode.BAD_REPLY };
  const assignments = Array.isArray(plan.assignments) ? plan.assignments : [];
  if (assignments.length === 0) return { ok: true, filled: 0, skipped: 0 };
  const done = await askTab(tabId, { type: Internal.APPLY, assignments });
  if (!done?.ok) return { ok: false, error: ErrorCode.NO_FORM };
  return { ok: true, filled: Number(done.filled) || 0, skipped: Number(done.skipped) || 0 };
}

/**
 * From the banner: only for the broker whose page it runs on, in its own tab.
 * From the popup: the active tab it names, which must be a listed broker's https page.
 * @param {Record<string, unknown>} msg
 * @param {Sender} sender
 */
async function fillFor(msg, sender) {
  if (isExtensionPage(sender)) {
    const tabId = msg.tabId;
    if (typeof tabId !== "number") return { ok: false, error: ErrorCode.BAD_REQUEST };
    let host = "";
    try {
      const tab = await api.tabs.get(tabId);
      const url = new URL(tab?.url ?? "");
      host = url.protocol === "https:" ? cleanHostname(url.hostname) : "";
    } catch {
      host = "";
    }
    const broker = await lookupHost(host);
    if (!broker) return { ok: false, error: ErrorCode.UNKNOWN_BROKER };
    return fillTab(broker.id, tabId);
  }
  const brokerId = msg.brokerId;
  if (!isBrokerId(brokerId) || !(await isKnownBroker(brokerId))) {
    return { ok: false, error: ErrorCode.UNKNOWN_BROKER };
  }
  if (!(await senderMayActOn(brokerId, sender)) || typeof sender.tab?.id !== "number") {
    return { ok: false, error: ErrorCode.NOT_ALLOWED };
  }
  return fillTab(brokerId, sender.tab.id);
}

/** @param {Sender} sender */
async function canFill(sender) {
  if (typeof sender.tab?.id !== "number") return false;
  const probe = await askTab(sender.tab.id, { type: Internal.FORM_PROBE });
  return probe?.ok === true && Number(probe.boxes) > 0;
}

async function pairStart() {
  const reply = await startPairing();
  return reply.ok && typeof reply.code === "string" && /^\d{6}$/.test(reply.code)
    ? { ok: true, code: reply.code }
    : { ok: false, error: reply.error ?? ErrorCode.BAD_REPLY };
}

/**
 * A content script may act only on the broker whose site it runs on. Extension pages (the
 * popup) may act on any broker in the bundled list.
 * @param {string} brokerId
 * @param {Sender} sender
 */
async function senderMayActOn(brokerId, sender) {
  if (isExtensionPage(sender)) return true;
  const broker = await lookupHost(contentScriptHost(sender));
  return broker !== null && broker.id === brokerId;
}

/**
 * @param {unknown} brokerId
 * @param {Sender} sender
 */
async function startRemovalFor(brokerId, sender) {
  if (!isBrokerId(brokerId) || !(await isKnownBroker(brokerId))) {
    return { ok: false, error: ErrorCode.UNKNOWN_BROKER };
  }
  if (!(await senderMayActOn(brokerId, sender))) return { ok: false, error: ErrorCode.NOT_ALLOWED };
  const reply = await startRemoval(brokerId);
  return reply.ok ? { ok: true, accepted: reply.accepted === true } : { ok: false, error: reply.error ?? ErrorCode.BAD_REPLY };
}

/**
 * @param {unknown} brokerId
 * @param {Sender} sender
 */
async function dismissFor(brokerId, sender) {
  if (!isBrokerId(brokerId) || !(await isKnownBroker(brokerId))) {
    return { ok: false, error: ErrorCode.UNKNOWN_BROKER };
  }
  if (!(await senderMayActOn(brokerId, sender))) return { ok: false, error: ErrorCode.NOT_ALLOWED };
  await dismissBroker(brokerId);
  return { ok: true };
}

async function appStatus() {
  const reply = await getAppStatus();
  return {
    ok: true,
    connected: reply.ok,
    appVersion: reply.ok && typeof reply.app_version === "string" ? reply.app_version : "",
    paired: reply.ok && reply.paired === true,
    appOpen: reply.ok && reply.app_open === true,
  };
}

/**
 * @param {unknown} message
 * @param {Sender} sender
 */
async function handle(message, sender) {
  if (typeof message !== "object" || message === null) return { ok: false, error: ErrorCode.BAD_REQUEST };
  const msg = /** @type {Record<string, unknown>} */ (message);
  switch (msg.type) {
    case Internal.SITE_CHECK: {
      // A content script is answered about its own page only; the popup names the active tab.
      if (isExtensionPage(sender)) return siteCheck(cleanHostname(msg.hostname), false);
      const check = await siteCheck(contentScriptHost(sender), true);
      return check.showBanner && check.paired ? { ...check, canFill: await canFill(sender) } : check;
    }
    case Internal.START_REMOVAL:
      return startRemovalFor(msg.brokerId, sender);
    case Internal.DISMISS:
      return dismissFor(msg.brokerId, sender);
    case Internal.STATUS:
      return isExtensionPage(sender) ? appStatus() : { ok: false, error: ErrorCode.NOT_ALLOWED };
    case Internal.PAIR_START:
      return isExtensionPage(sender) ? pairStart() : { ok: false, error: ErrorCode.NOT_ALLOWED };
    case Internal.FILL:
      return fillFor(msg, sender);
    default:
      return { ok: false, error: ErrorCode.BAD_REQUEST };
  }
}

// Global Privacy Control. The person can take the "all websites" permission back in the
// browser's own settings, without opening ours. When that happens, and each time the
// background starts, the rest of the signal is switched off too if the permission is gone, so
// nothing stays half on. The background can only switch it OFF; switching it on needs the
// person's click on the Settings page.
api.permissions?.onRemoved?.addListener(() => {
  void turnGpcOffIfGrantGone();
});
void turnGpcOffIfGrantGone();

api.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (sender.id !== api.runtime.id) return false;
  handle(message, sender).then(sendResponse, () => sendResponse({ ok: false, error: "internal_error" }));
  return true; // the answer comes later
});
