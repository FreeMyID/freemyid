// Build-time data for the v3 site. Reads the SAME files as tools/build_site.py, so there is one
// source of truth: site_src/site.yaml, pages.yaml, data/*.yaml and the PUBLIC sample registry.
// Never point this at brokers/registry.yaml (the full registry is private).
import { existsSync, readFileSync, realpathSync } from "node:fs";
import { basename, dirname, resolve } from "node:path";
import { parse } from "yaml";

// The repo root is the nearest folder above the working dir (web/) that holds site_src/.
// (import.meta.url points into the build cache once Astro bundles this module.)
function findRepo(): string {
  let d = process.cwd();
  while (!existsSync(resolve(d, "site_src/site.yaml"))) {
    const up = dirname(d);
    if (up === d) throw new Error("site_src/ not found above " + process.cwd());
    d = up;
  }
  return d;
}
const REPO = findRepo();
const SRC = resolve(REPO, "site_src");

function load<T = any>(path: string): T {
  return parse(readFileSync(path, "utf8")) as T;
}

/** Same guard as tools/build_site.py validate_registry_path. */
function samplePath(): string {
  const p = process.env.FMID_SAMPLE_REGISTRY || resolve(REPO, "brokers/registry.sample.yaml");
  const real = realpathSync(p);
  let full = "";
  try { full = realpathSync(resolve(REPO, "brokers/registry.yaml")); } catch { /* not present: fine */ }
  if (real === full) throw new Error(`refusing ${p}: resolves to brokers/registry.yaml (private)`);
  if (!basename(real).endsWith(".sample.yaml")) throw new Error(`refusing ${p}: not a .sample.yaml file`);
  if (!real.startsWith(REPO + "/")) throw new Error(`refusing ${p}: outside the repo`);
  return real;
}

export interface SiteCfg {
  name: string; tagline: string; base_url: string; base_path: string;
  repo_url: string; releases_url: string; download_url: string; redirects: Record<string, string>;
}
export interface PageCfg {
  id: string; out: string; label: string; title: string; description: string;
  nav?: string; jsonld?: string[]; noindex?: boolean;
}
export interface Release { version: string | null; date?: string | Date; size_mb?: number; sha256?: string }
export interface Faq { id: string; q: string; a: string; home?: boolean }

export const site = load<SiteCfg>(resolve(SRC, "site.yaml"));
export const pagesList = load<PageCfg[]>(resolve(SRC, "pages.yaml"));
export const pages: Record<string, PageCfg> = Object.fromEntries(pagesList.map((p) => [p.id, p]));
export const release = (load<Release>(resolve(SRC, "data/release.yaml")) || { version: null }) as Release;
export const faq = load<Faq[]>(resolve(SRC, "data/faq.yaml"));
export const icons = load<Record<string, string>>(resolve(SRC, "data/icons.yaml"));
const intros = load<Record<string, string>>(resolve(SRC, "data/guide_intros.yaml")) || {};

export const releaseDate = release.date
  ? (release.date instanceof Date ? release.date.toISOString().slice(0, 10) : String(release.date))
  : "";

