// sitemap.xml: every indexable page (pages.yaml entries without noindex, plus the broker guides).
// Deterministic (sorted). The v2 styleguide is not part of v3.
// WR-39 <lastmod>: never the build date. Guides: the broker's last_verified when verified (shown on the page),
// otherwise the last commit of the guide data. Other pages: the last commit of their source file (plus the data
// file that fills them). Left out when unknown (e.g. a shallow clone), which Google accepts.
import type { APIRoute } from "astro";
import { gitDate, guides, pagesList, site } from "@/lib/site";

const W = "web/src/pages/";
// Data files that change what a page says, beside its own .astro file.
const PAGE_DATA: Record<string, string[]> = {
  home: ["site_src/data/faq.yaml", "site_src/data/release.yaml"],
  faq: ["site_src/data/faq.yaml"],
  download: ["site_src/data/release.yaml"],
  guides: ["brokers/registry.sample.yaml", "site_src/data/guide_intros.yaml"],
};
const pageSource = (out: string) => `${W}${out}index.astro`;
const guideData = ["brokers/registry.sample.yaml", "site_src/data/guide_intros.yaml"];

export const GET: APIRoute = () => {
  const today = new Date().toISOString().slice(0, 10);
  const entries: [string, string][] = [
    ...pagesList.filter((p) => !p.noindex).map((p): [string, string] =>
      [site.base_url + p.out, gitDate([pageSource(p.out), ...(PAGE_DATA[p.id] ?? [])])]),
    ...guides.map((g): [string, string] =>
      [site.base_url + g.out, g.verified ? g.last_verified : gitDate(guideData)]),
  ].sort(([a], [b]) => (a < b ? -1 : a > b ? 1 : 0));
  const xml = (s: string) => s.replace(/&/g, "&amp;");
  const body = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' +
    entries.map(([u, d]) => `  <url><loc>${xml(u)}</loc>${d && d <= today ? `<lastmod>${d}</lastmod>` : ""}</url>\n`).join("") +
    "</urlset>\n";
  return new Response(body, { headers: { "Content-Type": "application/xml" } });
};
