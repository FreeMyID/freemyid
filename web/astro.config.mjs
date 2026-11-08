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

export default defineConfig({
  site: BASE_URL,
  base: BASE_PATH,
  output: "static",
  trailingSlash: "always",
  // favicons, og.png, screenshots and the fridge card are shared with the v2 build (no copies)
  publicDir: fileURLToPath(new URL("../site_src/static", import.meta.url)),
  outDir: "./dist",
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
    build: { assetsInlineLimit: 0 }, // never inline scripts or assets as data: URIs
    server: { fs: { allow: [fileURLToPath(new URL("..", import.meta.url))] } },
  },
});
