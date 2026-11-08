// Per-page Open Graph images (WO-170..174, 179). Pure helpers, no imports, so tests can run this file
// directly with Node's type stripping (tests/test_web_og_images.py).
//
// A pages.yaml entry may name `og_image` (a file name in web/src/art/og/, with or without ".png")
// and `og_alt`. Every PNG in that folder is published at assets/<name>.png by
// src/pages/assets/[og].png.ts. A named image that isn't in the folder yet falls back to og-home with
// the home alt text (never the page's own alt, which would describe a picture that isn't there).

export const OG_DEFAULT = "og-home";
export const OG_DEFAULT_ALT = "Free My ID: take your name off the websites that sell it.";
const NAME = /^og-[a-z0-9]+(?:-[a-z0-9]+)*$/;

/** File names (no extension) of the OG images that may be published, from a folder listing. */
export function ogNames(files: string[]): string[] {
  return files.filter((f) => f.endsWith(".png")).map((f) => f.slice(0, -4)).filter((n) => NAME.test(n)).sort();
}

export interface OgChoice { ogImage: string; ogAlt: string; fallback: boolean }

/** The og:image path and alt for a page entry, given the images that exist. */
export function resolveOg(entry: { id?: string; og_image?: string | null; og_alt?: string | null },
                          available: string[]): OgChoice {
  const def = { ogImage: `assets/${OG_DEFAULT}.png`, ogAlt: OG_DEFAULT_ALT };
  if (!entry.og_image) return { ...def, fallback: false };
  const name = entry.og_image.replace(/\.png$/, "");
  if (!NAME.test(name)) throw new Error(`pages.yaml ${entry.id}: og_image "${entry.og_image}" must look like og-some-name`);
  if (!available.includes(name)) return { ...def, fallback: true };
  const alt = (entry.og_alt ?? "").trim();
  if (!alt) throw new Error(`pages.yaml ${entry.id}: og_image ${name} needs og_alt`);
  return { ogImage: `assets/${name}.png`, ogAlt: alt, fallback: false };
}
