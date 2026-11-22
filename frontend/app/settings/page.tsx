"use client";

import { PageHeader } from "@/components/ui/StudioUI";
import { useEffect, useState } from "react";
import { Shield, Database, Server, Laptop, RefreshCw, HardDrive, CheckCircle2, Cpu, Layers } from "lucide-react";
import { api, getBackendUrl } from "@/lib/api";

export default function SettingsPage() {
  const [backendStatus, setBackendStatus] = useState<any>(null);
  const [desktopStatus, setDesktopStatus] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [cacheCleared, setCacheCleared] = useState(false);

  useEffect(() => {
    Promise.all([
      fetch(`${getBackendUrl()}/api/v1/health`)
        .then((res) => res.json())
        .catch(() => ({ status: "offline" })),
      api.getDesktopStatus().catch(() => null),
    ])
      .then(([health, desktop]) => {
        setBackendStatus(health);
        setDesktopStatus(desktop);
      })
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
    <div className="page settings-page">
      <PageHeader number="06" label="Workspace settings" title="Behind the sound." description="Your local system, provenance configuration, and workspace data." />

      <div className="settings-sections">
        {/* System & Integration Status */}
        <div className="settings-section space-y-5">
          <div className="flex items-center gap-2.5 pb-2 border-b border-line ">
            <Server className="h-5 w-5 text-muted" />
            <h3 className="font-semibold text-base text-ink ">Local System Infrastructure</h3>
          </div>

          <div className="grid grid-cols-1 gap-4 pt-2">
            <div className="p-4 rounded-lg bg-canvas  border border-line/60  space-y-1">
              <span className="text-xs text-muted font-medium">FastAPI Engine</span>
              <p className="font-semibold text-sm capitalize text-emerald-600 dark:text-emerald-400 flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
                {backendStatus?.status === "ok" ? "Connected (Local :8000)" : "Degraded / Offline"}
              </p>
            </div>

            <div className="p-4 rounded-lg bg-canvas  border border-line/60  space-y-1">
              <span className="text-xs text-muted font-medium">Database</span>
              <p className="font-semibold text-sm capitalize text-emerald-600 dark:text-emerald-400 flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
                {backendStatus?.desktop_mode
                  ? "Healthy (Local SQLite - Offline)"
                  : backendStatus?.database === "healthy"
                  ? "Healthy (Local PostgreSQL)"
                  : "Checking"}
              </p>
            </div>

            <div className="p-4 rounded-lg bg-canvas  border border-line/60  space-y-1">
              <span className="text-xs text-muted font-medium">Background Job Queue</span>
              <p className="font-semibold text-sm capitalize text-emerald-600 dark:text-emerald-400 flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
                {backendStatus?.desktop_mode || backendStatus?.redis?.includes("desktop mode")
                  ? "Active (Local Desktop In-Memory Queue)"
                  : backendStatus?.redis === "healthy"
                  ? "Healthy (Local Redis)"
                  : "Connecting"}
              </p>
            </div>
          </div>
        </div>

        {/* Neural Hardware Acceleration & Models */}
        {desktopStatus && (
          <div className="settings-section space-y-5">
            <div className="flex items-center gap-2.5 pb-2 border-b border-line ">
              <Cpu className="h-5 w-5 text-emerald-500" />
              <h3 className="font-semibold text-base text-ink ">Neural Inference & Acceleration</h3>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
              <div className="p-3.5 rounded-lg bg-canvas border border-line/60 space-y-1">
                <span className="text-muted font-medium">Hardware Backend</span>
                <p className="font-semibold text-ink text-sm flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
                  {desktopStatus.is_apple_silicon ? "Apple Silicon (MPS Hardware Accelerated)" : desktopStatus.device?.toUpperCase() || "CPU"}
                </p>
              </div>

              <div className="p-3.5 rounded-lg bg-canvas border border-line/60 space-y-1">
                <span className="text-muted font-medium">FFmpeg Audio Engine</span>
                <p className="font-semibold text-ink text-sm flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
                  {desktopStatus.ffmpeg?.available ? "Detected & Connected" : "Missing"}
                </p>
              </div>
            </div>

            {/* Models Status */}
            <div className="space-y-2 pt-1">
              <span className="text-xs text-muted font-semibold uppercase tracking-wider">Neural Model Weights</span>
              <div className="grid grid-cols-1 gap-2">
                {desktopStatus.models?.ready_models?.map((m: any) => (
                  <div key={m.id} className="p-3 rounded-md bg-canvas border border-line/60 flex items-center justify-between text-xs">
                    <div className="flex items-center gap-2">
                      <Layers className="h-3.5 w-3.5 text-muted" />
                      <span className="font-medium text-ink">{m.name}</span>
                    </div>
                    <span className="font-mono text-emerald-600 dark:text-emerald-400 font-semibold bg-emerald-50 dark:bg-emerald-950/40 px-2 py-0.5 rounded text-[11px]">
                      Ready ({m.approx_size_mb} MB)
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* Storage Info */}
            {desktopStatus.models?.disk_space && (
              <div className="p-3 rounded-md bg-canvas border border-line/60 text-xs text-muted flex items-center justify-between">
                <span>Free Disk Space</span>
                <span className="font-mono font-medium text-ink">{desktopStatus.models.disk_space.free_gb} GB Available</span>
              </div>
            )}
          </div>
        )}

        {/* Pure Local Desktop Mode */}
        <div className="settings-section space-y-5">
          <div className="flex items-center gap-2.5 pb-2 border-b border-line ">
            <Laptop className="h-5 w-5 text-emerald-500" />
            <h3 className="font-semibold text-base text-ink ">Pure Local Single-User Mode</h3>
          </div>

          <p className="text-xs text-muted  leading-relaxed">
            KolRep is running in pure single-user local workstation mode. Audio generation, feature extraction, neural inference, and C2PA signing are executed entirely on your machine.
          </p>

          <div className="grid grid-cols-1 gap-3 text-xs pt-1">
            <div className="p-3.5 rounded-md bg-canvas  border border-line/60  flex items-center justify-between">
              <span className="text-muted">Machine Identity</span>
              <span className="font-mono font-medium text-ink ">local-owner</span>
            </div>
            <div className="p-3.5 rounded-md bg-canvas  border border-line/60  flex items-center justify-between">
              <span className="text-muted">Network Boundary</span>
              <span className="font-medium text-emerald-600 dark:text-emerald-400">100% On-Device / Zero Cloud</span>
            </div>
          </div>
        </div>

        {/* Security & Speaker Verification Policy */}
        <div className="settings-section space-y-5">
          <div className="flex items-center gap-2.5 pb-2 border-b border-line ">
            <Shield className="h-5 w-5 text-muted" />
            <h3 className="font-semibold text-base text-ink ">Provenance & Safety Standards</h3>
          </div>

          <p className="text-xs text-muted  leading-relaxed">
            Every audio file synthesized by KolRep embeds dual-layer provenance protection: an inaudible acoustic watermark (QIM) and an ECDSA P-256 signed C2PA manifest compliant with EU AI Act Article 50.
          </p>

          <div className="p-4 rounded-lg bg-canvas  border border-line  text-xs text-muted  space-y-1">
            <p className="font-semibold text-ink ">Revocation & Deletion Guarantee:</p>
            <p>
              When you delete a voice in the Voice Library, KolRep immediately deletes the model checkpoints, acoustic embeddings, and audio samples directly from your disk.
            </p>
          </div>
        </div>

        {/* Local Storage & Cache */}
        <div className="settings-section space-y-5">
          <div className="flex items-center gap-2.5 pb-2 border-b border-line ">
            <HardDrive className="h-5 w-5 text-muted" />
            <h3 className="font-semibold text-base text-ink ">Local Workspace & Data</h3>
          </div>

          <div className="flex flex-col items-start gap-4">
            <div>
              <h4 className="text-sm font-semibold text-ink ">Clear Browser Playback Cache</h4>
              <p className="text-xs text-muted">Resets temporary audio blob URLs and session playback buffers.</p>
            </div>
            <button
              onClick={handleClearCache}
              className="px-4 py-2 rounded-md border border-line  text-xs font-medium text-ink  hover:bg-soft  transition-colors flex items-center gap-1.5"
            >
              {cacheCleared ? (
                <>
                  <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" />
                  <span>Cache Cleared</span>
                </>
              ) : (
                <>
                  <RefreshCw className="h-3.5 w-3.5 text-muted" />
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
