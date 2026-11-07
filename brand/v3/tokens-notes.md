# v3 theme: Free My ID tokens mapped to Tailwind / shadcn/ui

Source of truth stays `site_src/tokens.yaml` (the build-time contrast check). Port the **hex** values below; the HSL
columns are only a convenience for shadcn's `H S% L%` convention and are rounded (a rounded HSL can drift a hex by 1).
In Tailwind v4 prefer hex in `:root` / `.dark` and `@theme inline { --color-primary: var(--primary); ... }`.

Look: shadcn-clean (flat, 1px borders, soft shadow only on cards), warm rather than neon. Navy is the only strong
colour; red is a small accent and is also our `destructive` (used only for real errors, never alarm banners); gold is the focus ring.
Radius: `--radius: 0.75rem` (soft, friendly). Body text 20px base, per D6.

## Mapping (light | dark)

| shadcn variable | tokens.yaml | Light hex | Dark hex | Light HSL | Dark HSL |
|---|---|---|---|---|---|
| `--background` | bg | #ffffff | #0d131d | 0 0% 100% | 218 38% 8% |
| `--foreground` | text | #151b26 | #eef1f6 | 219 29% 12% | 218 31% 95% |
| `--card` | card | #ffffff | #172131 | 0 0% 100% | 217 36% 14% |
| `--card-foreground` | text | #151b26 | #eef1f6 | 219 29% 12% | 218 31% 95% |
| `--popover` / `-foreground` | card / text | #ffffff / #151b26 | #172131 / #eef1f6 | as card / text | as card / text |
| `--primary` | brand | #1b3366 | #a9c3f3 | 221 58% 25% | 219 76% 81% |
| `--primary-foreground` | brand-ink | #ffffff | #0d131d | 0 0% 100% | 218 38% 8% |
| `--secondary` | surface-strong | #e1e8f2 | #25334b | 215 40% 92% | 218 34% 22% |
| `--secondary-foreground` | heading | #14264a | #dde7fb | 220 57% 18% | 220 79% 93% |
| `--muted` | surface | #eef2f7 | #1a2434 | 213 36% 95% | 217 33% 15% |
| `--muted-foreground` | muted | #414b5c | #c0c8d5 | 218 17% 31% | 217 20% 79% |
| `--accent` (shadcn hover tint) | brand-soft | #e6edf8 | #1d2b45 | 217 56% 94% | 219 41% 19% |
| `--accent-foreground` | heading | #14264a | #dde7fb | 220 57% 18% | 220 79% 93% |
| `--destructive` | accent (flag red) | #a3202e | #f5a3ab | 354 67% 38% | 354 80% 80% |
| `--destructive-foreground` | white / bg | #ffffff | #0d131d | 0 0% 100% | 218 38% 8% |
| `--border` | line | #dbe1ea | #2a374d | 216 26% 89% | 218 29% 23% |
| `--input` | line-strong | #6b778c | #8794ab | 218 13% 48% | 218 18% 60% |
| `--ring` | focus | #f2b705 | #f2b705 | 45 96% 48% | 45 96% 48% |

Notes on the non-obvious choices:
- shadcn's `--accent` is a *hover tint*, not our red. Our red is `--destructive` (and the `--brand-red` extra below).
- `--input` uses `line-strong` so input borders meet 3:1 (WCAG 1.4.11); `--border` (decorative hairlines) stays soft.
- Focus: keep the two-ring pattern: `outline: 3px solid var(--ring)` plus an inner `box-shadow: 0 0 0 2px var(--focus-inner)`
  (#151b26 light / #eef1f6 dark). Do not use shadcn's default faint ring.

## Extra tokens to add (not in shadcn's set)

| Variable | Light | Dark | Use |
|---|---|---|---|
| `--background-alt` | #f4f6f9 | #121a26 | alternate bands |
| `--heading` | #14264a | #dde7fb | h1-h4 |
| `--link` | #17488f | #a8caff | links (7:1 on bg, alt, card, surface) |
| `--success` | #1c6639 | #8fd6a6 | ticks, "confirmed" |
| `--warning` | #7a4f00 | #f0c674 | "waiting" chip |
| `--band-brand` / `-foreground` | #1b2f5b / #fff | #162543 / #eef1f6 | the one deep navy band (final CTA) |
| `--footer` / `-foreground` | #0f1c38 / #e8edf6 | #080c14 / #dfe5ee | footer |
| `--brand-red` | #a3202e | #f5a3ab | flag bar, small accents only |

## Contrast (computed from the hex above; all pass the tokens.yaml minimums)

| Pair (light / dark) | Ratio | Min |
|---|---|---|
| foreground on background | 17.3 / 16.4 | 7 |
| muted-foreground on background | 8.8 / 11.0 | 7 |
| muted-foreground on card | 8.8 / 9.6 | 7 |
| muted-foreground on muted (surface) | 7.8 / 9.3 | 7 |
| muted-foreground on accent (brand-soft) | 7.5 / 8.4 | 7 |
| foreground on accent (brand-soft) | 14.7 / 12.5 | 7 |
| primary-foreground on primary | 12.3 / 10.4 | 7 |
| primary on background (outline button text, links-as-buttons) | 12.3 / 10.4 | 4.5 |
| destructive on background | 7.5 / 9.5 | 4.5 |
| destructive-foreground on destructive | 7.5 / 9.5 | 4.5 |
| input border on background | 4.5 / 6.1 | 3 |

Rules for new components (shadcn / Magic UI / Aceternity):
- Never put `text-muted-foreground` on anything but background, card, muted or accent (the pairs above). No `/50` opacity text.
- Any gradient, glow, spotlight, beam or particle effect must keep text on a flat token colour behind it; effects sit behind, never under text. Keep them navy/brand-soft (no neon, no purple/cyan gradients), and honour `prefers-reduced-motion`.
- Buttons: primary = `--primary`; secondary = outline with `--input` border and `--primary` text. One filled primary per screen.
- Dark mode primary is a light periwinkle (#a9c3f3) with near-black text; do not swap it for the light-mode navy.

## Illustration colours (brand/v3 SVGs)

SVGs carry their own light/dark palette via `prefers-color-scheme`, and also read these optional page variables when inlined
(set them from the theme so a manual theme toggle works too): `--fmi-ink` (heading), `--fmi-paper` (card), `--fmi-tint` (brand-soft),
`--fmi-brand` (primary), `--fmi-red` (accent), `--fmi-ok` (success), `--fmi-line` (input), `--fmi-sun` (warm). Defaults live in each file.
Illustration-only warm tones (skin, hair, lamp light) are not UI tokens; do not reuse them for UI.
