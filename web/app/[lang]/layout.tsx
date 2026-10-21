import type { Metadata } from "next";
import { notFound } from "next/navigation";
import "@fontsource/plus-jakarta-sans/300.css";
import "@fontsource/plus-jakarta-sans/400.css";
import "@fontsource/plus-jakarta-sans/600.css";
import "@fontsource/plus-jakarta-sans/700.css";
import "@fontsource/noto-sans-devanagari/devanagari-400.css";
import "@fontsource/noto-sans-devanagari/devanagari-600.css";
import "@fontsource/noto-sans-devanagari/devanagari-700.css";
import "../globals.css";
import { LOCALES, isLocale } from "@/lib/i18n/config";
import { AppShell } from "@/components/farm/app-shell";
import { MotionRoot } from "@/components/motion";
import { I18nProvider } from "@/lib/i18n/provider";

export const metadata: Metadata = { title: "AgriMine", description: "Smarter crops. Healthier farms." };

// Every locale is a prebuilt route (a static export cannot discover them at request time).
export function generateStaticParams() {
  return LOCALES.map((lang) => ({ lang }));
}
export const dynamicParams = false;

// Set the theme before the first paint so a dark-mode user never sees a white flash.
const themeScript = `try{var t=localStorage.getItem('theme');if(!t){t=matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light'}document.documentElement.dataset.theme=t}catch(e){}`;

export default async function RootLayout({ children, params }: LayoutProps<"/[lang]">) {
  const { lang } = await params;
  if (!isLocale(lang)) notFound();
  return (
    <html lang={lang} suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeScript }} />
      </head>
      <body>
        <I18nProvider locale={lang}>
          <MotionRoot><AppShell>{children}</AppShell></MotionRoot>
        </I18nProvider>
      </body>
    </html>
  );
}
