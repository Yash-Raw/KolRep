"use client";

import { useState } from "react";
import Link from "next/link";
import { Bot, CheckCircle2, Clock, Edit2, Sparkles, Trash2 } from "lucide-react";
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
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-soft  text-muted ">
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
    <article className="voice-sleeve">
      <div className="sleeve-art" aria-hidden="true" />
      <div className="sleeve-content"><h2 className="sleeve-title">{voice.name}</h2><p className="eyebrow">{voice.language || "English"} / VOICE PROFILE</p><div className="sleeve-meta">{getStatusBadge(voice.status)}{voice.audio_duration && <span className="mono">{voice.audio_duration.toFixed(1)}s</span>}</div>{voice.quality_report?.quality && <p className="text-xs text-muted capitalize mt-3">Audio quality: {voice.quality_report.quality}</p>}</div>
      <div className="sleeve-actions"><div className="flex flex-wrap gap-2">{voice.status === "ready" && <><Link href={`/studio?voice=${voice.id}`} className="flex items-center gap-1.5 text-xs font-medium text-accent"><Sparkles size={13} />Use in studio</Link><Link href={`/agents?new=true&voice=${voice.id}`} className="flex items-center gap-1.5 text-xs font-medium"><Bot size={13} />Assign agent</Link></>}</div><div className="flex gap-1"><button onClick={() => onRename(voice)} title="Rename voice" aria-label={`Rename ${voice.name}`} className="p-2 text-muted hover:text-ink"><Edit2 size={14} /></button><button onClick={handleDeleteClick} disabled={isDeleting} title="Delete voice" aria-label={`Delete ${voice.name}`} className="p-2 text-muted hover:text-red-600"><Trash2 size={14} /></button></div></div>
    </article>
  );
}
