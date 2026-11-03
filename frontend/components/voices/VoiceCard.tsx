"use client";

import { useState } from "react";
import Link from "next/link";
import { Bot, CheckCircle2, Clock, Edit2, Mic, Sparkles, Trash2 } from "lucide-react";
import { Voice } from "@/types";

interface VoiceCardProps {
  voice: Voice;
  onRename: (voice: Voice) => void;
  onDelete: (id: string) => void;
}

export function VoiceCard({ voice, onRename, onDelete }: VoiceCardProps) {
  const [isDeleting, setIsDeleting] = useState(false);

  const getStatusBadge = (status: Voice["status"]) => {
    switch (status) {
      case "ready":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800">
            <CheckCircle2 className="h-3 w-3" />
            Ready
          </span>
        );
      case "cloning":
      case "validating":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-amber-50 dark:bg-amber-950/40 text-amber-700 dark:text-amber-300 border border-amber-200 dark:border-amber-800 animate-pulse">
            <Clock className="h-3 w-3" />
            Processing
          </span>
        );
      case "failed":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-50 dark:bg-red-950/40 text-red-700 dark:text-red-300 border border-red-200 dark:border-red-800">
            Failed
          </span>
        );
      case "verification_required":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-purple-50 dark:bg-purple-950/40 text-purple-700 dark:text-purple-300 border border-purple-200 dark:border-purple-800">
            Verification Required
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-neutral-100 dark:bg-neutral-800 text-neutral-600 dark:text-neutral-400">
            {voice.status}
          </span>
        );
    }
  };

  const handleDeleteClick = async () => {
    if (confirm(`Are you sure you want to permanently delete voice "${voice.name}"?`)) {
      setIsDeleting(true);
      try {
        await onDelete(voice.id);
      } finally {
        setIsDeleting(false);
      }
    }
  };

  return (
    <div className="flex flex-col justify-between p-5 rounded-2xl border border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-900 shadow-xs hover:shadow-md transition-shadow">
      <div>
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-xl bg-neutral-100 dark:bg-neutral-800 flex items-center justify-center text-neutral-900 dark:text-white">
              <Mic className="h-5 w-5" />
            </div>
            <div>
              <h4 className="font-semibold text-neutral-900 dark:text-white line-clamp-1">{voice.name}</h4>
              <p className="text-xs text-neutral-500 capitalize">{voice.language || "English"}</p>
            </div>
          </div>
          {getStatusBadge(voice.status)}
        </div>

        {/* Audio Quality Report Details */}
        {voice.audio_duration && (
          <div className="mt-4 flex items-center gap-4 text-xs text-neutral-500 font-mono">
            <span>Duration: {voice.audio_duration.toFixed(1)}s</span>
            {voice.quality_report?.quality && (
              <span className="capitalize">Quality: {voice.quality_report.quality}</span>
            )}
          </div>
        )}
      </div>

      <div className="mt-5 pt-4 border-t border-neutral-100 dark:border-neutral-800 flex items-center justify-between">
        <div className="flex items-center gap-1.5">
          {voice.status === "ready" && (
            <>
              <Link
                href={`/studio?voice=${voice.id}`}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-neutral-100 dark:bg-neutral-800 text-neutral-900 dark:text-white hover:bg-neutral-200 dark:hover:bg-neutral-700 transition-colors"
              >
                <Sparkles className="h-3.5 w-3.5" />
                <span>Use in Studio</span>
              </Link>
              <Link
                href={`/agents?new=true&voice=${voice.id}`}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-neutral-100 dark:bg-neutral-800 text-neutral-900 dark:text-white hover:bg-neutral-200 dark:hover:bg-neutral-700 transition-colors"
              >
                <Bot className="h-3.5 w-3.5" />
                <span>Assign Agent</span>
              </Link>
            </>
          )}
        </div>

        <div className="flex items-center gap-1">
          <button
            onClick={() => onRename(voice)}
            title="Rename voice"
            className="p-1.5 rounded-lg text-neutral-400 hover:text-neutral-900 dark:hover:text-white hover:bg-neutral-100 dark:hover:bg-neutral-800 transition-colors"
          >
            <Edit2 className="h-4 w-4" />
          </button>
          <button
            onClick={handleDeleteClick}
            disabled={isDeleting}
            title="Delete voice"
            className="p-1.5 rounded-lg text-neutral-400 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-950/40 transition-colors"
          >
            <Trash2 className="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  );
}
