// v3 Open Graph images (brand/v3/og, copied to src/art/og) published at assets/og-*.png.
// site_src/static stays the v2 public folder, so v3-only files are emitted from here.
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import type { APIRoute } from "astro";

const NAMES = ["og-home", "og-download"];
export function getStaticPaths() {
  return NAMES.map((og) => ({ params: { og } }));
}
export const GET: APIRoute = ({ params }) => {
  const file = resolve(process.cwd(), "src/art/og", `${params.og}.png`);
  return new Response(readFileSync(file), { headers: { "Content-Type": "image/png" } });
};
