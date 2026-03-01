import type { Metadata } from "next";
import { Lexend, Noto_Sans_KR } from "next/font/google";
import type { ReactNode } from "react";

import { BRAND_DESCRIPTION, BRAND_KO, BRAND_NAME, BRAND_TITLE } from "@/lib/brand";

import "./globals.css";

const displayFont = Lexend({
  subsets: ["latin"],
  variable: "--font-display",
  display: "swap",
});

const bodyFont = Noto_Sans_KR({
  subsets: ["latin"],
  variable: "--font-body",
  display: "swap",
});

const FALLBACK_SITE_URL = "http://localhost:3000";

function resolveSiteUrl() {
  const value = process.env.NEXT_PUBLIC_SITE_URL?.trim();
  if (!value) return FALLBACK_SITE_URL;

  try {
    return new URL(value).toString().replace(/\/$/, "");
  } catch {
    return FALLBACK_SITE_URL;
  }
}

const siteUrl = resolveSiteUrl();

export const metadata: Metadata = {
  metadataBase: new URL(siteUrl),
  title: BRAND_TITLE,
  description: BRAND_DESCRIPTION,
  applicationName: BRAND_NAME,
  alternates: {
    canonical: "/",
  },
  openGraph: {
    type: "website",
    locale: "ko_KR",
    url: siteUrl,
    siteName: BRAND_NAME,
    title: BRAND_TITLE,
    description: `${BRAND_KO} 운영 웹앱`,
  },
  twitter: {
    card: "summary",
    title: BRAND_TITLE,
    description: `${BRAND_KO} 운영 웹앱`,
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: ReactNode;
}>) {
  return (
    <html lang="ko">
      <body className={`${displayFont.variable} ${bodyFont.variable}`}>{children}</body>
    </html>
  );
}
