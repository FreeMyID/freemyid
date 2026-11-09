// shadcn/ui Button variants (copied in, retuned to Free My ID tokens and sizes).
// Links use these classes directly (`<a class={buttonVariants(...)}>`), as shadcn recommends,
// so a button is real HTML that works with JavaScript off. Button.astro / ShimmerButton.astro wrap
// the same variants. Backward compatible: variants primary/secondary/ghost/onBrand and sizes sm/md/lg
// keep their names and defaults; everything else is additive.
// Every variant keeps `no-underline` and `inline-flex` (Section brand-band rule CA-2 and the
// forced-colors border rule CA-6 in global.css key on them).
import { cva, type VariantProps } from "class-variance-authority";

export const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2xs rounded-lg font-bold no-underline " +
    "transition-colors duration-200 motion-reduce:transition-none text-center leading-snug " +
    "[&_svg]:size-[1.1em] [&_svg]:shrink-0 hover:no-underline",
  {
    variants: {
      variant: {
        // one filled primary per screen
        primary: "bg-brand text-brand-ink shadow-1 hover:bg-heading",
        // outline: line-strong border meets 3:1, brand text meets 4.5:1
        secondary: "border-2 border-line-strong bg-card text-brand hover:bg-brand-soft",
        ghost: "!px-xs text-link underline underline-offset-[0.18em] hover:bg-brand-soft",
        onBrand: "bg-band-brand-ink text-band-brand hover:bg-band-brand-ink/90",
        // --- revamp additions
        // shadcn "outline": quieter than secondary (1px border, heading text)
        outline: "border border-line-strong bg-transparent text-heading hover:bg-surface",
        // tinted, for a second action next to primary inside cards
        soft: "bg-brand-soft text-heading hover:bg-surface-strong",
        // looks like a link but keeps the 48px target
        link: "!px-0 text-link underline underline-offset-[0.18em] decoration-[0.08em] hover:decoration-[0.14em]",
        // second action inside a brand band (ink text >= 7:1 on the band, hover veil is 10%)
        onBrandOutline: "border-2 border-band-brand-ink bg-transparent text-band-brand-ink hover:bg-band-brand-ink/10",
      },
      size: {
        sm: "min-h-tap px-s py-2xs text-body",
        md: "min-h-tap px-m py-xs text-body",
        lg: "min-h-[3.25rem] px-l py-xs text-lead",
        xl: "min-h-[3.75rem] px-xl py-s text-lead rounded-xl",
        icon: "size-tap p-0",
      },
      // decoration only; all motion is off under prefers-reduced-motion (components.css)
      effect: {
        none: "",
        lift: "btn-lift",
        shimmer: "btn-shimmer btn-lift",
      },
      full: {
        true: "w-full",
        false: "",
      },
    },
    defaultVariants: { variant: "primary", size: "md", effect: "none", full: false },
  },
);

export type ButtonVariantProps = VariantProps<typeof buttonVariants>;
export type ButtonVariant = NonNullable<ButtonVariantProps["variant"]>;
export type ButtonSize = NonNullable<ButtonVariantProps["size"]>;
