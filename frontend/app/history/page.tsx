"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { AlertCircle, Download, History, Loader2, Play, Sparkles, Trash2, Volume2 } from "lucide-react";
import { api } from "@/lib/api";
import { Generation, Voice } from "@/types";
import { AudioPlayer } from "@/components/audio/AudioPlayer";

export default function HistoryPage() {
  const [generations, setGenerations] = useState<Generation[]>([]);
  const [voices, setVoices] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeAudioUrl, setActiveAudioUrl] = useState<string | null>(null);

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

  const handleDelete = async (id: string) => {
    if (confirm("Are you sure you want to delete this generation?")) {
      try {
        await api.deleteGeneration(id);
        setGenerations((prev) => prev.filter((g) => g.id !== id));
        if (activeAudioUrl) setActiveAudioUrl(null);
      } catch (err: any) {
        alert(`Failed to delete generation: ${err.message}`);
      }
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10 w-full space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-neutral-900 dark:text-white">Generation History</h1>
          <p className="text-sm text-neutral-500 mt-1">
            Browse, listen to, and download all past Voice Studio speech generations.
          </p>
        </div>

        <Link
          href="/studio"
          className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-neutral-900 dark:bg-white text-white dark:text-neutral-900 text-sm font-medium hover:bg-neutral-800 dark:hover:bg-neutral-100 transition-colors shadow-xs"
        >
          <Sparkles className="h-4 w-4" />
          <span>New Studio Generation</span>
        </Link>
      </div>

      {error && (
        <div className="flex items-center gap-2 p-4 rounded-xl bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-800 text-sm text-red-600 dark:text-red-400">
          <AlertCircle className="h-4 w-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Floating Audio Player when active */}
      {activeAudioUrl && (
        <div className="sticky top-20 z-40 bg-white dark:bg-neutral-900 p-4 rounded-2xl border border-neutral-200 dark:border-neutral-800 shadow-lg">
          <div className="flex items-center justify-between pb-2">
            <span className="text-xs font-semibold text-neutral-900 dark:text-white">Now Playing</span>
            <button
              onClick={() => setActiveAudioUrl(null)}
              className="text-xs text-neutral-400 hover:text-neutral-900 dark:hover:text-white"
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
          <Loader2 className="h-8 w-8 animate-spin mx-auto text-neutral-400" />
          <p className="text-sm text-neutral-500">Loading generation history...</p>
        </div>
      ) : generations.length === 0 ? (
        <div className="py-20 text-center border-2 border-dashed border-neutral-200 dark:border-neutral-800 rounded-3xl p-8 space-y-4">
          <History className="h-10 w-10 text-neutral-400 mx-auto" />
          <div>
            <h3 className="font-semibold text-base text-neutral-900 dark:text-white">No generations found</h3>
            <p className="text-xs text-neutral-500 max-w-sm mx-auto mt-1">
              Synthesize speech in Voice Studio to see your completed audio files and downloads here.
            </p>
          </div>
          <Link
            href="/studio"
            className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-neutral-900 dark:bg-white text-white dark:text-neutral-900 text-xs font-medium hover:bg-neutral-800 transition-colors shadow-xs"
          >
            Go to Voice Studio
          </Link>
        </div>
      ) : (
        <div className="rounded-3xl border border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-900 overflow-hidden shadow-xs">
          <div className="divide-y divide-neutral-100 dark:divide-neutral-800">
            {generations.map((gen) => (
              <div
                key={gen.id}
                className="p-5 flex flex-col md:flex-row md:items-center justify-between gap-4 hover:bg-neutral-50/50 dark:hover:bg-neutral-800/30 transition-colors"
              >
                <div className="space-y-1.5 flex-1 min-w-0 pr-4">
                  <div className="flex items-center gap-3">
                    <span className="font-medium text-xs text-neutral-900 dark:text-white bg-neutral-100 dark:bg-neutral-800 px-2.5 py-0.5 rounded-full">
                      {voices[gen.voice_id] || "Cloned Voice"}
                    </span>
                    <span className="text-[11px] font-mono text-neutral-400">
                      {new Date(gen.created_at).toLocaleString()}
                    </span>
                    <span className="text-[11px] font-mono text-neutral-400">
                      {gen.character_count} chars
                    </span>
                  </div>

                  <p className="text-sm text-neutral-700 dark:text-neutral-300 line-clamp-2">
                    {gen.input_text}
                  </p>
                </div>

                <div className="flex items-center gap-3 shrink-0">
                  {gen.audio_url && (
                    <>
                      <button
                        onClick={() => setActiveAudioUrl(gen.audio_url || null)}
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-neutral-900 dark:bg-white text-white dark:text-neutral-900 text-xs font-medium hover:bg-neutral-800 transition-colors"
                      >
                        <Play className="h-3 w-3 fill-current" />
                        <span>Play</span>
                      </button>

                      <a
                        href={gen.audio_url}
                        download={`generation_${gen.id.slice(0, 8)}.mp3`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="p-2 rounded-lg text-neutral-500 hover:text-neutral-900 dark:hover:text-white hover:bg-neutral-100 dark:hover:bg-neutral-800 transition-colors"
                        title="Download audio file"
                      >
                        <Download className="h-4 w-4" />
                      </a>
                    </>
                  )}

                  <button
                    onClick={() => handleDelete(gen.id)}
                    className="p-2 rounded-lg text-neutral-400 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-950/40 transition-colors"
                    title="Delete generation"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
