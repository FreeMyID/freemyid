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
import { checkSite, getAppStatus, startRemoval } from "../lib/native.js";
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
  return {
    ok: true,
    broker: summary,
    appConnected,
    listingState,
    showBanner: forBanner && !QUIET_STATES.includes(listingState),
  };
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
  return { ok: true, connected: reply.ok, appVersion: reply.ok && typeof reply.app_version === "string" ? reply.app_version : "" };
}

/**
 * @param {unknown} message
 * @param {Sender} sender
 */
async function handle(message, sender) {
  if (typeof message !== "object" || message === null) return { ok: false, error: ErrorCode.BAD_REQUEST };
  const msg = /** @type {Record<string, unknown>} */ (message);
  switch (msg.type) {
    case Internal.SITE_CHECK:
      // A content script is answered about its own page only; the popup names the active tab.
      return isExtensionPage(sender)
        ? siteCheck(cleanHostname(msg.hostname), false)
        : siteCheck(contentScriptHost(sender), true);
    case Internal.START_REMOVAL:
      return startRemovalFor(msg.brokerId, sender);
    case Internal.DISMISS:
      return dismissFor(msg.brokerId, sender);
    case Internal.STATUS:
      return isExtensionPage(sender) ? appStatus() : { ok: false, error: ErrorCode.NOT_ALLOWED };
    default:
      return { ok: false, error: ErrorCode.BAD_REQUEST };
  }
}

api.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (sender.id !== api.runtime.id) return false;
  handle(message, sender).then(sendResponse, () => sendResponse({ ok: false, error: "internal_error" }));
  return true; // the answer comes later
});
