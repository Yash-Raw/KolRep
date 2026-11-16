"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { AlertCircle, Check, Copy, Download, FolderOpen, History, Link as LinkIcon, Loader2, Play, Shield, Sparkles, Trash2 } from "lucide-react";
import { PageHeader } from "@/components/ui/StudioUI";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { api } from "@/lib/api";
import { Generation, Voice } from "@/types";
import { AudioPlayer } from "@/components/audio/AudioPlayer";
import { copyToClipboard, downloadAudioFile, formatAudioFilename } from "@/lib/download";

export default function HistoryPage() {
  const [generations, setGenerations] = useState<Generation[]>([]);
  const [voices, setVoices] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeAudioUrl, setActiveAudioUrl] = useState<string | null>(null);
  const [copiedAction, setCopiedAction] = useState<string | null>(null);
  const [downloadingId, setDownloadingId] = useState<string | null>(null);
  const [genToDelete, setGenToDelete] = useState<Generation | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  const handleDownload = async (gen: Generation) => {
    if (!gen.audio_url || downloadingId) return;
    setDownloadingId(gen.id);
    const filename = formatAudioFilename({
      voiceName: voices[gen.voice_id],
      text: gen.input_text,
      id: gen.id,
    });
    try {
      await downloadAudioFile(gen.audio_url, filename);
    } finally {
      setDownloadingId(null);
    }
  };

  const handleCopy = async (text: string, actionKey: string) => {
    const success = await copyToClipboard(text);
    if (success) {
      setCopiedAction(actionKey);
      setTimeout(() => setCopiedAction(null), 2000);
    }
  };

  useEffect(() => {
    loadHistory();
  }, []);

  const loadHistory = async () => {
    setLoading(true);
    setError(null);
    try {
      const [genRes, voiceRes] = await Promise.all([
        api.getGenerations(1, 50),
        api.getVoices(),
      ]);

      const voiceMap: Record<string, string> = {};
      voiceRes.items.forEach((v) => {
        voiceMap[v.id] = v.name;
      });
      setVoices(voiceMap);
      setGenerations(genRes.items);
    } catch (err: any) {
      setError(err.message || "Failed to load generation history.");
    } finally {
      setLoading(false);
    }
  };

  const handleConfirmDelete = async () => {
    if (!genToDelete) return;
    setIsDeleting(true);
    setDeleteError(null);
    try {
      await api.deleteGeneration(genToDelete.id);
      setGenerations((prev) => prev.filter((g) => g.id !== genToDelete.id));
      if (activeAudioUrl && genToDelete.audio_url && activeAudioUrl.includes(genToDelete.id)) {
        setActiveAudioUrl(null);
      }
      setGenToDelete(null);
    } catch (err: any) {
      setDeleteError(err.message || "Failed to delete generation");
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <div className="page history-page">
      <PageHeader number="03" label="Recording archive" title="Every take, on record." description="Listen back, pick up where you left off, or take your audio with you." actions={<Link href="/studio" className="btn btn-primary"><Sparkles size={16} />New recording</Link>} />

      {error && (
        <div className="flex items-center gap-2 p-4 rounded-md bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-800 text-sm text-red-600 dark:text-red-400">
          <AlertCircle className="h-4 w-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Floating Audio Player when active */}
      {activeAudioUrl && (
        <div className="sticky top-20 z-40 bg-paper  p-4 rounded-lg border border-line  ">
          <div className="flex items-center justify-between pb-2">
            <span className="text-xs font-semibold text-ink ">Now Playing</span>
            <button
              onClick={() => setActiveAudioUrl(null)}
              className="text-xs text-muted hover:text-ink "
            >
              Close
            </button>
          </div>
          <AudioPlayer src={activeAudioUrl} autoPlay={true} />
        </div>
      )}

      {/* Table / List */}
      {loading ? (
        <div className="py-24 text-center space-y-3">
          <Loader2 className="h-8 w-8 animate-spin mx-auto text-muted" />
          <p className="text-sm text-muted">Loading generation history...</p>
        </div>
      ) : generations.length === 0 ? (
        <div className="empty-state">
          <History className="h-10 w-10 text-muted mx-auto" />
          <div>
            <h3 className="font-semibold text-base text-ink ">No generations found</h3>
            <p className="text-xs text-muted max-w-sm mx-auto mt-1">
              Synthesize speech in Voice Studio to see your completed audio files and downloads here.
            </p>
          </div>
          <Link
            href="/studio"
            className="inline-flex items-center gap-2 px-4 py-2 rounded-md bg-accent  text-white  text-xs font-medium hover:bg-soft transition-colors "
          >
            Go to Voice Studio
          </Link>
        </div>
      ) : (
        <div className="history-list">
          <div className="divide-y divide-line ">
            {generations.map((gen, index) => (
              <div
                key={gen.id}
                className="history-entry"
              >
                <span className="history-index">{String(index + 1).padStart(2, "0")}</span>
                <div className="min-w-0">
                  <div className="history-meta">
                    <span className="font-medium text-xs text-ink  bg-soft  px-2.5 py-0.5 rounded-full">
                      {voices[gen.voice_id] || "Cloned Voice"}
                    </span>
                    <span className="text-[11px] font-mono text-muted">
                      {new Date(gen.created_at).toLocaleString()}
                    </span>
                    <span className="text-[11px] font-mono text-muted">
                      {gen.character_count} chars
                    </span>
                    {gen.is_watermarked && (
                      <span className="inline-flex items-center gap-1 font-mono text-[10px] text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800 px-2 py-0.5 rounded-full font-semibold">
                        <Shield className="h-2.5 w-2.5" />
                        C2PA Signed
                      </span>
                    )}
                  </div>

                  <p className="history-text line-clamp-2">
                    {gen.input_text}
                  </p>

                  {gen.local_file_path && (
                    <div className="flex items-center gap-1.5 pt-0.5 text-[11px] font-mono text-muted ">
                      <FolderOpen className="h-3 w-3 shrink-0" />
                      <span className="truncate max-w-lg select-all">{gen.local_file_path}</span>
                    </div>
                  )}
                </div>

                <div className="flex items-center gap-2 shrink-0">
                  {gen.audio_url && (
                    <>
                      <button
                        onClick={() => setActiveAudioUrl(gen.audio_url || null)}
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-accent  text-white  text-xs font-medium hover:bg-soft transition-colors "
                      >
                        <Play className="h-3 w-3 fill-current" />
                        <span>Play</span>
                      </button>

                      <button
                        type="button"
                        onClick={() => handleDownload(gen)}
                        disabled={downloadingId === gen.id}
                        className="p-2 rounded-lg text-muted hover:text-ink  hover:bg-soft  transition-colors disabled:opacity-50"
                        title="Download MP3 directly to your computer"
                      >
                        {downloadingId === gen.id ? (
                          <Loader2 className="h-4 w-4 animate-spin text-ink " />
                        ) : (
                          <Download className="h-4 w-4" />
                        )}
                      </button>

                      <button
                        type="button"
                        onClick={() => handleCopy(gen.audio_url || "", `url-${gen.id}`)}
                        className="p-2 rounded-lg text-muted hover:text-ink  hover:bg-soft  transition-colors"
                        title="Copy direct audio URL"
                      >
                        {copiedAction === `url-${gen.id}` ? (
                          <Check className="h-4 w-4 text-emerald-500" />
                        ) : (
                          <LinkIcon className="h-4 w-4" />
                        )}
                      </button>

                      {gen.local_file_path && (
                        <button
                          type="button"
                          onClick={() => handleCopy(gen.local_file_path || "", `path-${gen.id}`)}
                          className="p-2 rounded-lg text-muted hover:text-ink  hover:bg-soft  transition-colors"
                          title="Copy local Mac path"
                        >
                          {copiedAction === `path-${gen.id}` ? (
                            <Check className="h-4 w-4 text-emerald-500" />
                          ) : (
                            <Copy className="h-4 w-4" />
                          )}
                        </button>
                      )}
                    </>
                  )}

                  <button
                    onClick={() => {
                      setGenToDelete(gen);
                      setDeleteError(null);
                    }}
                    className="p-2 rounded-lg text-muted hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-950/40 transition-colors"
                    title="Delete generation"
                    aria-label="Delete generation"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Delete Confirmation Dialog */}
      <ConfirmDialog
        isOpen={!!genToDelete}
        title="Delete Recording"
        description={
          deleteError
            ? `Error deleting recording: ${deleteError}`
            : "Are you sure you want to delete this generation? This will permanently remove this audio recording and its provenance record from your device."
        }
        confirmLabel="Delete Recording"
        isLoading={isDeleting}
        onConfirm={handleConfirmDelete}
        onCancel={() => {
          if (!isDeleting) {
            setGenToDelete(null);
            setDeleteError(null);
          }
        }}
      />
    </div>
  );
}
