"use client";

import { LayoutGroup, MotionConfig, motion, useReducedMotion, type Transition, type Variants } from "motion/react";
import { createContext, useContext, type ReactNode } from "react";

/**
 * The one place that decides HOW things move. Rules:
 *  - Anyone who asked their system for less motion gets none: every primitive then renders its final state at once (`useCalm`).
 *  - Motion is short (about 0.2 to 0.5 s) and only helps: it shows where something came from or went to; it never delays a task.
 *  - Springs for things you touch (press, glide); ease-out for things that arrive (fade up).
 */
export { AnimatePresence, LayoutGroup, motion } from "motion/react";

export const SPRING: Transition = { type: "spring", stiffness: 520, damping: 34, mass: 0.7 };      // press, glide
export const SOFT: Transition = { type: "spring", stiffness: 260, damping: 30 };                    // bars, rings
export const EASE_OUT = [0.22, 1, 0.36, 1] as const;                                                // things that arrive

/** True when the visitor asked for reduced motion (operating-system setting). */
export function useCalm(): boolean {
  return useReducedMotion() ?? false;
}

/** Wrap the app once: also lets Motion itself honour the setting for anything we forget. */
export function MotionRoot({ children }: { children: ReactNode }) {
  return <MotionConfig reducedMotion="user"><LayoutGroup>{children}</LayoutGroup></MotionConfig>;
}

// ---- a page: its cards arrive one after another -------------------------------------------------------------------------------
const PageContext = createContext(false);
export const usePageStagger = () => useContext(PageContext);

export const CONTAINER: Variants = { hidden: {}, show: { transition: { staggerChildren: 0.045, delayChildren: 0.02 } } };
export const RISE: Variants = { hidden: { opacity: 0, y: 14 }, show: { opacity: 1, y: 0, transition: { duration: 0.42, ease: EASE_OUT } } };

/** The content of one page. It is keyed by the address, so every navigation plays it again; the cards inside rise in turn. */
export function Page({ children }: { children: ReactNode }) {
  const calm = useCalm();
  return (
    <PageContext.Provider value>
      <motion.div variants={CONTAINER} initial={calm ? false : "hidden"} animate="show">{children}</motion.div>
    </PageContext.Provider>
  );
}

// ---- things you press -------------------------------------------------------------------------------------------------------
/** Props for any motion element that should answer a hover and a press: it lifts a hair, then dips under the finger. */
export function usePress(strength: "button" | "icon" | "none" = "button") {
  const calm = useCalm();
  if (calm || strength === "none") return {};
  return { whileHover: { y: -1.5 }, whileTap: { scale: strength === "icon" ? 0.9 : 0.96, y: 0 }, transition: SPRING } as const;
}
