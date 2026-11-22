// Free My ID website v3. Static output for GitHub Pages (origin and base path from site_src/site.yaml).
// Content comes from ../site_src (site.yaml, pages.yaml, data/*.yaml, static/) and
// ../brokers/registry.sample.yaml at build time: one source of truth with the v2 site.
import { defineConfig } from "astro/config";
import tailwindcss from "@tailwindcss/vite";
import { fileURLToPath } from "node:url";
import { readFileSync } from "node:fs";

// One source of truth with the v2 build: base_url (origin + path) and base_path in site_src/site.yaml.
const SITE_YAML = readFileSync(new URL("../site_src/site.yaml", import.meta.url), "utf8");
const yamlValue = (key) => {
  const m = SITE_YAML.match(new RegExp(`^${key}:\\s*(\\S+)`, "m"));
  if (!m) throw new Error(`site_src/site.yaml: ${key} missing`);
  return m[1];
};
const BASE_URL = new URL(yamlValue("base_url")).origin;
const BASE_PATH = yamlValue("base_path");

// A/B/C test arms (docs/AB_TEST.md). FMID_ARM unset = the normal site. FMID_ARM=<arm> builds a full copy of the
// site under <base>x/<arm>/ into dist-arms/<arm> (scripts/build-arms.mjs copies it into dist/x/<arm>/). Every arm
// page keeps its canonical on the normal URL and is noindex. The arm's look comes from @direction (below).
const ARMS = ["control", "heritage", "frontier", "glory"];
const ARM = process.env.FMID_ARM || "";
if (ARM && !ARMS.includes(ARM)) throw new Error(`FMID_ARM=${ARM}: expected one of ${ARMS.join(", ")}`);
const DIRECTION = ARM && ARM !== "control" ? ARM : "none";

export default defineConfig({
  site: BASE_URL,
  base: ARM ? `${BASE_PATH.replace(/\/?$/, "/")}x/${ARM}/` : BASE_PATH,
  output: "static",
  trailingSlash: "always",
  // favicons, og.png, screenshots and the fridge card are shared with the v2 build (no copies)
  publicDir: fileURLToPath(new URL("../site_src/static", import.meta.url)),
  outDir: ARM ? `./dist-arms/${ARM}` : "./dist",
  build: {
    format: "directory",
    inlineStylesheets: "never", // style-src 'self': no inline <style>
    assets: "_assets",
  },
  compressHTML: true,
  devToolbar: { enabled: false },
  security: {
    // Astro writes a <meta http-equiv="Content-Security-Policy"> into every page and hashes
    // its own inline island bootstrap script (pages with islands only). No 'unsafe-inline'.
    csp: {
      algorithm: "SHA-256",
      directives: [
        "default-src 'self'",
        "img-src 'self'",
        "font-src 'self'",
        "connect-src 'none'",
        "object-src 'none'",
        "frame-src 'none'",
        "form-action 'none'",
        "base-uri 'none'",
      ],
    },
  },
  vite: {
    plugins: [tailwindcss()],
    // The arm's direction stylesheet (fonts, motifs, colour overrides); "none" is empty, so the normal site and the
    // control arm ship exactly the CSS they shipped before.
    resolve: { alias: { "@direction": fileURLToPath(new URL(`./src/styles/directions/${DIRECTION}.css`, import.meta.url)) } },
    define: { __FMID_ARM__: JSON.stringify(ARM), __FMID_DIRECTION__: JSON.stringify(DIRECTION) },
    build: { assetsInlineLimit: 0 }, // never inline scripts or assets as data: URIs
    server: { fs: { allow: [fileURLToPath(new URL("..", import.meta.url))] } },
  },
});