/** Site-relative target ("" = home, "faq/#x", "og.png") -> path under the base ("/freemyid/faq/#x"). */
export function url(target: string): string {
  return import.meta.env.BASE_URL.replace(/\/?$/, "/") + target.replace(/^\//, "");
}
export function canonical(out: string): string {
  return site.base_url + out;
}

// ------------------------------------------------------------------ broker guides (port of load_guides)
const PEOPLE = new Set(["people_search", "background_check", "family_tree"]);
export const GROUPS: [string, string, Set<string>][] = [
  ["people", "People-search sites", PEOPLE],
  ["data", "Marketing data companies", new Set(["data_broker"])],
  ["other", "Official tools and other opt-outs", new Set(["other"])],
];
const FIELD_LABELS: Record<string, string> = {
  listing_url: "the web address of your listing on {name} (you find it by searching for yourself)",
  email: "an email address for removals (a separate one just for this is best)",
  full_name: "your name, as it shows on the listing",
  first_name: "your first name, as it shows on the listing",
  last_name: "your last name, as it shows on the listing",
  street_address: "the street address that shows on your listing",
  city: "your city",
  state: "your state",
  zip: "your ZIP code",
  dob: "your date of birth",
  phone: "a phone number the site can call or text with a code",
};

export function slugify(text: string): string {
  return text.toLowerCase().replace(/['’]/g, "").replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "");
}
function displayName(name: string): string {
  return name.split(" (")[0].trim().replace(/,? Inc\.?$/, "").trim();
}

export interface Guide {
  id: string; slug: string; name: string; full_name: string; category: string; group: string;
  method: string | null; home_url: string | null; opt_out_url: string | null; opt_out_host: string | null;
  email: string | null; has_email: boolean; covered_by_id: string | null; steps: string[];
  steps_mention_app: boolean; needs_email_verification: boolean; has_captcha: boolean;
  needs_id_upload: boolean; days: number | null; verified: boolean; last_verified: string;
  ca_registered: boolean; source_urls: string[]; priority: number; intro: string | null;
  required: string[]; covered_by: Guide | null; covers: Guide[]; out: string;
}

function lastVerified(v: unknown): string {
  if (!v) return "";
  return v instanceof Date ? v.toISOString().slice(0, 10) : String(v);
}

function loadGuides() {
  const reg = load<any>(samplePath());
  const raw = (reg.brokers as any[]).filter((b) => b.enabled !== false);
  const byId = new Map<string, Guide>();
  for (const b of raw) {
    const name = displayName(b.name);
    const steps: string[] = [...(b.steps || [])];
    const cat = b.category || "other";
    const g: Guide = {
      id: b.id, slug: slugify(name), name, full_name: b.name, category: cat,
      group: GROUPS.find(([, , cats]) => cats.has(cat))![0],
      method: b.method ?? null, home_url: b.url ?? null, opt_out_url: b.opt_out_url ?? null,
      opt_out_host: b.opt_out_url ? String(b.opt_out_url).split("/")[2] : null,
      email: b.method === "email" ? b.opt_out_email ?? null : null,
      has_email: Boolean(b.opt_out_email), covered_by_id: b.covered_by ?? null, steps,
      steps_mention_app: steps.some((s) => s.includes("Free My ID")),
      needs_email_verification: Boolean(b.needs_email_verification),
      has_captcha: Boolean(b.has_captcha) || steps.some((s) => s.toLowerCase().includes("captcha")),
      needs_id_upload: Boolean(b.needs_id_upload), days: b.typical_processing_days ?? null,
      verified: b.verification_status === "verified" && Boolean(b.last_verified),
      last_verified: lastVerified(b.last_verified), ca_registered: Boolean(b.ca_registered),
      source_urls: (b.source_urls || []).map(String), priority: Number(b.priority || 0),
      intro: intros[b.id] ?? null,
      required: (b.required_fields || []).filter((f: string) => f in FIELD_LABELS)
        .map((f: string) => FIELD_LABELS[f].replace("{name}", name)),
      covered_by: null, covers: [], out: "",
    };
    byId.set(g.id, g);
  }
  const slugs = [...byId.values()].map((g) => g.slug);
  const dupes = slugs.filter((s, i) => slugs.indexOf(s) !== i);
  if (dupes.length) throw new Error(`duplicate guide slugs: ${dupes}`);
  const lower = (s: string) => s.toLowerCase();
  for (const g of byId.values()) {
    g.covered_by = g.covered_by_id ? byId.get(g.covered_by_id) ?? null : null;
    g.covers = [...byId.values()].filter((o) => o.covered_by_id === g.id)
      .sort((a, b) => (lower(a.name) < lower(b.name) ? -1 : 1));
    g.out = `guides/${g.slug}/`;
  }
  const guides = [...byId.values()].sort((a, b) =>
    b.priority - a.priority || (lower(a.name) < lower(b.name) ? -1 : lower(a.name) > lower(b.name) ? 1 : 0));
  return { guides, meta: { updated: lastVerified(reg.updated), version: String(reg.version ?? "") } };
}

const loaded = loadGuides();
export const guides = loaded.guides;
export const guidesMeta = loaded.meta;

export function guideDescription(g: Guide): string {
  const what = g.group === "people" ? "your listing" : "your information";
  const d = `How to remove ${what} from ${g.name}, step by step, for free. Or let Free My ID do it for you.`;
  return d.length <= 155 ? d : d.slice(0, 152).replace(/ \S*$/, "") + "...";
}
export function guideTitle(g: Guide): string {
  return `Remove yourself from ${g.name}: free steps`.slice(0, 60);
}

// ------------------------------------------------------------------ JSON-LD (port of jsonld_for)
export type Crumb = [label: string, out: string];

export function stripTags(s: string): string {
  return s.replace(/<!--[\s\S]*?-->/g, "").replace(/<[^>]+>/g, "")
    .replace(/&amp;/g, "&").replace(/&lt;/g, "<").replace(/&gt;/g, ">").replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'").replace(/\s+/g, " ").trim();
}

export function jsonld(kind: string, crumbs: Crumb[], renderText: (html: string) => string): object {
  const base = site.base_url;
  switch (kind) {
    case "organization":
      return { "@context": "https://schema.org", "@type": "Organization", name: site.name, url: base,
        sameAs: [site.repo_url],
        description: "Free, open-source software that asks people-search sites to remove your listing." };
    case "website":
      return { "@context": "https://schema.org", "@type": "WebSite", name: site.name, url: base, inLanguage: "en-US" };
    case "software": {
      const d: Record<string, unknown> = { "@context": "https://schema.org", "@type": "SoftwareApplication",
        name: site.name, operatingSystem: "Windows 10, Windows 11", applicationCategory: "UtilitiesApplication",
        description: site.tagline + " Free, open source, runs on your own computer.", url: base,
        isAccessibleForFree: true, license: "https://www.gnu.org/licenses/agpl-3.0.html",
        offers: { "@type": "Offer", price: "0", priceCurrency: "USD" } };
      if (release.version) { d.downloadUrl = site.download_url; d.softwareVersion = String(release.version); }
      return d;
    }
    case "faq":
      return { "@context": "https://schema.org", "@type": "FAQPage", mainEntity: faq.map((q) => ({
        "@type": "Question", name: stripTags(q.q),
        acceptedAnswer: { "@type": "Answer", text: stripTags(renderText(q.a)) } })) };
    case "breadcrumbs":
      return { "@context": "https://schema.org", "@type": "BreadcrumbList", itemListElement: crumbs.map(
        ([label, out], i) => ({ "@type": "ListItem", position: i + 1, name: label, item: base + out })) };
  }
  throw new Error(`unknown jsonld kind ${kind}`);
}

/** Props for Base.astro from the pages.yaml entry `id` (one manifest for both builds). */
export function pageProps(id: string) {
  const p = pages[id];
  if (!p) throw new Error(`page ${id} not in site_src/pages.yaml`);
  const crumbs: Crumb[] = [["Home", ""]];
  if (id !== "home") crumbs.push([p.label, p.out]);
  return { title: p.title, description: p.description, out: p.out, nav: p.nav ?? null,
    noindex: Boolean(p.noindex), jsonldKinds: p.jsonld ?? [], crumbs };
}

/** JSON for a <script type="application/ld+json"> block; "<" is escaped so data can't close the tag. */
export function ldJson(obj: object): string {
  return JSON.stringify(obj).replace(/</g, "\\u003c");
}
