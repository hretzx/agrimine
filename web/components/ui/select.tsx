"use client";

import { Select as BaseSelect } from "@base-ui/react/select";
import { Check, ChevronsUpDown } from "lucide-react";
import type { ReactNode } from "react";
import { cn } from "@/lib/cn";

export type SelectOption = { value: string; label: string; icon?: ReactNode; hint?: string };

/**
 * A dropdown on Base UI's Select (keyboard search, arrow keys, screen-reader roles come with it).
 * `label` is the visible caption; it is also the accessible name.
 */
export function Select({ value, onChange, options, label, placeholder, className }: { value: string; onChange: (next: string) => void; options: SelectOption[]; label: string; placeholder?: string; className?: string }) {
  const items = options.map((o) => ({ value: o.value, label: o.label }));
  return (
    <BaseSelect.Root items={items} value={value || null} onValueChange={(next) => next && onChange(next as string)}>
      <div className={cn("flex flex-col gap-1.5", className)}>
        <BaseSelect.Label className="text-xs font-semibold text-ink-2">{label}</BaseSelect.Label>
        <BaseSelect.Trigger
          className={cn(
            "flex min-w-[14rem] items-center justify-between gap-3 rounded-xl bg-inset px-3 py-2.5 text-[0.9rem] font-semibold outline-none",
            "shadow-[inset_0_0_0_1px_var(--line)] hover:bg-card focus-visible:shadow-[inset_0_0_0_2px_var(--brand)] data-popup-open:shadow-[inset_0_0_0_2px_var(--brand)]",
          )}
        >
          <BaseSelect.Value placeholder={placeholder} className="data-placeholder:font-medium data-placeholder:text-ink-3" />
          <BaseSelect.Icon className="text-ink-3 [&>svg]:size-4"><ChevronsUpDown /></BaseSelect.Icon>
        </BaseSelect.Trigger>
      </div>
      <BaseSelect.Portal>
        <BaseSelect.Positioner sideOffset={6} className="z-50 select-none outline-none">
          <BaseSelect.Popup className="max-h-[var(--available-height)] min-w-[var(--anchor-width)] origin-[var(--transform-origin)] overflow-hidden rounded-2xl bg-card text-ink shadow-float outline-none transition-[scale,opacity] duration-100 data-ending-style:scale-95 data-ending-style:opacity-0 data-starting-style:scale-95 data-starting-style:opacity-0">
            <BaseSelect.List className="max-h-[min(22rem,var(--available-height))] overflow-y-auto p-1.5">
              {options.map((o) => (
                <BaseSelect.Item key={o.value} value={o.value} className="grid cursor-default grid-cols-[1.1rem_auto_1fr] items-center gap-2.5 rounded-xl px-2.5 py-2 text-sm outline-none data-highlighted:bg-inset">
                  <BaseSelect.ItemIndicator className="col-start-1 text-brand [&>svg]:size-4"><Check /></BaseSelect.ItemIndicator>
                  <span className="col-start-2 empty:hidden">{o.icon}</span>
                  <BaseSelect.ItemText className="col-start-3 font-medium">{o.label}</BaseSelect.ItemText>
                </BaseSelect.Item>
              ))}
            </BaseSelect.List>
          </BaseSelect.Popup>
        </BaseSelect.Positioner>
      </BaseSelect.Portal>
    </BaseSelect.Root>
  );
}
