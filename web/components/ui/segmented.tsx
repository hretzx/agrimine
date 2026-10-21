"use client";

import { Toggle } from "@base-ui/react/toggle";
import { ToggleGroup } from "@base-ui/react/toggle-group";
import { useId } from "react";
import { motion, SPRING } from "@/components/motion";
import { cn } from "@/lib/cn";

/** A pill switch with one selected option (language, theme). Built on Base UI's ToggleGroup: arrow keys and aria come with it. */
export function Segmented<T extends string>({
  value,
  onChange,
  options,
  label,
  className,
}: {
  value: T;
  onChange: (next: T) => void;
  options: { value: T; label: string }[];
  label: string;
  className?: string;
}) {
  const id = useId();       // one gliding pill per control
  return (
    <ToggleGroup
      aria-label={label}
      value={[value]}
      onValueChange={(next) => next[0] && onChange(next[0] as T)} // a segmented control always keeps one option selected
      className={cn("inline-flex rounded-full bg-seg-bg p-[0.2rem] shadow-[inset_0_0_0_1px_var(--line)]", className)}
    >
      {options.map((o) => (
        <Toggle
          key={o.value}
          value={o.value}
          className={cn(
            "relative isolate min-w-11 rounded-full px-3.5 py-3 text-[0.8rem] sm:min-w-0 sm:py-1.5 font-medium text-ink-3 outline-none transition-colors",
            "focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-brand",
            "data-pressed:text-seg-on-ink",
          )}
        >
          {o.value === value && <motion.span layoutId={`seg-${id}`} transition={SPRING} aria-hidden="true" className="absolute inset-0 -z-10 rounded-full bg-seg-on shadow-[0_2px_6px_rgb(0_0_0/.3)]" />}
          {o.label}
        </Toggle>
      ))}
    </ToggleGroup>
  );
}
