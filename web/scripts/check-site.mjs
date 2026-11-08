// Checks for the built v3 site (web/dist). Node stdlib only. Exit 1 on any problem.
//   node scripts/check-site.mjs dist
// Every page: lang, one <h1>, title <= 60, description <= 155, canonical, referrer meta, CSP meta
// (no 'unsafe-inline'/'unsafe-eval'; script hashes match the inline scripts present), no style=""
// attributes, no inline event handlers, no third-party asset URLs, every <img> has alt/width/height,
// internal links and #anchors resolve, sitemap lists every indexable page and nothing else,
// no mention of the private registry file, no deployed .js that no page loads. Then budgets
// (gzip, KiB = 1024 bytes): home first view < 300 KiB, JS on home < 80 KiB, CSS < 20 KiB.
import { createHash } from "node:crypto";
import { existsSync, readdirSync, readFileSync, statSync } from "node:fs";
import { join, relative } from "node:path";
import { gzipSync } from "node:zlib";

const dist = process.argv[2] || "dist";
// Origin and base path come from site_src/site.yaml (same source as astro.config.mjs and the v2 build).
const SITE_YAML = readFileSync(new URL("../../site_src/site.yaml", import.meta.url), "utf8");
const yamlValue = (key) => {
  const m = SITE_YAML.match(new RegExp(`^${key}:\\s*(\\S+)`, "m"));
  if (!m) throw new Error(`site_src/site.yaml: ${key} missing`);
  return m[1];
};
const BASE_PATH = yamlValue("base_path");
const ORIGIN = new URL(yamlValue("base_url")).origin;
const reEsc = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
const errors = [];
const err = (f, m) => errors.push(`${f}: ${m}`);

function* walk(dir) {
  for (const n of readdirSync(dir)) {
    const p = join(dir, n);
    if (statSync(p).isDirectory()) yield* walk(p);
    else yield p;
  }
}
const files = [...walk(dist)].map((p) => relative(dist, p).split("\\").join("/"));
const htmlFiles = files.filter((f) => f.endsWith(".html"));
const read = (f) => readFileSync(join(dist, f), "utf8");
const gz = (buf) => gzipSync(buf, { level: 9 }).length;
const sha = (s) => `'sha256-${createHash("sha256").update(s, "utf8").digest("base64")}'`;

