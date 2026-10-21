"use client";

import { CropGlyph } from "@/components/farm/crop-glyph";
import { Select } from "@/components/ui/select";
import { useMeta } from "@/lib/data";
import { useI18n } from "@/lib/i18n/provider";
import { cropName } from "@/lib/labels";

/** Choose one of the 22 crops (names in the language in use). `mark` is a crop key to tag, e.g. the recommended one. */
export function CropSelect({ value, onChange, label, mark, markText }: { value: string; onChange: (key: string) => void; label: string; mark?: string; markText?: string }) {
  const { locale } = useI18n();
  const crops = useMeta().data?.crops ?? [];
  return (
    <Select
      label={label}
      value={value}
      onChange={onChange}
      options={crops.map((c) => ({ value: c.key, label: `${cropName(c, locale)}${mark === c.key && markText ? ` · ${markText}` : ""}`, icon: <CropGlyph crop={c.key} size={24} round /> }))}
    />
  );
}
