"use client";

import { Database, Plus, Search, Wheat } from "lucide-react";
import { Suspense, useState } from "react";
import { LocaleSwitch, ThemeToggle } from "@/components/farm/controls";
import { CropGlyph, DRAWN_CROPS } from "@/components/farm/crop-glyph";
import { CropRow } from "@/components/farm/crop-row";
import { Sidebar } from "@/components/farm/sidebar";
import { StatCard } from "@/components/farm/stat-card";
import { Badge, STATUS_TONE } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardHeader } from "@/components/ui/card";
import { IconButton } from "@/components/ui/icon-button";
import { Segmented } from "@/components/ui/segmented";
import { Tip } from "@/components/ui/tooltip";
import { Track } from "@/components/ui/track";
import { useT } from "@/lib/i18n/provider";

/** The component gallery: every shared component in every state. The visual tests photograph this page (e2e/). */
function GalleryBody() {
  const t = useT();
  const [seg, setSeg] = useState<"a" | "b">("a");
  return (
    <div className="flex min-h-screen">
      <Sidebar active="home" badges={{ doctor: { text: t("status.good"), tone: "mint" }, planb: { text: "3", tone: "neutral" } }} />
      <main className="min-w-0 flex-1 space-y-3 px-[1.625rem] py-[1.375rem]" data-testid="gallery">
        <div className="flex items-center justify-between gap-4">
          <div>
            <h1 className="text-[1.6rem] font-semibold tracking-tight">{t("dev.title")}</h1>
            <p className="mt-0.5 text-sm text-ink-3">{t("dev.subtitle")}</p>
          </div>
          <div className="flex items-center gap-2.5">
            <LocaleSwitch />
            <ThemeToggle />
            <Button><Plus />{t("action.newCheck")}</Button>
          </div>
        </div>

        <div className="grid grid-cols-3 gap-3">
          <StatCard icon={<Database />} label={t("stat.records")} value="2,200" tint="linear-gradient(160deg,#e9f7e4,#cdebc3)" note={<Badge tone="lavender">{t("dev.readings", { count: 7 })}</Badge>} />
          <StatCard icon={<Wheat />} label={t("stat.crops")} value="22" tint="linear-gradient(160deg,#fff6d6,#f5df8e)" note={<Badge tone="butter">≈100</Badge>} />
          <StatCard icon={<Search />} label={t("stat.checks")} value="18" tint="linear-gradient(160deg,#e4f4fc,#bfe6f6)" />
        </div>

        <div className="grid grid-cols-2 gap-3">
          <Card>
            <CardHeader title="Buttons" subtitle="Base UI Button, four variants, disabled" />
            <div className="flex flex-wrap items-center gap-2.5">
              <Button>Primary</Button>
              <Button variant="dark">Dark</Button>
              <Button variant="outline">Outline</Button>
              <Button variant="ghost">Ghost</Button>
              <Button disabled>Disabled</Button>
              <Tip text="Icon buttons need a label"><IconButton label="Search"><Search /></IconButton></Tip>
              <Segmented value={seg} onChange={setSeg} label="Demo" options={[{ value: "a", label: "Option A" }, { value: "b", label: "Option B" }]} />
            </div>
          </Card>
          <Card>
            <CardHeader title="Badges" subtitle="Words always accompany colour" />
            <div className="flex flex-wrap gap-2">
              <Badge tone={STATUS_TONE.good}>{t("status.good")}</Badge>
              <Badge tone={STATUS_TONE.moderate}>{t("status.moderate")}</Badge>
              <Badge tone={STATUS_TONE.attention}>{t("status.attention")}</Badge>
              <Badge tone="lavender">{t("status.predicted")}</Badge>
              <Badge tone="sky">{t("status.pending")}</Badge>
              <Badge tone="ink">{t("level.strong")}</Badge>
              <Badge>neutral</Badge>
            </div>
          </Card>
          <Card>
            <CardHeader title="Tracks" subtitle="Base UI Progress: role=progressbar, 0 to 100" />
            <div className="space-y-3.5">
              <Track value={99.5} label="Naive Bayes" color="linear-gradient(90deg,#b79ced,#9d7de0)" hatch />
              <Track value={90.2} label="ID3" color="linear-gradient(90deg,#f4cf58,#e9b22e)" hatch />
              <Track value={42} label="Plain" />
              <Track value={140} label="Clamped above 100" />
            </div>
          </Card>
          <Card>
            <CardHeader title="Crop rows" subtitle="Similarity bar, status, score" />
            <div className="space-y-2">
              <CropRow crop="rice" name="Rice" subtitle="Match" score={60} tone="mint" tag={t("status.good")} color="var(--mint)" />
              <CropRow crop="jute" name="Jute" subtitle="Match" score={45} tone="butter" tag={t("status.moderate")} color="var(--butter)" />
              <CropRow crop="unknown-crop" name="A crop without a drawing" subtitle="Neutral leaf fallback" score={13} tone="coral" tag={t("level.consider")} color="var(--coral)" />
            </div>
          </Card>
          <Card className="col-span-2">
            <CardHeader title="Crop glyphs" subtitle={`${DRAWN_CROPS.length} of 22 drawn, plus the fallback for an unknown crop`} />
            <div className="flex flex-wrap items-center gap-3">
              {[...DRAWN_CROPS, "unknown-crop"].map((c) => (
                <div key={c} className="flex flex-col items-center gap-1 text-[0.7rem] text-ink-3">
                  <CropGlyph crop={c} size={52} />
                  {c}
                </div>
              ))}
            </div>
          </Card>
        </div>
      </main>
    </div>
  );
}

export default function Gallery() {
  return (
    <Suspense fallback={null}>
      <GalleryBody />
    </Suspense>
  );
}
