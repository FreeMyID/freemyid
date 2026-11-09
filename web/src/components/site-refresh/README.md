# Site refresh components

These plain Astro components and `site-refresh.css` form a temporary, route-scoped staging layer. Import the stylesheet on each refreshed page and wrap that page's refreshed content in `.site-refresh`. Do not edit the shared token or global stylesheet files.

After WO-204 passes, in-house will fold the pieces it keeps into the main design system and remove this namespace. The site should have one design system long term.

## Components

- `RefreshHero.astro`: page hero with heading, short lead, text actions, and an optional media slot. Use a real product image for product proof.
- `RefreshSection.astro`: centered section container with optional eyebrow, heading, and lead.
- `RefreshCard.astro`: semantic article card with a heading and body slot.
- `RefreshSteps.astro`: ordered list wrapper. Provide `<li>` steps with visible text; number bubbles are optional decoration, not the only label.
- `RefreshCallout.astro`: calm note or information callout.
- `RefreshButton.astro`: text link styled as a filled or secondary button. Never use without visible text.

## Example

```astro
---
import "@/styles/site-refresh.css";
import RefreshHero from "@/components/site-refresh/RefreshHero.astro";
---

<main class="site-refresh">
  <div class="site-refresh__wrap">
    <RefreshHero title="A clear page heading" lead="A short, factual explanation.">
      <a slot="actions" class="site-refresh__button" href="/how-it-works/">See how it works</a>
    </RefreshHero>
  </div>
</main>
```

Keep body copy at least 20px, all color values on existing `--fmi-*` tokens, and tap targets at least 44px. Check both themes and the route-specific copy against D8.
