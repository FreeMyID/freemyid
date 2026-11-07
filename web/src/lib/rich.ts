// Rich text from site_src data (FAQ answers are small HTML snippets with jinja url() calls).
// Instead of injecting HTML, we expand the two jinja forms the data uses, then parse the HTML into
// a tree with an allowlist of tags and attributes. RichText.astro renders the tree as elements,
// so Astro escapes every text node. Anything outside the allowlist fails the build.
import { release, url } from "./site";

export type RNode = string | { tag: string; attrs: Record<string, string>; children: RNode[] };

const ALLOWED: Record<string, string[]> = {
  p: [], a: ["href"], strong: [], em: [], code: [], br: [], ul: [], ol: [], li: [], kbd: [],
};
const VOID = new Set(["br"]);

/** Expand {{ url('x') }} and {% if release.version %}A{% else %}B{% endif %} (the only forms used). */
export function expand(src: string): string {
  let s = src.replace(/<!--[\s\S]*?-->/g, "");
  s = s.replace(/\{%\s*if release\.version\s*%\}([\s\S]*?)(?:\{%\s*else\s*%\}([\s\S]*?))?\{%\s*endif\s*%\}/g,
    (_, a, b) => (release.version ? a : b ?? ""));
  s = s.replace(/\{\{\s*url\('([^']*)'\)\s*\}\}/g, (_, t) => url(t));
  s = s.replace(/\{\{\s*release\.version\s*\}\}/g, String(release.version ?? ""));
  if (/\{[{%]/.test(s)) throw new Error(`unsupported template syntax in data: ${s.slice(0, 120)}`);
  return s;
}

function decode(s: string): string {
  return s.replace(/&quot;/g, '"').replace(/&#39;/g, "'").replace(/&lt;/g, "<").replace(/&gt;/g, ">")
    .replace(/&nbsp;/g, " ").replace(/&amp;/g, "&");
}

export function parse(html: string): RNode[] {
  const root: RNode[] = [];
  const stack: { tag: string; children: RNode[] }[] = [{ tag: "#root", children: root }];
  const re = /<\/?([a-z0-9]+)((?:\s+[a-z-]+="[^"]*")*)\s*\/?>|([^<]+)/gi;
  let m: RegExpExecArray | null;
  let consumed = 0;
  while ((m = re.exec(html))) {
    consumed += m[0].length;
    const top = stack[stack.length - 1];
    if (m[3] !== undefined) { top.children.push(decode(m[3])); continue; }
    const tag = m[1].toLowerCase();
    if (!(tag in ALLOWED)) throw new Error(`tag <${tag}> not allowed in rich text`);
    if (m[0].startsWith("</")) {
      if (top.tag !== tag) throw new Error(`mismatched </${tag}> in rich text`);
      stack.pop();
      continue;
    }
    const attrs: Record<string, string> = {};
    for (const a of m[2].matchAll(/([a-z-]+)="([^"]*)"/gi)) {
      if (!ALLOWED[tag].includes(a[1])) throw new Error(`attribute ${a[1]} not allowed on <${tag}>`);
      attrs[a[1]] = decode(a[2]);
    }
    if (attrs.href && !/^(https:\/\/|\/|#|mailto:)/.test(attrs.href)) throw new Error(`bad href ${attrs.href}`);
    const node = { tag, attrs, children: [] as RNode[] };
    top.children.push(node);
    if (!VOID.has(tag) && !m[0].endsWith("/>")) stack.push(node);
  }
  if (consumed !== html.length || stack.length !== 1) throw new Error(`could not parse rich text: ${html.slice(0, 120)}`);
  return root;
}

export function rich(src: string): RNode[] {
  return parse(expand(src).trim());
}

/** Plain text (for JSON-LD), after template expansion. */
export function renderPlain(src: string): string {
  return expand(src);
}
