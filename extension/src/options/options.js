// Options page: banner on/off and "forget my Not now choices". Stored on this computer only.

import { localize, t } from "../lib/i18n.js";
import { clearDismissed, isBannerEnabled, setBannerEnabled } from "../lib/settings.js";

const checkbox = /** @type {HTMLInputElement} */ (document.getElementById("banner-enabled"));
const forget = /** @type {HTMLButtonElement} */ (document.getElementById("forget"));
const result = /** @type {HTMLElement} */ (document.getElementById("result"));

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
