// Build-time data for /brokers/ ("Sites we cover"), read from brokers/coverage.public.yaml.
// That file is the PUBLIC coverage list written by tools/export_coverage.py: per site a display name,
// the main site hostname, a category, how the site is handled, a status, the month it was last
// checked and a family name. Nothing else. The full registry (brokers/registry.yaml) is private and
// is never read here: the path guard below refuses it, and the strict reader refuses any file with a
// field that is not on the allowlist, so a wrong or over-full export fails the build.
import { existsSync, readFileSync, realpathSync } from "node:fs";
import { basename, dirname, resolve } from "node:path";
import { parse } from "yaml";

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

/** Same guard as samplePath() in site.ts. FMID_COVERAGE lets a test build use another public list. */
function coveragePath(): string {
  const p = process.env.FMID_COVERAGE || resolve(REPO, "brokers/coverage.public.yaml");
  const real = realpathSync(p);
  let full = "";
  try { full = realpathSync(resolve(REPO, "brokers/registry.yaml")); } catch { /* not present: fine */ }
  if (real === full) throw new Error(`refusing ${p}: resolves to brokers/registry.yaml (private)`);
  if (!basename(real).endsWith(".public.yaml")) throw new Error(`refusing ${p}: not a .public.yaml file`);
  if (!real.startsWith(REPO + "/")) throw new Error(`refusing ${p}: outside the repo`);
  return real;
}

export type Category = "people_search" | "background_check" | "phone_lookup" | "family_tree" | "data_broker" | "risk_data" | "other";
export type Route = "automatic" | "email" | "assisted" | "by_hand";
export type Status = "verified" | "not_verified" | "not_available";
export interface CoverageSite {
  name: string; site: string; category: Category; route: Route; status: Status; checked?: string; family?: string;
}
export interface CoverageCounts { total: number; listed: number; verified: number; not_verified: number; not_available: number }

// Page order and plain-language labels. "Marketing data companies" is the label the guides index already uses.
export const CATEGORIES: [Category, string][] = [
  ["people_search", "People-search sites"],
  ["background_check", "Background-check sites"],
  ["phone_lookup", "Phone-lookup sites"],
  ["family_tree", "Family-tree sites"],
  ["risk_data", "Identity and risk data companies"],
  ["data_broker", "Marketing data companies"],
  ["other", "Official tools and other opt-outs"],
];
// How Free My ID handles a site (src/freemyid/engine/tiers.py; wording from /how-it-works/ "Three ways").
// `anchor` is the matching card on /how-it-works/.
// `short` is the label on a list row.
export const ROUTES: { id: Route; label: string; short: string; what: string; anchor?: string }[] = [
  { id: "email", label: "By email", short: "By email", anchor: "email",
    what: "Free My ID writes the removal letter for you to approve and sends it by email." },
  { id: "assisted", label: "Step by step with you", short: "Step by step", anchor: "do-it-with-me",
    what: "Free My ID opens the site's own removal form in your browser and guides you through it." },
  { id: "automatic", label: "Form filled in for you", short: "Filled in for you", anchor: "fill-it-in",
    what: "Free My ID fills in the site's removal form in a window you can watch." },
  { id: "by_hand", label: "By hand", short: "By hand",
    what: "The site only takes a request from inside your own account, by phone or by letter. Free My ID shows you the steps, and you do them." },
];
const ROUTE_IDS = ROUTES.map((r) => r.id) as string[];
const CATEGORY_IDS = CATEGORIES.map(([id]) => id) as string[];
const STATUSES = ["verified", "not_verified", "not_available"];
const FIELDS = ["name", "site", "category", "route", "status", "checked", "family"];
const REQUIRED = ["name", "site", "category", "route", "status"];
const COUNT_KEYS = ["total", "listed", "verified", "not_verified", "not_available"];
const HOST = /^[a-z0-9-]+(\.[a-z0-9-]+)+$/;
const MONTH = /^\d{4}-(0[1-9]|1[0-2])$/;
const NOT_A_NAME = /@|:\/\/|\bwww\.|[\x00-\x1f\x7f]/i;

