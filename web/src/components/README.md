# Component library (ui / magicui / aceternity)

Static Astro + CSS only: no JavaScript, no React islands, no new dependencies. Styles live in
`web/src/styles/components.css` (plus Tailwind utilities); tokens come from `site_src/tokens.yaml`
(generated `tokens.css`) and `styles/tokens-ext.css`. All motion runs only with
`prefers-reduced-motion: no-preference`; decorative layers are `aria-hidden` and drop out in forced
colours and print. Every component works in light and dark, at 320px and at 200% zoom.
Props are additive: old props keep their names and defaults.

Owner: Maya Chen. Shared components (Header, Section, PageHead, CtaDownload, ...) belong to the lead.

## ui/ (shadcn-style)

| Component | Props | Usage |
|---|---|---|
| `buttonVariants()` (`button-variants.ts`) | `variant`: primary (default, one per view) / secondary / ghost / onBrand / outline / soft / link / onBrandOutline; `size`: sm / md (default) / lg / xl / icon; `effect`: none / lift / shimmer; `full` | `<a class={buttonVariants({ variant: "secondary", size: "lg" })} href=...>` |
| `Button` | `href?` (a link, else `<button>`), `variant`, `size`, `effect`, `full`, `type`, `class`, any attribute | `<Button href={url("guides/")} variant="outline">See the guides</Button>` |
| `Card` | `as` (div/li/article/section/aside), `id`, `variant`: default / elevated / outline / soft / glow, `interactive`, `padding`: none/sm/md/lg, `class` | `<Card as="li" interactive>...</Card>` |
| `CardHeader`, `CardContent`, `CardFooter` | `class` | `<CardFooter><Button size="sm" variant="soft" href=...>Read more</Button></CardFooter>` |
| `CardTitle` | `as` (h2/h3 default/h4/p), `href` (whole card becomes the link), `id`, `rel`, `class` | `<CardTitle href={url("guides/spokeo/")}>Spokeo</CardTitle>` |
| `CardDescription` | `class` | `<CardDescription>Sends the request for you.</CardDescription>` |
| `Badge` | `variant`: default / ok / warn / brand / outline / solid / ok-soft / warn-soft / accent (tiny "New" chip only), `dot`, `class` | `<Badge variant="ok-soft" dot>Removed</Badge>` |
| `Alert` | `variant`: info (default) / note / ok / warn (calm, never red), `title?`, `icon?`, `id?`, `class` | `<Alert variant="warn" title="Heads-up">Some sites take 45 days.</Alert>` |
| `Separator` | `orientation`, `variant`: line / fade / flag, `decorative` (false = real `<hr>`), `label?`, `class` | `<Separator label="or" />` |
| `Tabs` | `id` (unique), `label` (legend), `tabs: {id,label}[]` (max 6), `selected?`, `headingLevel`, `class`; one named slot per tab id | `<Tabs id="os" label="Your Windows" tabs={[...]}><Fragment slot="w11">...</Fragment></Tabs>` |
| `Disclosure` | `summary`, `open?`, `name?` (same name = one open at a time), `id?`, `class` | `<Disclosure summary="Is it free?">Yes.</Disclosure>` |
| `BentoGrid` | `cols`: 2 / 3 (default), `label?`, `class` | `<BentoGrid>{BentoItem...}</BentoGrid>` |
| `BentoItem` | `title`, `eyebrow?`, `icon?`, `href?`, `span` 1/2/3, `rows` 1/2, `tone`: card / soft / brand, `glow` (default true), `headingLevel`, `class`; slot `visual` | `<BentoItem title="Runs on your PC" icon="computer" span={2}>Nothing is sent to us.</BentoItem>` |
| `FeatureGrid` | `items: {icon?, title, body, href?}[]`, `cols` 2/3/4, `headingLevel`, `label?`, `class` | `<FeatureGrid items={features} cols={3} />` |
| `StatGroup` / `Stat` | group: `label?`, `class`; stat: `value`, `label`, `hint?` (real, sourced numbers only) | `<StatGroup><Stat value="$0" label="Price" /></StatGroup>` |

CSS helpers: `.text-hero` (home h1 size), `.eyebrow` (small caps label with a red tick), `.icon-tile`.

## aceternity/

| Component | Props | Usage |
|---|---|---|
| `Spotlight` | `as` (section/div/header), `tone`: full / quiet, `pattern`: grid / dots / none, `edge`, `class`, any attribute | `<Spotlight aria-labelledby="hero-title" class="py-2xl">...</Spotlight>` |
| `GlowCard` | Card props (`as`, `id`, `interactive` default true, `padding`, `class`) | `<GlowCard as="li"><CardTitle>...</CardTitle></GlowCard>` |
| `Timeline` | `beam`: css / none, `variant`: default / cards, `surface`: bg / bg-alt / card (ring colour), `class` | `<Timeline surface="bg-alt">...</Timeline>` |
| `TimelineItem` | `n`, `title?`, `id?`, `meta?`, `icon?`, `status`: done / current / next, `headingLevel` | `<TimelineItem n={1} title="Install" status="done">...</TimelineItem>` |

## magicui/

| Component | Props | Usage |
|---|---|---|
| `Marquee` | `items`, `label`, `id` (pause switch), `speed`: slow / slower, `reverse`, `class` | `<Marquee id="guide-marquee-pause" label="Sites covered" items={names} />` |
| `BorderBeam` | `tone`: gold / brand, `class` | `<BorderBeam><a class={buttonVariants({ size: "lg" })} ...>Download</a></BorderBeam>` |
| `AnimatedGradientText` | `as` (span/p/strong), `pill`, `icon?`, `class` (bg, bg-alt, card, spot surfaces only) | `<AnimatedGradientText pill icon="shield">Free. Open source.</AnimatedGradientText>` |
| `ShimmerButton` | `href?`, `variant`: primary / onBrand, `size`: md / lg / xl, `full`, `class` | `<ShimmerButton href={site.download_url}>Download</ShimmerButton>` |
| `DotPattern` | `fade`, `class` (parent needs `relative isolate`) | `<div class="relative isolate"><DotPattern />...</div>` |

## Measured contrast (WCAG ratio, light / dark)

All 60 `tokens.yaml` pairs pass at build time (`gen-tokens.mjs`). Composites the token check can't see,
worked out from the token hex values:

| Case | Light | Dark |
|---|---|---|
| Spotlight worst case (85% spot + 5% gold + 30% grid line): text / muted / heading / link | 13.78 / 7.03 / 11.92 / 7.10 | 10.77 / 7.24 / 9.81 / 7.29 |
| Same, brand / accent (gradient text stops) | 9.79 / 5.98 | 6.84 / 6.22 |
| ShimmerButton label under the 22% white veil: primary / primary hover / onBrand | 6.28 / 7.37 / 13.09 | 11.96 / 15.69 / 13.82 |
| onBrandOutline label on its 10% hover veil | 9.66 | 10.17 |
| New status tints: ok on ok-soft / warn on warn-soft / accent on accent-soft | 6.16 / 6.35 / 6.54 | 8.96 / 9.39 / 8.24 |
| muted on spot / ok-soft / warn-soft | 7.14 / 7.78 / 7.85 | 7.45 / 9.05 / 8.98 |
