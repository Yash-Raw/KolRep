import type { Metadata } from "next";
import localFont from "next/font/local";
import { Suspense } from "react";
import { Navbar } from "@/components/layout/Navbar";
import { ModelSetupModal } from "@/components/desktop/ModelSetupModal";
import "./globals.css";

const studioFont = localFont({ src: "../public/fonts/SpaceGrotesk.ttf", variable: "--font-studio", display: "swap", weight: "300 700" });
const consoleFont = localFont({ src: "../public/fonts/IBMPlexMono-Regular.ttf", variable: "--font-console", display: "swap", weight: "400" });

export const metadata: Metadata = {
  title: "VoiceRep — 100% Local AI Voice Cloning & Studio Narration",
  description:
    "Instant zero-shot local voice cloning and studio narration with dual-layer C2PA cryptographic provenance and 100% data privacy.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`h-full ${studioFont.variable} ${consoleFont.variable}`}>
      <body className="min-h-full flex flex-col antialiased">
        <a href="#main-content" className="skip-link">Skip to content</a>
        <Suspense fallback={<div className="h-16 border-b border-line " />}>
          <Navbar />
        </Suspense>
        <main id="main-content" className="flex-1 flex flex-col">
          <Suspense fallback={<div className="py-20 text-center text-sm text-muted">Loading...</div>}>
            {children}
          </Suspense>
        </main>
        <ModelSetupModal />
      </body>
    </html>
  );
}
