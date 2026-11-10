"use client";

import { useEffect, useState } from "react";
import { Shield, Database, Server, Laptop, RefreshCw, HardDrive, CheckCircle2 } from "lucide-react";

export default function SettingsPage() {
  const [backendStatus, setBackendStatus] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [cacheCleared, setCacheCleared] = useState(false);

  useEffect(() => {
    fetch(`${process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000"}/api/v1/health`)
      .then((res) => res.json())
      .then((data) => setBackendStatus(data))
      .catch(() => setBackendStatus({ status: "offline" }))
      .finally(() => setLoading(false));
  }, []);

  const handleClearCache = () => {
    // Clear any local temporary playback caches
    if (typeof window !== "undefined") {
      sessionStorage.clear();
      setCacheCleared(true);
      setTimeout(() => setCacheCleared(false), 3000);
    }
  };

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-10 w-full space-y-8">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-neutral-900 dark:text-white">Settings</h1>
        <p className="text-sm text-neutral-500 mt-1">Platform architecture, hardware acceleration, and provenance configuration.</p>
      </div>

      <div className="space-y-6">
        {/* System & Integration Status */}
        <div className="p-6 rounded-3xl border border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-900 shadow-xs space-y-4">
          <div className="flex items-center gap-2.5 pb-2 border-b border-neutral-100 dark:border-neutral-800">
            <Server className="h-5 w-5 text-neutral-500" />
            <h3 className="font-semibold text-base text-neutral-900 dark:text-white">Local System Infrastructure</h3>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-2">
            <div className="p-4 rounded-2xl bg-neutral-50 dark:bg-neutral-800/50 border border-neutral-200/60 dark:border-neutral-700/60 space-y-1">
              <span className="text-xs text-neutral-500 font-medium">FastAPI Engine</span>
              <p className="font-semibold text-sm capitalize text-emerald-600 dark:text-emerald-400 flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
                {backendStatus?.status === "ok" ? "Connected (Local :8000)" : "Degraded / Offline"}
              </p>
            </div>

            <div className="p-4 rounded-2xl bg-neutral-50 dark:bg-neutral-800/50 border border-neutral-200/60 dark:border-neutral-700/60 space-y-1">
              <span className="text-xs text-neutral-500 font-medium">PostgreSQL Database</span>
              <p className="font-semibold text-sm capitalize text-emerald-600 dark:text-emerald-400 flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
                {backendStatus?.database === "healthy" ? "Healthy (Local PostgreSQL)" : "Checking"}
              </p>
            </div>

            <div className="p-4 rounded-2xl bg-neutral-50 dark:bg-neutral-800/50 border border-neutral-200/60 dark:border-neutral-700/60 space-y-1">
              <span className="text-xs text-neutral-500 font-medium">Redis / ARQ Worker</span>
              <p className="font-semibold text-sm capitalize text-emerald-600 dark:text-emerald-400 flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
                {backendStatus?.redis === "healthy" ? "Healthy (Local Redis)" : "Checking"}
              </p>
            </div>
          </div>
        </div>

        {/* Pure Local Desktop Mode */}
        <div className="p-6 rounded-3xl border border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-900 shadow-xs space-y-4">
          <div className="flex items-center gap-2.5 pb-2 border-b border-neutral-100 dark:border-neutral-800">
            <Laptop className="h-5 w-5 text-emerald-500" />
            <h3 className="font-semibold text-base text-neutral-900 dark:text-white">Pure Local Single-User Mode</h3>
          </div>

          <p className="text-xs text-neutral-600 dark:text-neutral-400 leading-relaxed">
            VoiceRep is running in pure single-user local workstation mode. Audio generation, feature extraction, neural inference, and C2PA signing are executed entirely on your machine.
          </p>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs pt-1">
            <div className="p-3.5 rounded-xl bg-neutral-50 dark:bg-neutral-800/40 border border-neutral-200/60 dark:border-neutral-700/60 flex items-center justify-between">
              <span className="text-neutral-500">Machine Identity</span>
              <span className="font-mono font-medium text-neutral-800 dark:text-neutral-200">local-owner</span>
            </div>
            <div className="p-3.5 rounded-xl bg-neutral-50 dark:bg-neutral-800/40 border border-neutral-200/60 dark:border-neutral-700/60 flex items-center justify-between">
              <span className="text-neutral-500">Network Boundary</span>
              <span className="font-medium text-emerald-600 dark:text-emerald-400">100% On-Device / Zero Cloud</span>
            </div>
          </div>
        </div>

        {/* Security & Speaker Verification Policy */}
        <div className="p-6 rounded-3xl border border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-900 shadow-xs space-y-4">
          <div className="flex items-center gap-2.5 pb-2 border-b border-neutral-100 dark:border-neutral-800">
            <Shield className="h-5 w-5 text-neutral-500" />
            <h3 className="font-semibold text-base text-neutral-900 dark:text-white">Provenance & Safety Standards</h3>
          </div>

          <p className="text-xs text-neutral-600 dark:text-neutral-400 leading-relaxed">
            Every audio file synthesized by VoiceRep embeds dual-layer provenance protection: an inaudible acoustic watermark (QIM) and an ECDSA P-256 signed C2PA manifest compliant with EU AI Act Article 50.
          </p>

          <div className="p-4 rounded-2xl bg-neutral-50 dark:bg-neutral-800/40 border border-neutral-200 dark:border-neutral-700 text-xs text-neutral-600 dark:text-neutral-300 space-y-1">
            <p className="font-semibold text-neutral-900 dark:text-white">Revocation & Deletion Guarantee:</p>
            <p>
              When you delete a voice in the Voice Library, VoiceRep immediately deletes the model checkpoints, acoustic embeddings, and audio samples directly from your disk.
            </p>
          </div>
        </div>

        {/* Local Storage & Cache */}
        <div className="p-6 rounded-3xl border border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-900 shadow-xs space-y-4">
          <div className="flex items-center gap-2.5 pb-2 border-b border-neutral-100 dark:border-neutral-800">
            <HardDrive className="h-5 w-5 text-neutral-500" />
            <h3 className="font-semibold text-base text-neutral-900 dark:text-white">Local Workspace & Data</h3>
          </div>

          <div className="flex items-center justify-between">
            <div>
              <h4 className="text-sm font-semibold text-neutral-900 dark:text-white">Clear Browser Playback Cache</h4>
              <p className="text-xs text-neutral-500">Resets temporary audio blob URLs and session playback buffers.</p>
            </div>
            <button
              onClick={handleClearCache}
              className="px-4 py-2 rounded-xl border border-neutral-200 dark:border-neutral-800 text-xs font-medium text-neutral-700 dark:text-neutral-300 hover:bg-neutral-100 dark:hover:bg-neutral-800 transition-colors flex items-center gap-1.5"
            >
              {cacheCleared ? (
                <>
                  <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" />
                  <span>Cache Cleared</span>
                </>
              ) : (
                <>
                  <RefreshCw className="h-3.5 w-3.5 text-neutral-500" />
                  <span>Clear Cache</span>
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
