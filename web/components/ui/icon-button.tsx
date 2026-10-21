"use client";

import { Button as BaseButton } from "@base-ui/react/button";
import type { ComponentProps } from "react";
import { cn } from "@/lib/cn";

/** A round icon button. `label` is REQUIRED: an icon alone has no accessible name. */
export function IconButton({ label, className, children, ...props }: ComponentProps<typeof BaseButton> & { label: string }) {
  return (
    <BaseButton
      aria-label={label}
      title={label}
      className={cn(
        "grid size-11 shrink-0 sm:size-[2.125rem] place-items-center rounded-full bg-card text-ink outline-none",
        "shadow-[0_0_0_1px_var(--line),0_1px_2px_rgb(0_0_0/.08)] transition hover:not-data-disabled:bg-inset",
        "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand [&>svg]:size-[1.05rem]",
        className,
      )}
      {...props}
    >
      {children}
    </BaseButton>
  );
}
