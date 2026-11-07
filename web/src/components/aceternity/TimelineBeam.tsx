// Aceternity UI "Timeline" beam (copied in and trimmed): the coloured line beside a numbered list
// fills in as you scroll through it. Island (client:visible); purely decorative (aria-hidden).
// The list itself, its numbers and the grey rail are static HTML (Timeline.astro), so nothing is
// lost with JavaScript off. Under prefers-reduced-motion the beam is shown full, without movement.
import { useEffect, useRef, useState } from "react";
import { m, LazyMotion, domMin, useReducedMotion, useScroll, useTransform } from "motion/react";

export default function TimelineBeam() {
  const ref = useRef<HTMLDivElement>(null);
  const reduce = useReducedMotion();
  const { scrollYProgress } = useScroll({ target: ref, offset: ["start 70%", "end 60%"] });
  const scaleY = useTransform(scrollYProgress, [0, 1], [0, 1]);
  // The server render has no style attribute (the CSP blocks style=""); motion sets the transform
  // through the DOM (element.style) after hydration, which the CSP allows.
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);
  const cls = "h-full w-full origin-top rounded-full bg-gradient-to-b from-brand via-brand to-accent";
  return (
    <LazyMotion features={domMin} strict>
      <div ref={ref} aria-hidden="true" className="absolute inset-y-0 start-[calc(1.25rem-2px)] w-1 overflow-hidden rounded-full">
        {mounted && !reduce ? <m.div className={cls} style={{ scaleY }} /> : <div className={mounted ? cls : "hidden"} />}
      </div>
    </LazyMotion>
  );
}
