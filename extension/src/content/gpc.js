// Global Privacy Control: the page-side half of the signal (STUB, off by default).
//
// The header half is rules/gpc.json ("Sec-GPC: 1"). This file is the other half the GPC
// proposal asks for: navigator.globalPrivacyControl reads true, so a site's own scripts can see
// the same choice the header states.
//
// It is NOT in the manifest. lib/gpc.js registers it only after the person turned the setting
// on in Settings and the browser granted the extra permission. Chrome and Edge only; Firefox
// has its own GPC setting and this file is left out of the Firefox package.
//
// It runs in the page's own world, so it is kept as small as it can be. It reads nothing,
// stores nothing, sends nothing and touches nothing else on the page. It states a true fact
// (the person switched the signal on); it does not disguise the browser in any way.

(() => {
  "use strict";
  try {
    Object.defineProperty(Navigator.prototype, "globalPrivacyControl", {
      get: () => true,
      configurable: true,
      enumerable: true,
    });
  } catch {
    // The page or the browser already defines it. Leave it alone.
  }
})();
