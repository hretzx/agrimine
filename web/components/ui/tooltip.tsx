"use client";

import { Tooltip as BaseTooltip } from "@base-ui/react/tooltip";
import type { ReactElement, ReactNode } from "react";

/** Wrap ONE focusable element: <Tip text="..."><IconButton .../></Tip>. Shows on hover and on keyboard focus. */
export function Tip({ text, children }: { text: ReactNode; children: ReactElement }) {
  return (
    <BaseTooltip.Provider>
      <BaseTooltip.Root>
        <BaseTooltip.Trigger render={children} />
        <BaseTooltip.Portal>
          <BaseTooltip.Positioner sideOffset={8}>
            <BaseTooltip.Popup className="rounded-lg bg-ink px-2.5 py-1.5 text-xs font-medium text-card shadow-float">{text}</BaseTooltip.Popup>
          </BaseTooltip.Positioner>
        </BaseTooltip.Portal>
      </BaseTooltip.Root>
    </BaseTooltip.Provider>
  );
}
