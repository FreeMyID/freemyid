import type { APIRoute } from "astro";
import { site } from "@/lib/site";

export const GET: APIRoute = () =>
  new Response(`User-agent: *\nAllow: /\n\nSitemap: ${site.base_url}sitemap.xml\n`, {
    headers: { "Content-Type": "text/plain" },
  });
