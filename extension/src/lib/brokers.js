// Broker-domain lookup.
//
// data/broker_domains.json is written by tools/build_extension.py from the PUBLIC sample
// registry and ships inside the extension package. It is read from the package itself
// (runtime.getURL), never from the network, and it is not updated remotely: a new list means a
// new extension version that went through store review.

import { api } from "./browser.js";
import { cleanHostname } from "./protocol.js";

/**
 * @typedef {Object} BrokerList
 * @property {number} schema
 * @property {string} registry_version
 * @property {Record<string, {name: string, banner: boolean}>} brokers  by broker id
 * @property {Record<string, string>} hosts                             hostname -> broker id
 */

/**
 * @typedef {Object} BrokerMatch
 * @property {string} id      broker id, e.g. "spokeo"
 * @property {string} name    display name
 * @property {boolean} banner true when the banner may be shown on this broker's own site
 */

/** @type {Promise<BrokerList>|undefined} */
let listPromise;

/**
 * Load the bundled list once per background lifetime.
 * @returns {Promise<BrokerList>}
 */
export function loadBrokerList() {
  listPromise ??= fetch(api.runtime.getURL("data/broker_domains.json")).then((r) => r.json());
  return listPromise;
}

/**
 * Exact-host lookup. Unknown or malformed hostnames return null.
 * @param {unknown} hostname
 * @returns {Promise<BrokerMatch|null>}
 */
export async function lookupHost(hostname) {
  const host = cleanHostname(hostname);
  if (!host) return null;
  const list = await loadBrokerList();
  if (!Object.hasOwn(list.hosts, host)) return null;
  const id = list.hosts[host];
  const broker = list.brokers[id];
  return broker ? { id, name: broker.name, banner: broker.banner === true } : null;
}

/**
 * @param {unknown} brokerId
 * @returns {Promise<boolean>}
 */
export async function isKnownBroker(brokerId) {
  if (typeof brokerId !== "string") return false;
  const list = await loadBrokerList();
  return Object.hasOwn(list.brokers, brokerId);
}
