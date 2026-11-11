// Options page: banner on/off, "forget my Not now choices", and the Global Privacy Control
// switch (a stub, off by default). Everything is stored on this computer only.

import { gpcSupport, isGpcOn, turnGpcOff, turnGpcOn } from "../lib/gpc.js";
import { localize, t } from "../lib/i18n.js";
import { clearDismissed, isBannerEnabled, setBannerEnabled } from "../lib/settings.js";

/**
 * @param {string} id
 * @returns {any}
 */
const $ = (id) => document.getElementById(id);

const checkbox = /** @type {HTMLInputElement} */ ($("banner-enabled"));
const forget = /** @type {HTMLButtonElement} */ ($("forget"));
const result = /** @type {HTMLElement} */ ($("result"));
const gpcControl = /** @type {HTMLElement} */ ($("gpc-control"));
const gpcBox = /** @type {HTMLInputElement} */ ($("gpc-enabled"));
const gpcResult = /** @type {HTMLElement} */ ($("gpc-result"));

localize(document);

isBannerEnabled().then((enabled) => {
  checkbox.checked = enabled;
});

checkbox.addEventListener("change", async () => {
  await setBannerEnabled(checkbox.checked);
  result.textContent = t("optionsSaved");
});

forget.addEventListener("click", async () => {
  await clearDismissed();
  result.textContent = t("optionsForgotten");
});

// Global Privacy Control. Chrome and Edge: this extension can send it once the person says
// yes to the browser's permission question. Elsewhere the browser's own setting is the switch.
const support = gpcSupport();
if (support === "extension") {
  isGpcOn().then((on) => {
    gpcBox.checked = on;
  });
  gpcBox.addEventListener("change", async () => {
    // turnGpcOn() must start inside this handler: the browser only shows its permission
    // question in answer to the person's own click.
    gpcBox.disabled = true;
    try {
      if (gpcBox.checked) {
        const on = await turnGpcOn();
        gpcBox.checked = on;
        gpcResult.textContent = t(on ? "optionsGpcOn" : "optionsGpcDeclined");
      } else {
        await turnGpcOff();
        gpcResult.textContent = t("optionsGpcOff");
      }
    } catch {
      gpcBox.checked = await isGpcOn();
      gpcResult.textContent = t(gpcBox.checked ? "optionsGpcOn" : "optionsGpcDeclined");
    } finally {
      gpcBox.disabled = false;
    }
  });
} else {
  gpcControl.hidden = true;
  gpcResult.textContent = t(support === "on_already" ? "optionsGpcAlready" : "optionsGpcBrowser");
}
