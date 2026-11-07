// shadcn/ui helper: merge class names, letting later Tailwind classes win.
// tailwind-merge is told about our type-scale and spacing names, so text-body (a font size)
// and text-brand-ink (a color) are not treated as the same utility.
import { clsx, type ClassValue } from "clsx";
import { extendTailwindMerge } from "tailwind-merge";

const twMerge = extendTailwindMerge({
  extend: {
    theme: {
      text: ["small", "body", "lead", "h3", "h2", "h1", "display"],
      spacing: ["3xs", "2xs", "xs", "s", "m", "l", "xl", "2xl", "3xl", "tap", "gutter"],
    },
  },
});

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
