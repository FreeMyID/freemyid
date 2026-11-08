// Post-build: Astro's CSP meta lists the hashes of every inline script it *might* use. Rewrite each
// page's policy so it allows only what that page actually contains:
//   script-src 'none'                      on pages with no scripts at all (most pages)
//   script-src 'self' 'sha256-...'         on pages with islands (Astro's inline island bootstrap)
//   style-src  'self' ['sha256-...']       hashes only for inline <style> elements present
// JSON-LD blocks are data, not scripts, and need no hash. Deterministic.
import { createHash } from "node:crypto";
import { readdirSync, readFileSync, statSync, writeFileSync } from "node:fs";
import { join } from "node:path";

const dist = process.argv[2] || "dist";
const sha = (s) => `'sha256-${createHash("sha256").update(s, "utf8").digest("base64")}'`;

function* htmlFiles(dir) {
  for (const n of readdirSync(dir)) {
    const p = join(dir, n);
    if (statSync(p).isDirectory()) yield* htmlFiles(p);
    else if (n.endsWith(".html")) yield p;
  }
}

let changed = 0;
for (const f of htmlFiles(dist)) {
  let html = readFileSync(f, "utf8");
  const m = html.match(/<meta http-equiv="content-security-policy" content="([^"]*)">/i);
  if (!m) continue;
  const scripts = [...html.matchAll(/<script(\s[^>]*)?>([\s\S]*?)<\/script>/gi)];
  const inline = scripts.filter(([, attrs = ""]) => !/\ssrc=/.test(attrs) && !/type="application\/ld\+json"/.test(attrs))
    .map(([, , body]) => sha(body));
  const external = scripts.some(([, attrs = ""]) => /\ssrc=/.test(attrs) && !/type="application\/ld\+json"/.test(attrs));
  const styles = [...html.matchAll(/<style(\s[^>]*)?>([\s\S]*?)<\/style>/gi)].map(([, , body]) => sha(body));
  const scriptSrc = inline.length || external ? ["'self'", ...new Set(inline)].join(" ") : "'none'";
  const styleSrc = ["'self'", ...new Set(styles)].join(" ");
  const policy = m[1]
    .split(";").map((d) => d.trim()).filter(Boolean)
    .filter((d) => !/^(script-src|style-src)\b/.test(d))
    .concat([`script-src ${scriptSrc}`, `style-src ${styleSrc}`])
    .join("; ");
  // SEC-66: the policy goes directly after <meta charset>, before any <link>, JSON-LD or other <meta>.
  const meta = `<meta http-equiv="Content-Security-Policy" content="${policy}">`;
  const charset = '<meta charset="utf-8">';
  if (!html.includes(charset)) throw new Error(`${f}: no <meta charset="utf-8"> to anchor the CSP after`);
  html = html.replace(m[0], "").replace(charset, charset + meta);
  writeFileSync(f, html);
  changed++;
}
console.log(`tighten-csp: ${changed} pages`);
