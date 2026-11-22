// A/B/C test build (docs/AB_TEST.md). Builds the four arms of the home-page test and copies each into
// dist/x/<arm>/, next to the normal site that `pnpm build` already wrote to dist/.
//   node scripts/build-arms.mjs            (run after `pnpm build`; pages.yml does both)
// Each arm is a full copy of the site with base /x/<arm>/, every page noindex with its canonical on the normal URL
// (astro.config.mjs FMID_ARM). Files that only make sense once per origin are removed from the arm copies.
// The edge worker (worker/ab-test) serves "/" from one of these arms at random and counts views and downloads.
import { cpSync, existsSync, readdirSync, rmSync } from "node:fs";
import { execFileSync } from "node:child_process";
import { join } from "node:path";

export const ARMS = ["control", "heritage", "frontier", "glory"];
const web = new URL("..", import.meta.url).pathname;
const astro = join(web, "node_modules/.bin/astro");
if (!existsSync(join(web, "dist/index.html"))) throw new Error("dist/ is empty: run `pnpm build` first");

// Once per origin: search-engine files, the 404 page, site verification files, old-URL redirect stubs.
// (.well-known stays: the developers page links to security.txt under its own base.)
const PER_ORIGIN = ["sitemap.xml", "robots.txt", "404.html", ".nojekyll", "CNAME",
  "download.html", "faq.html", "how-it-works.html", "privacy.html", "privacy"];
const VERIFY = /^([0-9a-f]{32}\.txt|BingSiteAuth\.xml|google[0-9a-f]+\.html)$/;

for (const arm of ARMS) {
  const out = join(web, "dist-arms", arm);
  rmSync(out, { recursive: true, force: true });
  execFileSync(astro, ["build"], { cwd: web, stdio: ["ignore", "ignore", "inherit"],
    env: { ...process.env, FMID_ARM: arm, ASTRO_TELEMETRY_DISABLED: "1" } });
  execFileSync(process.execPath, [join(web, "scripts/tighten-csp.mjs"), out], { cwd: web, stdio: "ignore" });
  for (const n of readdirSync(out)) if (PER_ORIGIN.includes(n) || VERIFY.test(n)) rmSync(join(out, n), { recursive: true, force: true });
  const dest = join(web, "dist", "x", arm);
  rmSync(dest, { recursive: true, force: true });
  cpSync(out, dest, { recursive: true });
  console.log(`build-arms: ${arm} -> dist/x/${arm}/`);
}
