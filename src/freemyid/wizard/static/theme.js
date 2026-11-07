"use strict";
// Runs before the page paints, so there is no flash. The choice lives in a cookie on this
// computer only (a cookie is shared across ports, a localStorage entry is not).
(function () {
  var m = document.cookie.match(/(?:^|; )fmi_theme=(light|dark)/);
  if (m) { document.documentElement.setAttribute("data-theme", m[1]); }
})();
