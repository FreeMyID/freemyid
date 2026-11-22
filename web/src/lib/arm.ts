// Which A/B/C test arm this build is (docs/AB_TEST.md). Set by astro.config.mjs from FMID_ARM at build time.
//   ARM       ""            the normal site (search engines, links, every page outside the test)
//             "control"     the current design, built under /x/control/
//             "heritage" | "frontier" | "glory"   a design direction, built under /x/<arm>/
//   DIRECTION "none" for the normal site and control, otherwise the direction name.
declare const __FMID_ARM__: string;
declare const __FMID_DIRECTION__: string;
export type Direction = "none" | "heritage" | "frontier" | "glory";
export const ARM: string = __FMID_ARM__;
export const DIRECTION = __FMID_DIRECTION__ as Direction;
/** True inside any arm copy (noindex, counted downloads). */
export const IN_TEST = ARM !== "";
