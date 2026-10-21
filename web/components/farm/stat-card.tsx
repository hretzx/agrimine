import type { ReactNode } from "react";
import { Card } from "@/components/ui/card";

/** A big number with a label, an icon tile and a small note (Home's three summary cards). */
export function StatCard({ icon, label, value, note, tint }: { icon: ReactNode; label: string; value: ReactNode; note?: ReactNode; tint: string }) {
  return (
    <Card className="flex items-center gap-4 px-5 py-4">
      <span className="grid size-[2.9rem] place-items-center rounded-2xl text-[#0b2016] shadow-[inset_0_0_0_1px_rgb(10_10_10/.05),inset_0_1px_0_rgb(255_255_255/.7)] [&>svg]:size-5" style={{ background: tint }}>
        {icon}
      </span>
      <div className="min-w-0">
        <p className="text-[0.8rem] text-ink-3">{label}</p>
        <p className="text-[2.1rem] font-light leading-none tracking-[-0.04em] tabular-nums">{value}</p>
      </div>
      {note && <div className="ml-auto">{note}</div>}
    </Card>
  );
}
