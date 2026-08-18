import type { Metadata, Viewport } from "next";
import { Fraunces, Outfit } from "next/font/google";

import "./globals.css";
import "./approved-ui.css";
import "./donexto-skin.css";

const hmsSans = Outfit({
  variable: "--font-hms-sans",
  subsets: ["latin"],
  display: "swap",
});

const hmsDisplay = Fraunces({
  variable: "--font-hms-display",
  subsets: ["latin"],
  display: "swap",
});

export const metadata: Metadata = {
  manifest: "/manifest.webmanifest",
  title: "Donexto — Do Next To…",
  description:
    "Do Next To…: prioridades, dinero y respuestas — antes del caos de la bandeja. donexto.com",
  icons: {
    icon: [
      { url: "/brand/donexto-mark.svg", type: "image/svg+xml" },
      { url: "/favicon.ico" },
    ],
    apple: "/brand/donexto-mark.svg",
  },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 5,
  viewportFit: "cover",
  themeColor: "#070b12",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="es"
      suppressHydrationWarning
      className={`${hmsSans.variable} ${hmsDisplay.variable}`}
    >
      <body className={hmsSans.className}>{children}</body>
    </html>
  );
}