function fail(msg: string): never { throw new Error(`brokers/coverage.public.yaml: ${msg}`); }
function sameKeys(obj: unknown, want: string[], where: string): Record<string, unknown> {
  if (obj === null || typeof obj !== "object" || Array.isArray(obj)) fail(`${where}: expected a mapping`);
  const rec = obj as Record<string, unknown>;
  const extra = Object.keys(rec).filter((k) => !want.includes(k));
  if (extra.length) fail(`${where}: field not on the public allowlist: ${extra.join(", ")}`);
  return rec;
}

function loadCoverage() {
  const doc = sameKeys(parse(readFileSync(coveragePath(), "utf8")), ["format", "updated", "counts", "sites"], "file");
  if (doc.format !== 1) fail(`format ${String(doc.format)} is not supported`);
  const updated = String(doc.updated ?? "");
  if (!MONTH.test(updated)) fail("updated is not a YYYY-MM month");
  if (!Array.isArray(doc.sites) || doc.sites.length === 0) fail("no sites");
  const sites = (doc.sites as unknown[]).map((raw, i): CoverageSite => {
    const where = `sites[${i}]`;
    const r = sameKeys(raw, FIELDS, where);
    for (const k of REQUIRED) if (typeof r[k] !== "string" || !r[k]) fail(`${where}: ${k} missing`);
    for (const k of ["checked", "family"]) if (k in r && (typeof r[k] !== "string" || !r[k])) fail(`${where}: ${k} is empty`);
    const s = r as unknown as CoverageSite;
    if (!HOST.test(s.site)) fail(`${where}: site is not a bare hostname`);
    if (!CATEGORY_IDS.includes(s.category)) fail(`${where}: unknown category`);
    if (!ROUTE_IDS.includes(s.route)) fail(`${where}: unknown route`);
    if (!STATUSES.includes(s.status)) fail(`${where}: unknown status`);
    if (s.checked !== undefined && !MONTH.test(s.checked)) fail(`${where}: checked is not a YYYY-MM month`);
    for (const text of [s.name, s.family ?? ""]) {
      if (NOT_A_NAME.test(text) || text.length > 80) fail(`${where}: a name looks like contact data or a link`);
    }
    return s;
  });
  // The headline numbers must be the rows on the page: recount and compare.
  const n = (st: Status) => sites.filter((s) => s.status === st).length;
  const real: CoverageCounts = { total: sites.length, listed: n("verified") + n("not_verified"),
    verified: n("verified"), not_verified: n("not_verified"), not_available: n("not_available") };
  const counts = sameKeys(doc.counts, COUNT_KEYS, "counts") as unknown as CoverageCounts;
  for (const k of COUNT_KEYS as (keyof CoverageCounts)[]) {
    if (counts[k] !== real[k]) fail(`counts.${k} is ${String(counts[k])} but the rows give ${real[k]}`);
  }
  return { updated, counts: real, sites };
}

const loaded = loadCoverage();
export const coverage = loaded;

export interface CoverageGroup { id: Category; label: string; sites: CoverageSite[]; listed: number; verified: number }
/** Categories in page order, each A to Z (the file's own order); empty categories are left out. */
export const coverageGroups: CoverageGroup[] = CATEGORIES.map(([id, label]) => {
  const sites = loaded.sites.filter((s) => s.category === id);
  return { id, label, sites, listed: sites.filter((s) => s.status !== "not_available").length,
    verified: sites.filter((s) => s.status === "verified").length };
}).filter((g) => g.sites.length > 0);

/** Sites per route among the listed (available) sites; routes with no site are left out. */
export const routeCounts = ROUTES.map((r) => ({ ...r,
  count: loaded.sites.filter((s) => s.route === r.id && s.status !== "not_available").length }))
  .filter((r) => r.count > 0);

const MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September",
  "October", "November", "December"];
/** "2026-11" -> "November 2026" (or "Nov 2026" when short). */
export function monthLabel(ym: string, short = false): string {
  const name = MONTHS[Number(ym.slice(5, 7)) - 1];
  return `${short ? name.slice(0, 3) : name} ${ym.slice(0, 4)}`;
}
/** Thousands separator for counts ("1,204"). */
export function num(n: number): string {
  return String(n).replace(/\B(?=(\d{3})+(?!\d))/g, ",");
}
