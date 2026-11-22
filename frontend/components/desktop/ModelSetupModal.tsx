"use client";

import { useEffect, useState } from "react";
import { DownloadCloud, CheckCircle2, HardDrive, Cpu, AlertCircle, Loader2, X } from "lucide-react";
import { DialogFrame } from "@/components/ui/DialogFrame";
import { api } from "@/lib/api";

export function ModelSetupModal() {
  const [isOpen, setIsOpen] = useState(false);
  const [statusData, setStatusData] = useState<any>(null);
  const [isDownloading, setIsDownloading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [currentTask, setCurrentTask] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;

    async function checkStatus() {
      try {
        const data = await api.getDesktopStatus();
        if (!isMounted) return;
        setStatusData(data);

        // If models are not ready, prompt first-run setup
        if (data?.models && !data.models.all_ready) {
          setIsOpen(true);
        }
      } catch (err) {
        // Not running in desktop mode or backend not yet reached
      }
    }

    checkStatus();
    return () => {
      isMounted = false;
    };
  }, []);

  // Poll download progress when downloading
  useEffect(() => {
    if (!isDownloading) return;

    const interval = setInterval(async () => {
      try {
        const downloadStatus = await api.getModelDownloadStatus();
        if (downloadStatus.is_downloading) {
          setProgress(downloadStatus.progress || 0);
          setCurrentTask(downloadStatus.current_task || "Downloading neural weights...");
        } else if (downloadStatus.progress >= 100) {
          setProgress(100);
          setCurrentTask("Download complete!");
          setIsDownloading(false);
          setTimeout(() => {
            setIsOpen(false);
          }, 1500);
        } else if (downloadStatus.error) {
          setError(downloadStatus.error);
          setIsDownloading(false);
        }
      } catch {
        // ignore poll errors
      }
    }, 1000);

    return () => clearInterval(interval);
  }, [isDownloading]);

  const handleStartDownload = async () => {
    setError(null);
    setIsDownloading(true);
    setProgress(5);
    setCurrentTask("Initiating download...");

    try {
      await api.triggerModelDownload();
    } catch (err: any) {
      setError(err.message || "Failed to initiate download.");
      setIsDownloading(false);
    }
  };

  if (!isOpen || !statusData) return null;

  const disk = statusData?.models?.disk_space;
  const missingModels = statusData?.models?.missing_models || [];

  return (
    <DialogFrame onClose={() => !isDownloading && setIsOpen(false)}>
      <div className="dialog-panel max-w-lg" role="dialog" aria-modal="true" aria-label="First-Run Model Setup">
        {/* Header */}
        <div className="dialog-header flex items-center justify-between px-6 py-5 border-b border-line">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-soft text-ink">
              <DownloadCloud className="h-5 w-5" />
            </div>
            <div>
              <h3 className="font-semibold text-lg text-ink">First-Run Model Setup</h3>
              <p className="text-xs text-muted">Offline Neural Inference Engine</p>
            </div>
          </div>
          {!isDownloading && (
            <button
              onClick={() => setIsOpen(false)}
              aria-label="Close setup modal"
              className="p-1 rounded-lg text-muted hover:text-ink hover:bg-soft transition-colors"
            >
              <X className="h-5 w-5" />
            </button>
          )}
        </div>

        {/* Content */}
        <div className="p-6 space-y-5">
          <p className="text-sm text-ink leading-relaxed">
            KolRep generates speech and aligns voices using modern <strong>F5-TTS Diffusion Transformers</strong> and <strong>Whisper</strong>. To ensure complete privacy with zero cloud dependencies, the neural model weights are stored locally on your Mac.
          </p>

          {/* Hardware & Storage Badge */}
          <div className="grid grid-cols-2 gap-3 p-3 rounded-lg bg-soft border border-line text-xs">
            <div className="flex items-center gap-2">
              <Cpu className="h-4 w-4 text-muted" />
              <div>
                <p className="font-medium text-ink">Acceleration</p>
                <p className="text-muted">{statusData.mps_available ? "Apple Silicon (MPS)" : "CPU Fallback"}</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <HardDrive className="h-4 w-4 text-muted" />
              <div>
                <p className="font-medium text-ink">Free Disk Space</p>
                <p className="text-muted">{disk?.free_gb ?? "?"} GB available</p>
              </div>
            </div>
          </div>

          {/* Models List */}
          <div className="space-y-2">
            <p className="text-xs font-semibold text-muted uppercase tracking-wider">Required Weights (~1.05 GB total)</p>
            <div className="space-y-1.5">
              {missingModels.map((m: any) => (
                <div key={m.id} className="flex items-center justify-between p-2.5 rounded-lg border border-line text-xs bg-card">
                  <span className="font-medium text-ink">{m.name}</span>
                  <span className="text-muted font-mono">{m.approx_size_mb} MB</span>
                </div>
              ))}
            </div>
          </div>

          {error && (
            <div className="flex items-center gap-2 p-3 rounded-lg bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-800 text-xs text-red-600 dark:text-red-400">
              <AlertCircle className="h-4 w-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {/* Download Progress */}
          {isDownloading ? (
            <div className="space-y-3 pt-2">
              <div className="flex items-center justify-between text-xs text-ink font-medium">
                <span className="flex items-center gap-2">
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  {currentTask}
                </span>
                <span className="font-mono">{Math.round(progress)}%</span>
              </div>
              <div className="w-full bg-soft rounded-full h-2 overflow-hidden border border-line">
                <div
                  className="bg-ink h-2 rounded-full transition-all duration-300"
                  style={{ width: `${progress}%` }}
                />
              </div>
            </div>
          ) : (
            <div className="pt-2 flex justify-end gap-3">
              <button
                type="button"
                onClick={() => setIsOpen(false)}
                className="px-4 py-2 text-xs font-medium text-muted hover:text-ink hover:bg-soft rounded-lg transition-colors"
              >
                Remind Me Later
              </button>
              <button
                type="button"
                onClick={handleStartDownload}
                className="px-5 py-2 text-xs font-semibold text-paper bg-ink rounded-lg hover:opacity-90 transition-opacity flex items-center gap-2"
              >
                <DownloadCloud className="h-4 w-4" />
                Download Models
              </button>
            </div>
          )}
        </div>
      </div>
    </DialogFrame>
  );
}
