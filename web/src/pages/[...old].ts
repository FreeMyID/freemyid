// Old URLs -> new clean URLs (site_src/site.yaml `redirects`, e.g. privacy.html and privacy/ -> safety/).
// Same redirect page as v2 redirect.html: meta refresh + a plain link, noindex, canonical, strict CSP
// (no scripts at all), so it works with JavaScript off.
// A/B/C test arms (docs/AB_TEST.md) also get get/windows/: the arm's Download button points there so the edge
// worker can count the download for that arm. Without the worker this page simply forwards to the real download.
import type { APIRoute } from "astro";
import { pages, pagesList, site, url } from "@/lib/site";
import { IN_TEST } from "@/lib/arm";

const CSP = "default-src 'self'; script-src 'none'; style-src 'self'; img-src 'self'; font-src 'self'; " +
  "connect-src 'none'; object-src 'none'; frame-src 'none'; form-action 'none'; base-uri 'none'";

const esc = (s: string) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");

interface Stub { href: string; label: string; canonical: string; title: string; h1: string; lead: string }

function pageStub(id: string): Stub {
  const target = pages[id] ?? pagesList.find((p) => p.out === `${id}/`);
  if (!target) throw new Error(`redirect target ${id} not in pages.yaml`);
  return { href: url(target.out), label: target.label, canonical: site.base_url + target.out,
    title: `Moved: ${target.label}`, h1: "This page has moved", lead: "It's now at" };
}

export function getStaticPaths() {
  const paths = Object.entries(site.redirects).map(([old, id]) => ({ params: { old }, props: { stub: pageStub(id) } }));
  if (IN_TEST) {
    const dl = pages.download;
    paths.push({ params: { old: "get/windows/index.html" }, props: { stub: {
      href: site.download_url, label: "Download Free My ID for Windows", canonical: site.base_url + (dl ? dl.out : ""),
      title: "Downloading Free My ID", h1: "Your download is starting", lead: "If it doesn't start, use this link:" } } });
  }
  return paths;
}

export const GET: APIRoute = ({ props }) => {
  const s = props.stub as Stub;
  const html = `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>${esc(s.title)}</title>
<meta name="description" content="This page moved to ${esc(s.canonical)}">
<meta http-equiv="Content-Security-Policy" content="${CSP}">
<meta name="referrer" content="no-referrer">
<meta name="robots" content="noindex">
<link rel="canonical" href="${esc(s.canonical)}">
<meta http-equiv="refresh" content="0; url=${esc(s.href)}">
</head>
<body>
<main id="main">
<h1>${esc(s.h1)}</h1>
<p>${esc(s.lead)} <a href="${esc(s.href)}">${esc(s.label)}</a>.</p>
</main>
</body>
</html>
`;
  return new Response(html, { headers: { "Content-Type": "text/html; charset=utf-8" } });
};
