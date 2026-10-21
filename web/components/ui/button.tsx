"use client";

import { Button as BaseButton } from "@base-ui/react/button";
import Link from "next/link";
import type { ComponentProps } from "react";
import { cn } from "@/lib/cn";

type Variant = "primary" | "dark" | "ghost" | "outline";

const VARIANTS: Record<Variant, string> = {
  primary:
    "bg-brand text-on-brand shadow-[inset_0_1px_0_rgb(255_255_255/.25),0_8px_18px_-8px_color-mix(in_srgb,var(--brand)_70%,transparent)] hover:not-data-disabled:brightness-110",
  dark: "bg-ink text-card shadow-[inset_0_1px_0_rgb(255_255_255/.18),0_8px_18px_-8px_rgb(0_0_0/.6)] hover:not-data-disabled:opacity-90",
  outline: "bg-card text-ink shadow-[0_0_0_1px_var(--line),0_1px_2px_rgb(0_0_0/.06)] hover:not-data-disabled:bg-inset",
  ghost: "bg-transparent text-ink-2 hover:not-data-disabled:bg-inset",
};

const BASE =
  "inline-flex select-none items-center justify-center gap-2 whitespace-nowrap rounded-full px-4 py-2.5 text-[0.84rem] font-semibold " +
  "outline-none transition focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand " +
  "data-disabled:cursor-not-allowed data-disabled:opacity-50";

export type ButtonProps = ComponentProps<typeof BaseButton> & { variant?: Variant };

/** A pill button on Base UI's Button (keyboard, focus and disabled behaviour come from Base UI). */
export function Button({ variant = "primary", className, ...props }: ButtonProps) {
  return <BaseButton className={cn(BASE, VARIANTS[variant], className)} {...props} />;
}

/** A link that looks like a Button: for moving to another page (a real <a>, so it works with middle-click and without JavaScript). */
export function ButtonLink({ variant = "primary", className, ...props }: ComponentProps<typeof Link> & { variant?: Variant }) {
  return <Link className={cn(BASE, VARIANTS[variant], className)} {...props} />;
}