// --- collect ids per page for anchor checks
const ids = new Map();
for (const f of htmlFiles) ids.set(f, new Set([...read(f).matchAll(/\sid="([^"]+)"/g)].map((m) => m[1])));

function resolveLocal(fromFile, href) {
  // returns [file, fragment] inside dist for a local URL, or null if external / not a page
  let [path, frag = ""] = href.split("#");
  if (path === "") return [fromFile, frag];
  if (/^[a-z]+:/i.test(path) || path.startsWith("//")) return null;
  path = path.split("?")[0];
  if (path.startsWith(BASE_PATH)) path = path.slice(BASE_PATH.length);
  else if (path.startsWith("/")) return ["__outside_base__" + path, frag];
  else {
    const dir = fromFile.includes("/") ? fromFile.slice(0, fromFile.lastIndexOf("/") + 1) : "";
    path = new URL(path, "http://x/" + dir).pathname.slice(1);
  }
  if (path === "" || path.endsWith("/")) path += "index.html";
  return [decodeURIComponent(path), frag];
}

const indexable = [];
for (const f of htmlFiles) {
  const html = read(f);
  const isRedirect = /http-equiv="refresh"/i.test(html);
  if (!/<html lang="en"/.test(html)) err(f, "missing <html lang=\"en\">");
  const title = html.match(/<title>([^<]*)<\/title>/)?.[1];
  if (!title) err(f, "missing <title>");
  else if (title.length > 60) err(f, `title ${title.length} > 60 chars`);
  const desc = html.match(/<meta name="description" content="([^"]*)"/)?.[1];
  if (!desc) err(f, "missing meta description");
  else if (desc.replace(/&amp;/g, "&").replace(/&quot;/g, '"').length > 155) err(f, `description > 155 chars`);
  if (!new RegExp(`<link rel="canonical" href="${reEsc(ORIGIN + BASE_PATH)}[^"]*"`).test(html)) err(f, "missing canonical");
  if (!/<meta name="referrer" content="no-referrer">/.test(html)) err(f, "missing referrer meta");
  const h1 = (html.match(/<h1[\s>]/g) || []).length;
  if (h1 !== 1) err(f, `${h1} <h1> elements`);
  const csp = html.match(/<meta http-equiv="Content-Security-Policy" content="([^"]*)">/)?.[1];
  if (!csp) err(f, "missing CSP meta (did tighten-csp run?)");
  else if (!/<head>\s*<meta charset="utf-8">\s*<meta http-equiv="Content-Security-Policy"/.test(html))
    err(f, "CSP meta is not directly after <meta charset> (SEC-66)");
  else {
    if (/unsafe-inline|unsafe-eval/.test(csp)) err(f, "CSP allows unsafe-inline/unsafe-eval");
    for (const d of ["default-src 'self'", "object-src 'none'", "base-uri 'none'", "form-action 'none'"])
      if (!csp.includes(d)) err(f, `CSP lacks ${d}`);
    const scripts = [...html.matchAll(/<script(\s[^>]*)?>([\s\S]*?)<\/script>/gi)];
    for (const [, attrs = "", body] of scripts) {
      if (/type="application\/ld\+json"/.test(attrs)) { try { JSON.parse(body); } catch { err(f, "invalid JSON-LD"); } continue; }
      if (/\ssrc="([^"]*)"/.test(attrs)) continue;
      if (!csp.includes(sha(body))) err(f, "inline script not covered by a CSP hash");
    }
    for (const [, , body] of html.matchAll(/<style(\s[^>]*)?>([\s\S]*?)<\/style>/gi))
      if (!csp.includes(sha(body))) err(f, "inline <style> not covered by a CSP hash");
  }
  if (/\sstyle="/.test(html)) err(f, 'style="" attribute (blocked by the CSP)');
  // WR-60/SEC-65: look only inside start tags (comments and script/style bodies removed), any quoting or spacing.
  const tagsOnly = html.replace(/<!--[\s\S]*?-->/g, "").replace(/<(script|style)\b([^>]*)>[\s\S]*?<\/\1>/gi, "<$1$2>");
  for (const [tag] of tagsOnly.matchAll(/<[a-z][^>]*>/gi)) {
    if (/\son[a-z]+\s*=/i.test(tag)) err(f, `inline event handler attribute: ${tag.slice(0, 80)}`);
    if (/\s(?:href|src|action|formaction|xlink:href)\s*=\s*["']?\s*javascript:/i.test(tag)) err(f, `javascript: URL: ${tag.slice(0, 80)}`);
  }
  // third-party assets: src / link href / srcset must be local
  for (const m of html.matchAll(/<(?:img|script|source|iframe|video|audio|embed)\b[^>]*\ssrc="([^"]+)"/gi))
    if (/^(https?:)?\/\//.test(m[1])) err(f, `third-party asset ${m[1]}`);
  for (const m of html.matchAll(/<link\b[^>]*>/gi)) {
    const href = m[0].match(/href="([^"]+)"/)?.[1] || "";
    if (/rel="canonical"/.test(m[0])) continue;
    if (/^(https?:)?\/\//.test(href)) err(f, `third-party <link> ${href}`);
  }
  if (/<iframe|<embed|<object/i.test(html)) err(f, "embed/iframe/object");
  if (/<form\b/i.test(html)) err(f, "form element (the site has no forms)");
  for (const m of html.matchAll(/<img\b[^>]*>/gi)) {
    for (const a of ["alt", "width", "height"]) if (!new RegExp(`\\s${a}="`).test(m[0])) err(f, `<img> without ${a}`);
  }
  // links and anchors
  for (const m of html.matchAll(/<a\b[^>]*\shref="([^"]*)"/gi)) {
    const href = m[1].replace(/&amp;/g, "&");
    // /get/* are Cloudflare redirects to release assets (tools/cloudflare_redirects.py), not pages: allowed as absolute links.
    if (href.startsWith(ORIGIN) && !href.startsWith(ORIGIN + "/get/")) err(f, `absolute link to own site ${href} (use the base path)`);
    const r = resolveLocal(f, href);
    if (!r) continue;
    const [target, frag] = r;
    if (target.startsWith("__outside_base__")) { err(f, `link outside base path ${href}`); continue; }
    if (!files.includes(target)) { err(f, `broken link ${href}`); continue; }
    if (frag && target.endsWith(".html") && !ids.get(target)?.has(frag)) err(f, `missing anchor ${href}`);
  }
  for (const m of html.matchAll(/\s(?:src|srcset)="([^"]*)"/gi)) {
    for (const part of m[1].split(",")) {
      const u = part.trim().split(/\s+/)[0];
      const r = u && resolveLocal(f, u);
      if (r && !files.includes(r[0])) err(f, `missing asset ${u}`);
    }
  }
  if (/registry\.yaml\b/.test(html.replace(/registry\.sample\.yaml/g, ""))) err(f, "mentions the private registry.yaml");
  if (!isRedirect && !/<meta name="robots" content="noindex">/.test(html)) indexable.push(f);
}

// sitemap
const sm = existsSync(join(dist, "sitemap.xml")) ? read("sitemap.xml") : "";
const locs = new Set([...sm.matchAll(/<loc>([^<]+)<\/loc>/g)].map((m) => m[1]));
for (const f of indexable) {
  const u = `${ORIGIN}${BASE_PATH}${f.replace(/index\.html$/, "")}`;
  if (!locs.has(u)) err("sitemap.xml", `missing ${u}`);
  locs.delete(u);
}
for (const u of locs) err("sitemap.xml", `lists a page that isn't indexable or doesn't exist: ${u}`);
// WR-39: <lastmod> is optional (left out on shallow clones), but when present it must be a real W3C date, not in the future.
const todayUtc = new Date().toISOString().slice(0, 10);
for (const [, d] of sm.matchAll(/<lastmod>([^<]*)<\/lastmod>/g)) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(d) || Number.isNaN(Date.parse(d))) err("sitemap.xml", `bad lastmod ${d}`);
  else if (d > todayUtc) err("sitemap.xml", `lastmod in the future: ${d}`);
}
if (/<(priority|changefreq)>/.test(sm)) err("sitemap.xml", "priority/changefreq are ignored by Google; leave them out");
if (!existsSync(join(dist, "robots.txt"))) err("robots.txt", "missing");

