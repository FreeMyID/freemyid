// Client for the Free My ID desktop app (native messaging host "org.freemyid.host").
//
// This is the ONLY way the extension talks to anything outside itself. There is no network
// code in this extension: no analytics, no telemetry, no remote configuration.
//
// One short-lived host process per request (runtime.sendNativeMessage). That fits a service
// worker that can be stopped at any time, and nothing here needs a long-lived connection.

import { api } from "./browser.js";
import { AppMessage, ErrorCode, HOST_NAME, isReplyTo, makeEnvelope } from "./protocol.js";

/** How long to wait for the app before saying "not connected". */
const TIMEOUT_MS = 5000;

/**
 * @typedef {Object} AppReply
 * @property {boolean} ok
 * @property {string} [error]          error code when ok is false
 * @property {string} [app_version]    status
 * @property {string|null} [broker_id] site_check
 * @property {string} [listing_state]  site_check
 * @property {boolean} [accepted]      start_removal
 */

/**
 * Send one request to the app and wait for its reply.
 * Never throws: a missing app, a timeout or a malformed reply all come back as {ok: false}.
 * Nothing about the request or the reply is logged.
 * @param {string} type one of AppMessage
 * @param {Record<string, string>} [fields]
 * @returns {Promise<AppReply>}
 */
export async function sendToApp(type, fields = {}) {
  const request = makeEnvelope(type, fields);
  /** @type {ReturnType<typeof setTimeout>|undefined} */
  let timer;
  try {
    const timeout = new Promise((_resolve, reject) => {
      timer = setTimeout(() => reject(new Error("timeout")), TIMEOUT_MS);
    });
    const reply = await Promise.race([api.runtime.sendNativeMessage(HOST_NAME, request), timeout]);
    if (!isReplyTo(request, reply)) return { ok: false, error: ErrorCode.BAD_REPLY };
    return /** @type {AppReply} */ (reply);
  } catch {
    // Host not installed, app not set up, browser refused, or timeout. All mean the same to
    // the person: the app did not answer.
    return { ok: false, error: ErrorCode.APP_NOT_CONNECTED };
  } finally {
    clearTimeout(timer);
  }
}

/** Is the app there at all? */
export const pingApp = () => sendToApp(AppMessage.PING);

/** Connected + app version. */
export const getAppStatus = () => sendToApp(AppMessage.STATUS);

/**
 * Ask the app what it knows about a broker site. Call this only for hostnames that are on the
 * bundled broker list, so the app is never told about ordinary browsing.
 * @param {string} hostname
 */
export const checkSite = (hostname) => sendToApp(AppMessage.SITE_CHECK, { hostname });

/**
 * Ask the app to start a removal for one broker. The app does all the work and applies its
 * own rules (consent, confirmed matches only, data minimisation); the extension only asks.
 * @param {string} brokerId
 */
export const startRemoval = (brokerId) => sendToApp(AppMessage.START_REMOVAL, { broker_id: brokerId });
