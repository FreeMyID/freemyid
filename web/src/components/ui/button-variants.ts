// shadcn/ui Button variants (copied in, retuned to Free My ID tokens and sizes).
// Links use these classes directly (`<a class={buttonVariants(...)}>`), as shadcn recommends,
// so a button is real HTML that works with JavaScript off. button.tsx wraps the same variants
// for React islands.
import { cva, type VariantProps } from "class-variance-authority";

export const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2xs rounded-lg font-bold no-underline " +
    "transition-colors duration-200 motion-reduce:transition-none text-center " +
    "[&_svg]:size-[1.1em] [&_svg]:shrink-0 hover:no-underline",
  {
    variants: {
      variant: {
        // one filled primary per screen
        primary: "bg-brand text-brand-ink shadow-1 hover:bg-heading",
        // outline: line-strong border meets 3:1, brand text meets 4.5:1
        secondary: "border-2 border-line-strong bg-card text-brand hover:bg-brand-soft",
        ghost: "text-link underline underline-offset-[0.18em] hover:bg-brand-soft",
        onBrand: "bg-band-brand-ink text-band-brand hover:bg-bg-alt",
      },
      size: {
        sm: "min-h-tap px-s py-2xs text-body",
        md: "min-h-tap px-m py-xs text-body",
        lg: "min-h-[3.25rem] px-l py-xs text-lead",
      },
    },
    defaultVariants: { variant: "primary", size: "md" },
  },
);

export type ButtonVariantProps = VariantProps<typeof buttonVariants>;
