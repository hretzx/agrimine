"use client";

import { AlertTriangle } from "lucide-react";
import { useT } from "@/lib/i18n/provider";
import { Button, ButtonLink } from "./button";
import { useI18n } from "@/lib/i18n/provider";

/** A calm placeholder while data loads: same height as the content, so the page does not jump. */
export function Loading({ className = "h-32" }: { className?: string }) {
  const t = useT();
  return (
    <div role="status" aria-live="polite" className={`grid place-items-center rounded-tile bg-inset text-sm text-ink-3 ${className}`}>
      <span className="sr-only">{t("state.loading")}</span>
      <span aria-hidden="true" className="size-5 animate-spin rounded-full border-2 border-line border-t-brand" />
    </div>
  );
}

/** A visible, plain-language error with a way out. Never an empty card and never a stack trace. */
export function ErrorState({ onRetry }: { onRetry?: () => void }) {
  const t = useT();
  return (
    <div role="alert" className="flex flex-col items-center gap-3 rounded-tile bg-coral/12 p-5 text-center text-sm text-coral-ink">
      <AlertTriangle className="size-5" aria-hidden="true" />
      <p>{t("state.error")}</p>
      {onRetry && <Button variant="outline" onClick={onRetry}>{t("state.retry")}</Button>}
    </div>
  );
}

/** What a card says when nothing has been saved yet: a sentence and the way forward, never a spinner that never ends. */
export function NoCheck({ className = "h-60" }: { className?: string }) {
  const { t, locale } = useI18n();
  return (
    <div className={`flex flex-col items-center justify-center gap-3 rounded-tile bg-inset text-center ${className}`} data-testid="no-check">
      <p className="max-w-[16rem] text-sm text-ink-3">{t("check.none")}</p>
      <ButtonLink href={`/${locale}/check/`} variant="outline">{t("action.newCheck")}</ButtonLink>
    </div>
  );
}
