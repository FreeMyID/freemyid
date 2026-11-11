// Message names and shapes, in one place.
//
// Two kinds of messages exist:
//   1. App messages: extension <-> Free My ID desktop app, over native messaging.
//      Versioned envelopes {v, type, id, ...}. Mirrored in src/freemyid/native_host.py.
//   2. Internal messages: content script / popup / options -> background, inside the extension.
//
// Neither kind ever carries personal details. The only things that travel are a site hostname
// that is already on the bundled broker list, a broker id, and status words.

/** Native messaging host name. Must match the host manifest installed by the desktop app. */
export const HOST_NAME = "org.freemyid.host";

/** Envelope version. Bump only with a matching change in native_host.py and docs/EXTENSION.md. */
export const PROTOCOL_VERSION = 1;

/** App message types (requests). */
export const AppMessage = Object.freeze({
  PING: "ping",
  STATUS: "status",
  SITE_CHECK: "site_check",
  START_REMOVAL: "start_removal",
});

/** Internal message types. The content script repeats these literals (it cannot import). */
export const Internal = Object.freeze({
  SITE_CHECK: "fmid.site_check",
  START_REMOVAL: "fmid.start_removal",
  DISMISS: "fmid.dismiss",
  STATUS: "fmid.status",
});

/** Listing states, the same words as freemyid.models.ListingState. */
export const LISTING_STATES = Object.freeze([
  "unknown",
  "not_found",
  "found",
  "submitted",
  "awaiting_verification",
  "confirmed",
  "removed",
  "reappeared",
  "needs_human",
  "error",
]);

/** States where a request is already on its way, so the banner stays quiet. */
export const QUIET_STATES = Object.freeze(["submitted", "awaiting_verification", "confirmed", "removed"]);

/** Error codes the extension itself produces (the app has its own, see docs/EXTENSION.md). */
export const ErrorCode = Object.freeze({
  APP_NOT_CONNECTED: "app_not_connected",
  BAD_REPLY: "bad_reply",
  BAD_REQUEST: "bad_request",
  NOT_ALLOWED: "not_allowed",
  UNKNOWN_BROKER: "unknown_broker",
});

const HOSTNAME = /^(?=.{4,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$/;
const BROKER_ID = /^[a-z0-9_]{1,64}$/;

/**
 * @typedef {Object} Envelope
 * @property {1} v            protocol version
 * @property {string} type    one of AppMessage
 * @property {string} id      request id; the reply repeats it
 */

/**
 * Lower-case a hostname and drop a trailing dot. Returns "" when it is not a plain hostname.
 * @param {unknown} value
 * @returns {string}
 */
export function cleanHostname(value) {
  if (typeof value !== "string") return "";
  const host = value.trim().toLowerCase().replace(/\.$/, "");
  return HOSTNAME.test(host) ? host : "";
}

/**
 * @param {unknown} value
 * @returns {value is string}
 */
export function isBrokerId(value) {
  return typeof value === "string" && BROKER_ID.test(value);
}

/**
 * Build a request envelope.
 * @param {string} type
 * @param {Record<string, string>} [fields]
 * @returns {Envelope & Record<string, string>}
 */
export function makeEnvelope(type, fields = {}) {
  return { ...fields, v: PROTOCOL_VERSION, type, id: crypto.randomUUID() };
}

/**
 * Check that a reply belongs to the request and has the expected shape.
 * @param {Envelope} request
 * @param {unknown} reply
 * @returns {boolean}
 */
export function isReplyTo(request, reply) {
  if (typeof reply !== "object" || reply === null) return false;
  const r = /** @type {Record<string, unknown>} */ (reply);
  return r.v === PROTOCOL_VERSION && r.id === request.id && typeof r.ok === "boolean";
}
