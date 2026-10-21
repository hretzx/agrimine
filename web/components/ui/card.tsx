import type { ComponentProps, ReactNode } from "react";
import { cn } from "@/lib/cn";

/** The one card: white (or forest) surface, soft ring, top sheen and a faint green glow along the top edge. */
export function Card({ className, ...props }: ComponentProps<"section">) {
  return (
    <section
      className={cn(
        "relative overflow-hidden rounded-card bg-card px-5 pb-5 pt-[1.1rem] shadow-card",
        "bg-[radial-gradient(140%_55%_at_50%_-22%,var(--glow),transparent_62%)]",
        className,
      )}
      {...props}
    />
  );
}

export function CardHeader({ icon, title, subtitle, action }: { icon?: ReactNode; title: ReactNode; subtitle?: ReactNode; action?: ReactNode }) {
  return (
    <header className="mb-3.5 flex items-center justify-between gap-2.5">
      <div className="flex items-center gap-2.5">
        {icon && <span className="text-ink-3 [&>svg]:size-[1.1rem]">{icon}</span>}
        <div>
          <h2 className="text-[0.95rem] font-semibold leading-tight tracking-tight">{title}</h2>
          {subtitle && <p className="mt-0.5 text-xs text-ink-3">{subtitle}</p>}
        </div>
      </div>
      {action}
    </header>
  );
}
