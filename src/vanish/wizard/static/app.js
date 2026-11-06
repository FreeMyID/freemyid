"use strict";
(function () {
  var presets = JSON.parse((document.getElementById("presets") || {}).textContent || "{}");
  var prov = document.getElementById("provider");
  var custom = document.getElementById("custom-hosts");
  function sync() {
    if (!prov || !custom) { return; }
    var p = prov.value;
    custom.hidden = p !== "other";
    var info = document.getElementById("provider-help");
    if (info) { info.textContent = (presets[p] || {}).help || ""; }
  }
  if (prov) { prov.addEventListener("change", sync); sync(); }
  var btn = document.getElementById("test-conn");
  if (btn) {
    btn.addEventListener("click", function () {
      var out = document.getElementById("test-result");
      out.textContent = "Testing...";
      var form = btn.form;
      fetch("/wizard/test-connection", {
        method: "POST", credentials: "same-origin",
        headers: { "X-CSRF": form.csrf.value },
        body: new FormData(form)
      }).then(function (r) { return r.json(); }).then(function (j) {
        out.textContent = j.message;
        out.className = j.ok ? "note" : "error";
      }).catch(function () { out.textContent = "Test failed."; out.className = "error"; });
    });
  }
  document.querySelectorAll("[data-print]").forEach(function (el) {
    el.addEventListener("click", function () { window.print(); });
  });
  var rec = document.querySelectorAll("[data-confirm]");
  rec.forEach(function (el) {
    el.addEventListener("click", function (e) {
      if (!window.confirm(el.getAttribute("data-confirm"))) { e.preventDefault(); }
    });
  });
})();
