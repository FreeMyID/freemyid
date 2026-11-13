// Build-time data for /brokers/ ("Sites we cover"), read from brokers/coverage.public.yaml.
// That file is the PUBLIC coverage list written by tools/export_coverage.py: per site a display name,
// the main site hostname, a category, how the site is handled, a status, the month it was last
// checked, the state data broker registries that list it and a family name. Nothing else. Sites with
// no working removal route are not in the file at all; only their number is (counts.not_available). The full registry (brokers/registry.yaml) is private and
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
export type Status = "verified" | "not_verified";
export interface CoverageSite {
  name: string; site: string; category: Category; route: Route; status: Status; checked?: string;
  registered?: string;   // "CA", "VT" or "CA,VT": on that state's official data broker registry
  family?: string;       // the covered_by parent: its removal also covers this site
}
export interface CoverageCounts { listed: number; verified: number; not_verified: number; not_available: number }

// Page groups, in page order, with plain-language labels. A group is a category, except that
// data_broker rows split in two (orchestrator ruling 2026-11-13): rows on a state's official data
// broker registry are "Registered data brokers", with the sentence below under the heading; the rest
// keep "Marketing data companies", the label the guides index uses.
// Adding a group: add its `.cov:has(#cov-c-<id>:checked)` rule in pages/brokers/index.astro too
// (tests/test_web_coverage_page.py clicks every group filter).
export type GroupId = Category | "registered";
export const GROUPS: { id: GroupId; label: string; note?: string }[] = [
  { id: "people_search", label: "People-search sites" },
  { id: "background_check", label: "Background-check sites" },
  { id: "phone_lookup", label: "Phone-lookup sites" },
  { id: "family_tree", label: "Family-tree sites" },
  { id: "risk_data", label: "Identity and risk data companies" },
  { id: "registered", label: "Registered data brokers",
    note: "These companies are on a state's official data broker registry. Being listed does not mean they did anything wrong; it means the law lets you ask them to delete your data." },
  { id: "data_broker", label: "Marketing data companies" },
  { id: "other", label: "Official tools and other opt-outs" },
];
export function groupOf(s: CoverageSite): GroupId {
  return s.category === "data_broker" && s.registered ? "registered" : s.category;
}
const STATES: Record<string, string> = { CA: "California", VT: "Vermont" };
/** "CA,VT" -> "California and Vermont". */
export function registeredIn(codes: string): string {
  const names = codes.split(",").map((c) => STATES[c]);
  return names.length > 1 ? `${names.slice(0, -1).join(", ")} and ${names[names.length - 1]}` : names[0];
}
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
const CATEGORY_IDS = ["people_search", "background_check", "phone_lookup", "family_tree", "data_broker", "risk_data", "other"];
const STATUSES = ["verified", "not_verified"];
const FIELDS = ["name", "site", "category", "route", "status", "checked", "registered", "family"];
const REQUIRED = ["name", "site", "category", "route", "status"];
const COUNT_KEYS = ["listed", "verified", "not_verified", "not_available"];
const REGISTERED = /^(CA|VT)(,(CA|VT))*$/;
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
  if (doc.format !== 2) fail(`format ${String(doc.format)} is not supported (re-export with tools/export_coverage.py)`);
  const updated = String(doc.updated ?? "");
  if (!MONTH.test(updated)) fail("updated is not a YYYY-MM month");
  if (!Array.isArray(doc.sites) || doc.sites.length === 0) fail("no sites");
  const sites = (doc.sites as unknown[]).map((raw, i): CoverageSite => {
    const where = `sites[${i}]`;
    const r = sameKeys(raw, FIELDS, where);
    for (const k of REQUIRED) if (typeof r[k] !== "string" || !r[k]) fail(`${where}: ${k} missing`);
    for (const k of ["checked", "registered", "family"]) if (k in r && (typeof r[k] !== "string" || !r[k])) fail(`${where}: ${k} is empty`);
    const s = r as unknown as CoverageSite;
    if (!HOST.test(s.site)) fail(`${where}: site is not a bare hostname`);
    if (!CATEGORY_IDS.includes(s.category)) fail(`${where}: unknown category`);
    if (!ROUTE_IDS.includes(s.route)) fail(`${where}: unknown route`);
    if (!STATUSES.includes(s.status)) fail(`${where}: unknown status (sites that are not available must not be listed)`);
    if (s.registered !== undefined && !REGISTERED.test(s.registered)) fail(`${where}: registered is not a list of state codes`);
    if (s.checked !== undefined && !MONTH.test(s.checked)) fail(`${where}: checked is not a YYYY-MM month`);
    for (const text of [s.name, ...(s.family ? [s.family] : [])]) {
      if (NOT_A_NAME.test(text) || text.length > 80) fail(`${where}: a name looks like contact data or a link`);
      if (text.length < 3 || /^formerly/i.test(text) || text.includes("_")) fail(`${where}: a name is too short, starts with "formerly" or is an id`);
    }
    return s;
  });
  // The headline numbers must be the rows on the page: recount and compare.
  const n = (st: Status) => sites.filter((s) => s.status === st).length;
  const counts = sameKeys(doc.counts, COUNT_KEYS, "counts") as unknown as CoverageCounts;
  // not_available sites are not in the file, so that one number cannot be recounted: it must be a whole number.
  if (!Number.isInteger(counts.not_available) || counts.not_available < 0) fail("counts.not_available is not a count");
  const real: CoverageCounts = { listed: sites.length, verified: n("verified"), not_verified: n("not_verified"),
    not_available: counts.not_available };
  for (const k of COUNT_KEYS as (keyof CoverageCounts)[]) {
    if (counts[k] !== real[k]) fail(`counts.${k} is ${String(counts[k])} but the rows give ${real[k]}`);
  }
  return { updated, counts: real, sites };
}

const loaded = loadCoverage();
export const coverage = loaded;

export interface CoverageGroup { id: GroupId; label: string; note?: string; sites: CoverageSite[]; verified: number }
/** Groups in page order, each A to Z (the file's own order); empty groups are left out. */
export const coverageGroups: CoverageGroup[] = GROUPS.map((g) => {
  const sites = loaded.sites.filter((s) => groupOf(s) === g.id);
  return { ...g, sites, verified: sites.filter((s) => s.status === "verified").length };
}).filter((g) => g.sites.length > 0);

/** Sites per route; routes with no site are left out. */
export const routeCounts = ROUTES.map((r) => ({ ...r, count: loaded.sites.filter((s) => s.route === r.id).length }))
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
