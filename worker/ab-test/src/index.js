// Free My ID home-page A/B/C test (docs/AB_TEST.md). Cloudflare Worker on two routes:
//   freemyid.org/      picks a design at random and serves that arm's home (the HTML of /x/<arm>/) at "/".
//   freemyid.org/x/*   arm pages pass through; an arm's get/windows/ counts a download and redirects to it.
// Cookie-free: the visitor stays in their design because every link inside an arm points into /x/<arm>/.
// Counts are daily totals in D1 (schema.sql): one row per day, arm, event ("assign", "view", "download") and page
// path, whose count goes up by one. Never an IP address, user agent, referrer, location, cookie or identifier.
// Kill switch: AB_ENABLED != "1" sends everything straight to the site, exactly as without the worker.

export const ARMS = ["control", "heritage", "frontier", "glory"];
const BOT = /bot|crawl|spider|slurp|preview|facebookexternalhit|embedly|whatsapp|telegram|lighthouse|headless|curl|wget|python|httpclient/i;

/** Weights from env.AB_WEIGHTS ('{"control":1,"heritage":1,...}'); unknown arms dropped, default equal. */
export function weights(raw) {
  let w = {};
  try { w = raw ? JSON.parse(raw) : {}; } catch { w = {}; }
  const out = ARMS.map((a) => [a, Number.isFinite(w[a]) && w[a] >= 0 ? w[a] : raw ? 0 : 1]);
  return out.some(([, n]) => n > 0) ? out : ARMS.map((a) => [a, 1]);
}

/** r in [0, 1): weighted pick. */
export function pickArm(ws, r) {
  const total = ws.reduce((s, [, n]) => s + n, 0);
  let x = r * total;
  for (const [a, n] of ws) { if (x < n) return a; x -= n; }
  return ws.filter(([, n]) => n > 0).at(-1)[0];
}

export const isBot = (ua) => !ua || BOT.test(ua);

/** "/x/heritage/faq/" -> { arm: "heritage", rest: "/faq/" }, or null. */
export function armPath(pathname) {
  const m = pathname.match(/^\/x\/([a-z]+)(\/.*)?$/);
  if (!m || !ARMS.includes(m[1])) return null;
  return { arm: m[1], rest: m[2] || "/" };
}

const UPSERT = "INSERT INTO totals (day, arm, event, page, n) VALUES (?1, ?2, ?3, ?4, 1) " +
  "ON CONFLICT (day, arm, event, page) DO UPDATE SET n = n + 1";

/** Adds one to today's total for (arm, event, page). Runs after the response; never breaks the page. */
function count(env, ctx, arm, event, page) {
  if (!env.DB) return;
  const day = new Date().toISOString().slice(0, 10);
  try {
    const p = env.DB.prepare(UPSERT).bind(day, arm, event, page).run().catch(() => {});
    if (ctx?.waitUntil) ctx.waitUntil(p);
  } catch { /* counting never breaks the page */ }
}

export default {
  async fetch(request, env, ctx) {
    if (env.AB_ENABLED !== "1" || !["GET", "HEAD"].includes(request.method)) return fetch(request);
    const url = new URL(request.url);
    const bot = isBot(request.headers.get("user-agent") || "");

    if (url.pathname === "/") {
      if (bot) return fetch(request); // search engines and link previews always get the normal home page
      const arm = pickArm(weights(env.AB_WEIGHTS), Math.random());
      const res = await fetch(new Request(new URL(`/x/${arm}/`, url), request));
      if (!res.ok) return fetch(request); // an arm missing at the origin never breaks the home page
      if (request.method === "GET") count(env, ctx, arm, "assign", "/");
      const out = new Response(res.body, res);
      out.headers.set("Cache-Control", "no-store"); // each visit draws again; browsers and the edge never keep one arm
      out.headers.delete("ETag");
      out.headers.delete("Last-Modified");
      return out;
    }

    const ap = armPath(url.pathname);
    if (!ap) return fetch(request);
    if (/^\/get\/windows\/?$/.test(ap.rest)) {
      if (!bot && request.method === "GET") count(env, ctx, ap.arm, "download", "/get/windows/");
      return Response.redirect(env.DOWNLOAD_URL || "https://freemyid.org/get/windows", 302);
    }
    const res = await fetch(request);
    const html = (res.headers.get("content-type") || "").includes("text/html");
    if (!bot && res.ok && html && request.method === "GET") count(env, ctx, ap.arm, "view", ap.rest);
    return res;
  },
};
