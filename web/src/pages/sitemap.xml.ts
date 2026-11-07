// sitemap.xml: every indexable page (pages.yaml entries without noindex, plus the broker guides).
// Deterministic (sorted, no dates). The v2 styleguide is not part of v3.
import type { APIRoute } from "astro";
import { guides, pagesList, site } from "@/lib/site";

export const GET: APIRoute = () => {
  const urls = [
    ...pagesList.filter((p) => !p.noindex).map((p) => site.base_url + p.out),
    ...guides.map((g) => site.base_url + g.out),
  ].sort();
  const body = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' +
    urls.map((u) => `  <url><loc>${u.replace(/&/g, "&amp;")}</loc></url>\n`).join("") + "</urlset>\n";
  return new Response(body, { headers: { "Content-Type": "application/xml" } });
};
