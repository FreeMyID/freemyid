// Old URLs -> new clean URLs (site_src/site.yaml `redirects`, e.g. privacy.html and privacy/ -> safety/).
// Same redirect page as v2 redirect.html: meta refresh + a plain link, noindex, canonical, strict CSP
// (no scripts at all), so it works with JavaScript off.
import type { APIRoute } from "astro";
import { pages, pagesList, site, url } from "@/lib/site";

const CSP = "default-src 'self'; script-src 'none'; style-src 'self'; img-src 'self'; font-src 'self'; " +
  "connect-src 'none'; object-src 'none'; frame-src 'none'; form-action 'none'; base-uri 'none'";

const esc = (s: string) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");

export function getStaticPaths() {
  return Object.entries(site.redirects).map(([old, id]) => ({ params: { old }, props: { id } }));
}

export const GET: APIRoute = ({ props }) => {
  const target = pages[props.id as string] ?? pagesList.find((p) => p.out === `${props.id}/`);
  if (!target) throw new Error(`redirect target ${props.id} not in pages.yaml`);
  const href = url(target.out);
  const html = `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Moved: ${esc(target.label)}</title>
<meta name="description" content="This page moved to ${esc(site.base_url + target.out)}">
<meta http-equiv="Content-Security-Policy" content="${CSP}">
<meta name="referrer" content="no-referrer">
<meta name="robots" content="noindex">
<link rel="canonical" href="${esc(site.base_url + target.out)}">
<meta http-equiv="refresh" content="0; url=${esc(href)}">
</head>
<body>
<main id="main">
<h1>This page has moved</h1>
<p>It's now at <a href="${esc(href)}">${esc(target.label)}</a>.</p>
</main>
</body>
</html>
`;
  return new Response(html, { headers: { "Content-Type": "text/html; charset=utf-8" } });
};
