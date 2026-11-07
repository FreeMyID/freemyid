# web v3 handoff (branch `site-v3`, never pushed)

Status: IN PROGRESS. Done: scaffold + theme (84c2262 era), layout/header/footer/CTA, home page.
Next: download, how-it-works, safety, faq, families, guides + per-broker guides, i-do-not-consent, 404,
redirects, sitemap/robots; then checks (scripts/check-site.mjs, tighten-csp), shots, pages-v3.yml.draft.

Build: `cd web && pnpm install --frozen-lockfile && pnpm build` (output web/dist). Preview: serve a folder
containing a `freemyid -> web/dist` symlink with `python -m http.server`, open /freemyid/.
