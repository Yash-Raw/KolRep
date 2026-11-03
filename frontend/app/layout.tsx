import type { Metadata } from "next";
import { Suspense } from "react";
import { Navbar } from "@/components/layout/Navbar";
import "./globals.css";

export const metadata: Metadata = {
  title: "VoiceRep — AI Voice Replication & Agents",
  description:
    "Upload an authorized voice once. Reusable high-fidelity voice cloning for Text-to-Speech narration and Conversational AI Voice Agents.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="h-full">
      <body className="min-h-full flex flex-col bg-neutral-50/50 dark:bg-neutral-950 text-neutral-900 dark:text-neutral-100 antialiased font-sans selection:bg-neutral-900 selection:text-white dark:selection:bg-white dark:selection:text-neutral-900">
        <Suspense fallback={<div className="h-16 border-b border-neutral-200 dark:border-neutral-800" />}>
          <Navbar />
        </Suspense>
        <main className="flex-1 flex flex-col">
          <Suspense fallback={<div className="py-20 text-center text-sm text-neutral-400">Loading...</div>}>
            {children}
          </Suspense>
        </main>
      </body>
    </html>
  );
}
