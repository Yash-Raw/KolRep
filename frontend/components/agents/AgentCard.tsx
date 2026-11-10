"use client";

import { useState } from "react";
import Link from "next/link";
import { Bot, Mic, PhoneCall, Trash2 } from "lucide-react";
import { Agent, Voice } from "@/types";

interface AgentCardProps {
  agent: Agent;
  voiceName?: string;
  onDelete: (id: string) => void;
}

export function AgentCard({ agent, voiceName = "Cloned Voice", onDelete }: AgentCardProps) {
  const [isDeleting, setIsDeleting] = useState(false);

  const handleDelete = async () => {
    if (confirm(`Are you sure you want to delete voice agent "${agent.name}"?`)) {
      setIsDeleting(true);
      try {
        await onDelete(agent.id);
      } finally {
        setIsDeleting(false);
      }
    }
  };

  return (
    <article className="agent-unit">
      <div className="agent-unit-header"><span className="record-mark"><Bot size={22} strokeWidth={1.5} /></span><span className="status-label text-emerald-700 dark:text-emerald-300">Active</span></div>
      <h2 className="sleeve-title">{agent.name}</h2><p className="text-xs text-muted mb-5">{agent.description || "Voice Agent"}</p>
      <div className="flex justify-between gap-3 border-y border-line py-3 text-xs"><span className="flex items-center gap-2"><Mic size={14} />{voiceName}</span><span className="eyebrow">{agent.language}</span></div>
      <p className="text-xs text-muted line-clamp-2 leading-relaxed my-5">{agent.system_prompt}</p>
      <div className="sleeve-actions"><Link href={`/agents/${agent.id}/playground`} className="flex items-center gap-2 text-xs font-medium text-accent"><PhoneCall size={14} />Launch playground</Link><button onClick={handleDelete} disabled={isDeleting} title="Delete agent" aria-label={`Delete ${agent.name}`} className="p-2 text-muted hover:text-red-600"><Trash2 size={15} /></button></div>
    </article>
  );
}
