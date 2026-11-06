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

  var btn = document.getElementById("test-conn");
  if (btn) {
    btn.addEventListener("click", function () {
      var out = document.getElementById("test-result");
      out.textContent = "Testing...";
      out.className = "";
      var form = btn.form;
      fetch("/wizard/test-connection", {
        method: "POST", credentials: "same-origin",
        headers: { "X-CSRF": form.csrf.value },
        body: new FormData(form)
      }).then(function (r) { return r.json(); }).then(function (j) {
        out.textContent = j.message;
        out.className = j.ok ? "note" : "error";
      }).catch(function () { out.textContent = "The test did not finish."; out.className = "error"; });
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
