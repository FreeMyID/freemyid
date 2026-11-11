// One namespace for every browser.
//
// Firefox exposes the WebExtension APIs as `browser` (promise based). Chrome and Edge expose
// them as `chrome`, and under Manifest V3 those calls return promises too when no callback is
// passed. So a single alias is all the "polyfill" this extension needs. We wrote it ourselves
// on purpose: no third-party code ships in this extension.
//
// The content script (src/content/banner.js) is a classic script and cannot import this file,
// so it repeats the one line below.

/** @type {typeof chrome} */
export const api = /** @type {any} */ (globalThis).browser ?? /** @type {any} */ (globalThis).chrome;
