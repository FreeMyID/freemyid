// Content script: the banner on known people-search sites.
//
// Runs ONLY on the hosts listed in the manifest (built from the public broker list), in the
// top frame, in the browser's isolated world.
//
// What it does: asks the background "should I show the banner here?", and if so shows a calm,
// dismissible card with two buttons.
// What it does NOT do: it reads nothing from the page. Not the text, not forms, not cookies,
// not the address beyond what the browser already tells the background about the sender.
// It never touches a CAPTCHA or any "are you human" check, never fills a form and never clicks
// anything on the page. (Form help for the Assisted tier is future work; see assisted-fill.js.)
//
// This is a classic script (manifest content scripts cannot be ES modules), so it cannot import
// from ../lib. The message names below repeat lib/protocol.js; tests keep them in step.

(() => {
  "use strict";

  if (window.top !== window) return;

  /** @type {typeof chrome} */
  const api = /** @type {any} */ (globalThis).browser ?? /** @type {any} */ (globalThis).chrome;

  const MSG_SITE_CHECK = "fmid.site_check";
  const MSG_START_REMOVAL = "fmid.start_removal";
  const MSG_DISMISS = "fmid.dismiss";

  /** @param {string} key */
  const t = (key) => api.i18n.getMessage(key) || key;

  const CSS = `
    :host { all: initial; }
    .card {
      position: fixed; top: 16px; right: 16px; z-index: 2147483647;
      box-sizing: border-box; width: min(440px, calc(100vw - 32px));
      padding: 20px; border: 2px solid #1b3366; border-radius: 12px;
      background: #ffffff; color: #151b26;
      font: 400 20px/1.45 system-ui, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      box-shadow: 0 6px 24px rgba(0, 0, 0, 0.25);
    }
    .brand { margin: 0 0 8px; font-size: 16px; font-weight: 700; color: #1b3366; }
    .text { margin: 0 0 16px; }
    .buttons { display: flex; flex-wrap: wrap; gap: 12px; }
    button {
      min-height: 48px; padding: 10px 20px; border-radius: 8px; cursor: pointer;
      font: 700 19px/1.2 system-ui, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }
    button:focus-visible { outline: 3px solid #a3202e; outline-offset: 2px; }
    button[disabled] { opacity: 0.6; cursor: default; }
    .primary { background: #1b3366; color: #ffffff; border: 2px solid #1b3366; }
    .secondary { background: #ffffff; color: #1b3366; border: 2px solid #1b3366; }
    @media (prefers-color-scheme: dark) {
      .card { background: #0f1520; color: #f2f5fa; border-color: #c4d5f7; }
      .brand { color: #c4d5f7; }
      .primary { background: #c4d5f7; color: #0f1520; border-color: #c4d5f7; }
      .secondary { background: #0f1520; color: #c4d5f7; border-color: #c4d5f7; }
      button:focus-visible { outline-color: #f5a3ab; }
    }
    @media (forced-colors: active) {
      .card, button { border: 2px solid CanvasText; }
    }
  `;

  /**
   * @param {string} tag
   * @param {string} className
   * @param {string} [text]
   */
  function make(tag, className, text) {
    const el = document.createElement(tag);
    el.className = className;
    if (text) el.textContent = text; // text only, never HTML
    return el;
  }

  /** @param {{id: string, name: string}} broker */
  function showBanner(broker) {
    const host = document.createElement("div");
    const shadow = host.attachShadow({ mode: "closed" });
    const sheet = new CSSStyleSheet();
    sheet.replaceSync(CSS);
    shadow.adoptedStyleSheets = [sheet];

    const card = make("section", "card");
    card.setAttribute("role", "region");
    card.setAttribute("aria-label", t("bannerLabel"));
    const text = make("p", "text", t("bannerText"));
    text.setAttribute("role", "status");
    const buttons = make("div", "buttons");
    const remove = /** @type {HTMLButtonElement} */ (make("button", "primary", t("bannerRemove")));
    const notNow = /** @type {HTMLButtonElement} */ (make("button", "secondary", t("bannerNotNow")));
    remove.type = "button";
    notNow.type = "button";
    buttons.append(remove, notNow);
    card.append(make("p", "brand", t("extName")), text, buttons);
    shadow.append(card);

    const close = () => host.remove();

    remove.addEventListener("click", async (event) => {
      if (!event.isTrusted) return; // a real click by the person, not one made by the page
      remove.disabled = true;
      notNow.disabled = true;
      text.textContent = t("bannerWorking");
      /** @type {{ok?: boolean, error?: string}|undefined} */
      let reply;
      try {
        reply = await api.runtime.sendMessage({ type: MSG_START_REMOVAL, brokerId: broker.id });
      } catch {
        reply = undefined;
      }
      if (reply?.ok) text.textContent = t("bannerStarted");
      else if (!reply || reply.error === "app_not_connected") text.textContent = t("bannerNoApp");
      else text.textContent = t("bannerNotReady");
      const done = /** @type {HTMLButtonElement} */ (make("button", "secondary", t("bannerClose")));
      done.type = "button";
      done.addEventListener("click", close);
      buttons.replaceChildren(done);
    });

    notNow.addEventListener("click", (event) => {
      if (!event.isTrusted) return;
      api.runtime.sendMessage({ type: MSG_DISMISS, brokerId: broker.id }).catch(() => {});
      close();
    });

    document.documentElement.append(host);
  }

  api.runtime
    .sendMessage({ type: MSG_SITE_CHECK })
    .then((/** @type {any} */ reply) => {
      if (reply?.ok && reply.showBanner && reply.broker) showBanner(reply.broker);
    })
    .catch(() => {
      // Background not reachable (extension updating or switched off): show nothing.
    });
})();
