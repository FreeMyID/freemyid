// "Protect yourself" guides, built from brokers/checklists.yaml (public, CC BY-NC 4.0, maintained by
// broker-researcher). The fields and checks mirror the Checklist / ChecklistFile models in
// src/freemyid/models.py (extra keys forbidden, id pattern, verification literal, unique ids), so a
// YAML change that the app would reject also fails the site build.
// `notes` is research-internal (what our checker could open, what to re-check) and is never rendered.
import { existsSync, readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { parse } from "yaml";

function findRepo(): string {
  let d = process.cwd();
  while (!existsSync(resolve(d, "brokers/checklists.yaml"))) {
    const up = dirname(d);
    if (up === d) throw new Error("brokers/checklists.yaml not found above " + process.cwd());
    d = up;
  }
  return d;
}
const FILE = resolve(findRepo(), "brokers/checklists.yaml");
const MAX_BYTES = 512 * 1024; // same cap as src/freemyid/checklists.py

export interface Checklist {
  id: string; title: string; why: string; url: string; cost: string; time_needed: string;
  need_on_hand: string[]; steps: string[]; how_to_undo: string; source_urls: string[];
  date_checked: string; verification: "official_page" | "partial"; notes: string | null; tips: string[]; status_note: string | null;
}

const FIELDS = ["id", "title", "why", "url", "cost", "time_needed", "need_on_hand", "steps", "how_to_undo",
  "source_urls", "date_checked", "verification", "notes", "tips", "status_note"];
const REQUIRED = ["id", "title", "why", "url", "cost", "time_needed", "steps", "how_to_undo", "source_urls",
  "date_checked", "verification"];

function isoDate(v: unknown, where: string): string {
  const s = v instanceof Date ? v.toISOString().slice(0, 10) : String(v ?? "");
  if (!/^\d{4}-\d{2}-\d{2}$/.test(s)) throw new Error(`${where}: not a date: ${s}`);
  return s;
}
function httpUrl(v: unknown, where: string): string {
  const s = String(v ?? "");
  const u = new URL(s); // throws on garbage
  if (u.protocol !== "https:" && u.protocol !== "http:") throw new Error(`${where}: not an http(s) URL`);
  return s;
}
function str(v: unknown, where: string, max?: number): string {
  if (typeof v !== "string" || !v.trim()) throw new Error(`${where}: expected text`);
  if (max && v.length > max) throw new Error(`${where}: longer than ${max}`);
  return v;
}
function strList(v: unknown, where: string, min = 0): string[] {
  if (v == null && min === 0) return [];
  if (!Array.isArray(v) || v.length < min) throw new Error(`${where}: expected a list (at least ${min})`);
  return v.map((x, i) => str(x, `${where}[${i}]`));
}

function validate(raw: any): Checklist {
  const where = `checklists.yaml ${raw?.id ?? "?"}`;
  for (const k of Object.keys(raw)) if (!FIELDS.includes(k)) throw new Error(`${where}: unknown field ${k}`);
  for (const k of REQUIRED) if (raw[k] == null) throw new Error(`${where}: missing ${k}`);
  if (!/^[a-z0-9_]{2,40}$/.test(raw.id)) throw new Error(`${where}: bad id`);
  if (raw.verification !== "official_page" && raw.verification !== "partial") throw new Error(`${where}: bad verification`);
  return {
    id: raw.id, title: str(raw.title, `${where}.title`, 120), why: str(raw.why, `${where}.why`),
    url: httpUrl(raw.url, `${where}.url`), cost: str(raw.cost, `${where}.cost`),
    time_needed: str(raw.time_needed, `${where}.time_needed`),
    need_on_hand: strList(raw.need_on_hand, `${where}.need_on_hand`), steps: strList(raw.steps, `${where}.steps`, 1),
    how_to_undo: str(raw.how_to_undo, `${where}.how_to_undo`),
    source_urls: strList(raw.source_urls, `${where}.source_urls`, 1).map((u, i) => httpUrl(u, `${where}.source_urls[${i}]`)),
    date_checked: isoDate(raw.date_checked, `${where}.date_checked`), verification: raw.verification,
    notes: raw.notes ?? null, tips: strList(raw.tips ?? [], `${where}.tips`), status_note: raw.status_note ?? null,
  };
}

function loadFile() {
  const text = readFileSync(FILE, "utf8");
  if (Buffer.byteLength(text) > MAX_BYTES) throw new Error("checklists.yaml is too large");
  const doc = parse(text);
  for (const k of Object.keys(doc)) if (!["version", "updated", "checklists"].includes(k)) throw new Error(`checklists.yaml: unknown key ${k}`);
  const items = (doc.checklists as any[]).map(validate);
  const ids = items.map((c) => c.id);
  if (new Set(ids).size !== ids.length) throw new Error("checklists.yaml: duplicate checklist id");
  return { version: String(doc.version), updated: isoDate(doc.updated, "checklists.yaml updated"), items };
}

// ------------------------------------------------------------------ groups on /protect/ (orchestrator brief)
export const PROTECT_GROUPS: { key: string; title: string; ids: string[] }[] = [
  { key: "credit", title: "Freeze your credit", ids: ["freeze_equifax", "freeze_experian", "freeze_transunion",
    "freeze_innovis", "freeze_chexsystems", "freeze_nctue", "freeze_lexisnexis"] },
  { key: "junk", title: "Stop junk mail and pre-approved offers", ids: ["optoutprescreen", "dmachoice", "national_do_not_call"] },
  { key: "government", title: "Lock down government accounts", ids: ["irs_ip_pin", "ssa_my_social_security", "usps_informed_delivery"] },
  { key: "search", title: "Search results", ids: ["google_results_about_you", "bing_content_removal"] },
  { key: "california", title: "California residents", ids: ["ca_drop"] },
];

// Entries held back from the public site until the orchestrator rules. freeze_lexisnexis: its official
// host is in the private registry, so the leak scan (tools/site_check.py private_host_hashes) flags it.
// The page is not built and the hub doesn't link it; nothing is obfuscated to get past the scan.
const HOLD = new Set<string>([]);   // freeze_lexisnexis released 2026-11-07 (PUBLIC_OK_HOSTS)

// Entries whose phone numbers are unverified and must never be shown (orchestrator brief: ChexSystems).
const HIDE_PHONE_STEPS = new Set(["freeze_chexsystems"]);
const PHONE_RE = /(?:\b1-)?\(?\b\d{3}\)?[ .-]\d{3}-\d{4}\b|\b1-\d{3}-\d-[A-Z]{3}-[A-Z]{3}\b/;
export const hasPhone = (s: string) => PHONE_RE.test(s);

export interface ProtectPage extends Checklist {
  out: string; group: string; groupTitle: string; host: string; free: boolean;
  shownSteps: { text: string; phone: boolean }[];
}

const file = loadFile();
const byId = new Map(file.items.map((c) => [c.id, c]));
for (const g of PROTECT_GROUPS) for (const id of g.ids) if (!byId.has(id)) throw new Error(`/protect/ group ${g.key}: no checklist ${id}`);
const grouped = new Set(PROTECT_GROUPS.flatMap((g) => g.ids));
for (const id of byId.keys()) if (!grouped.has(id)) throw new Error(`checklist ${id} is not in a /protect/ group (web/src/lib/protect.ts)`);

export const protectPages: ProtectPage[] = PROTECT_GROUPS.flatMap((g) => g.ids.filter((id) => !HOLD.has(id)).map((id) => {
  const c = byId.get(id)!;
  return {
    ...c, out: `protect/${c.id}/`, group: g.key, groupTitle: g.title, host: new URL(c.url).hostname.replace(/^www\./, ""),
    free: /^free\b/i.test(c.cost),
    shownSteps: c.steps.filter((s) => !(HIDE_PHONE_STEPS.has(c.id) && hasPhone(s)))
      .map((s) => ({ text: s, phone: c.verification === "partial" && hasPhone(s) })),
  };
}));
export const protectMeta = { version: file.version, updated: file.updated };

const MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
/** 2026-11-07 -> "November 7, 2026" (US reading order). */
export function longDate(iso: string): string {
  const [y, m, d] = iso.split("-").map(Number);
  return `${MONTHS[m - 1]} ${d}, ${y}`;
}
