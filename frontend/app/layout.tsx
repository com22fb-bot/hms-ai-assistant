import type { Metadata, Viewport } from "next";
import { Fraunces, Outfit } from "next/font/google";

import "./globals.css";
import "./approved-ui.css";

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
  title: "HMS AI Assistant — Centro Inteligente",
  description:
    "Centro Inteligente de Operaciones basado en Casos Inteligentes.",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 5,
  viewportFit: "cover",
  themeColor: "#0a0e10",
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
