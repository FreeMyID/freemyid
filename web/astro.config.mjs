// Free My ID website v3. Static output for GitHub Pages under /freemyid/.
// Content comes from ../site_src (site.yaml, pages.yaml, data/*.yaml, static/) and
// ../brokers/registry.sample.yaml at build time: one source of truth with the v2 site.
import { defineConfig } from "astro/config";
import react from "@astrojs/react";
import tailwindcss from "@tailwindcss/vite";
import { fileURLToPath } from "node:url";

const BASE_URL = "https://freemyid.github.io"; // change with base when freemyid.org exists
const BASE_PATH = "/freemyid/";

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
  integrations: [react()],
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