// --- budgets
// every script a page loads, following static imports (island chunks)
function pageScripts(f, html) {
  const js = new Set();
  for (const m of html.matchAll(/(?:component-url|renderer-url|src)="([^"]+\.js)"/g)) js.add(resolveLocal(f, m[1])[0]);
  const queue = [...js];
  while (queue.length) {
    const j = queue.pop();
    const src = readFileSync(join(dist, j), "utf8");
    for (const m of src.matchAll(/(?:from|import)\s*"(\.\/[^"]+\.js)"/g)) {
      const dep = j.slice(0, j.lastIndexOf("/") + 1) + m[1].slice(2);
      if (!js.has(dep)) { js.add(dep); queue.push(dep); }
    }
  }
  return js;
}
function pageWeight(f) {
  const html = read(f);
  const css = [...html.matchAll(/<link rel="stylesheet" href="([^"]+)"/g)].map((m) => resolveLocal(f, m[1])[0]);
  const js = pageScripts(f, html);
  // first-view images: eager <img> (no loading="lazy") and inline art is already in the HTML
  const imgs = [...html.matchAll(/<img\b[^>]*>/g)].filter((m) => !/loading="lazy"/.test(m[0]))
    .map((m) => resolveLocal(f, m[0].match(/\ssrc="([^"]+)"/)[1])[0]);
  const size = (list) => list.reduce((n, p) => n + gz(readFileSync(join(dist, p))), 0);
  return { html: gz(Buffer.from(html)), css: size(css), js: size([...js]), img: imgs.reduce((n, p) => n + statSync(join(dist, p)).size, 0) };
}
// no deployed script that no page loads (SEC-63: an unused chunk is still a same-origin script gadget)
const usedJs = new Set();
for (const f of htmlFiles) for (const j of pageScripts(f, read(f))) usedJs.add(j);
for (const f of files) if (f.endsWith(".js") && !usedJs.has(f)) err(f, "script that no page loads (remove it from the build)");
const rows = [];
for (const f of ["index.html", "download/index.html", "how-it-works/index.html", "safety/index.html", "faq/index.html",
  "families/index.html", "guides/index.html", "guides/spokeo/index.html", "i-do-not-consent/index.html", "404.html"]) {
  if (!files.includes(f)) continue;
  const w = pageWeight(f);
  const total = w.html + w.css + w.js + w.img;
  rows.push(`${f.padEnd(28)} html ${(w.html / 1024).toFixed(1).padStart(5)}  css ${(w.css / 1024).toFixed(1).padStart(5)}  js ${(w.js / 1024).toFixed(1).padStart(5)}  img ${(w.img / 1024).toFixed(1).padStart(5)}  first view ${(total / 1024).toFixed(1).padStart(6)} KiB`);
  if (f === "index.html") {
    if (total > 300 * 1024) err(f, `first-view transfer ${(total / 1024).toFixed(1)} KiB > 300 KiB`);
    if (w.js > 80 * 1024) err(f, `JS ${(w.js / 1024).toFixed(1)} KiB gzip > 80 KiB`);
  }
  if (w.css > 20 * 1024) err(f, `CSS ${(w.css / 1024).toFixed(1)} KiB gzip > 20 KiB`);
}
console.log("Page weights (KiB = 1024 bytes, gzip -9; images as stored):\n" + rows.join("\n"));
for (const e of errors) console.log("ERROR:", e);
console.log(`${htmlFiles.length} HTML files, ${indexable.length} indexable. ${errors.length ? errors.length + " problem(s)" : "OK"}`);
process.exit(errors.length ? 1 : 0);
