// Open Graph images (brand art copied to src/art/og) published at assets/og-*.png.
// site_src/static stays the v2 public folder, so these files are emitted from here. Data-driven:
// every og-*.png in src/art/og is published; pages pick one with og_image/og_alt in pages.yaml.
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import type { APIRoute } from "astro";
import { OG_DIR, ogImages } from "@/lib/site";

export function getStaticPaths() {
  return ogImages.map((og) => ({ params: { og } }));
}
export const GET: APIRoute = ({ params }) => {
  const file = resolve(OG_DIR, `${params.og}.png`);
  return new Response(readFileSync(file), { headers: { "Content-Type": "image/png" } });
};
