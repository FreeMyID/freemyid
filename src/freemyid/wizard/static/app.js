"use strict";
(function () {
  document.documentElement.className += " js";

  // Show or hide blocks depending on a radio choice: data-when="name:value1,value2".
  var conds = document.querySelectorAll("[data-when]");
  function sync() {
    conds.forEach(function (el) {
      var spec = el.getAttribute("data-when").split(":");
      var checked = document.querySelector('input[name="' + spec[0] + '"]:checked');
      el.hidden = !(checked && spec[1].split(",").indexOf(checked.value) !== -1);
    });
  }
  if (conds.length) {
    document.addEventListener("change", function (e) {
      if (e.target && e.target.type === "radio") { sync(); }
    });
    sync();
  }

  var back = document.querySelector("[data-back]");
  if (back && window.history.length > 1) {
    back.addEventListener("click", function (e) { e.preventDefault(); window.history.back(); });
  }

  var btn = document.getElementById("test-conn");
  if (btn) {
    var out = document.getElementById("test-result");
    var box = document.getElementById("trust-box");
    var form = btn.form;
    var post = function (url, body) {
      return fetch(url, { method: "POST", credentials: "same-origin",
        headers: { "X-CSRF": form.csrf.value }, body: body }).then(function (r) { return r.json(); });
    };
    var runTest = function () {
      out.textContent = "Testing..."; out.className = ""; box.hidden = true;
      post("/wizard/test-connection", new FormData(form)).then(function (j) {
        if (j.status === "trust") {
          out.textContent = "";
          document.getElementById("trust-text").textContent = j.message;
          document.getElementById("trust-code").textContent = j.display;
          document.getElementById("trust-question").firstChild.textContent = j.question;
          box.hidden = false;
          document.getElementById("trust-yes").focus();
          return;
        }
        out.textContent = j.message;
        out.className = j.ok ? "note" : "error";
      }).catch(function () { out.textContent = "The test did not finish."; out.className = "error"; });
    };
    btn.addEventListener("click", runTest);
    document.getElementById("trust-yes").addEventListener("click", function () {
      var fd = new FormData(); fd.append("answer", "yes");
      post("/wizard/trust-certificate", fd).then(function (j) { if (j.ok) { runTest(); } });
    });
    document.getElementById("trust-no").addEventListener("click", function () {
      var fd = new FormData(); fd.append("answer", "no");
      post("/wizard/trust-certificate", fd).then(function (j) {
        box.hidden = true; out.textContent = j.message; out.className = "error";
      });
    });
  }

  // Copy buttons: data-copy holds the text.
  function copyText(text) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      return navigator.clipboard.writeText(text);
    }
    return new Promise(function (resolve, reject) {
      var ta = document.createElement("textarea");
      ta.value = text; ta.setAttribute("readonly", "");
      ta.style.position = "fixed"; ta.style.opacity = "0";
      document.body.appendChild(ta); ta.select();
      var ok = false;
      try { ok = document.execCommand("copy"); } catch (e) { ok = false; }
      document.body.removeChild(ta);
      if (ok) { resolve(); } else { reject(); }
    });
  }
  document.querySelectorAll("[data-copy]").forEach(function (el) {
    el.addEventListener("click", function () {
      var old = el.textContent;
      copyText(el.getAttribute("data-copy")).then(function () {
        el.textContent = "Copied!";
      }, function () { el.textContent = "Select and copy by hand"; });
      setTimeout(function () { el.textContent = old; }, 2000);
    });
  });

  document.querySelectorAll("[data-print]").forEach(function (el) {
    el.addEventListener("click", function () { window.print(); });
  });
  document.querySelectorAll("[data-confirm]").forEach(function (el) {
    el.addEventListener("click", function (e) {
      if (!window.confirm(el.getAttribute("data-confirm"))) { e.preventDefault(); }
    });
  });
})();

(function () {
  // Light/dark toggle. Starts from the computer's setting; the choice is kept in a cookie.
  var btn = document.getElementById("theme-toggle");
  if (!btn) { return; }
  var root = document.documentElement;
  var dark = function () {
    var t = root.getAttribute("data-theme");
    return t ? t === "dark" : window.matchMedia("(prefers-color-scheme: dark)").matches;
  };
  var show = function () {
    btn.setAttribute("aria-pressed", dark() ? "true" : "false");
    document.getElementById("theme-label").textContent = dark() ? "Light" : "Dark";
  };
  btn.hidden = false;
  show();
  btn.addEventListener("click", function () {
    var next = dark() ? "light" : "dark";
    root.setAttribute("data-theme", next);
    document.cookie = "fmi_theme=" + next + "; path=/; max-age=31536000; SameSite=Strict";
    show();
  });
})();

(function () {
  // "Print this page" buttons (inline handlers are blocked by the page policy).
  document.querySelectorAll("[data-print]").forEach(function (b) {
    b.addEventListener("click", function () { window.print(); });
  });
})();
