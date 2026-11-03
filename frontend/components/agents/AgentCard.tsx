"use client";

import { useState } from "react";
import Link from "next/link";
import { Bot, Mic, PhoneCall, Trash2, User } from "lucide-react";
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
    <div className="flex flex-col justify-between p-6 rounded-2xl border border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-900 shadow-xs hover:shadow-md transition-shadow">
      <div>
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-xl bg-neutral-900 dark:bg-white text-white dark:text-neutral-900 flex items-center justify-center shadow-xs">
              <Bot className="h-5 w-5" />
            </div>
            <div>
              <h4 className="font-semibold text-neutral-900 dark:text-white line-clamp-1">{agent.name}</h4>
              <p className="text-xs text-neutral-500 line-clamp-1">{agent.description || "Voice Agent"}</p>
            </div>
          </div>

          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800">
            Active
          </span>
        </div>

        {/* Assigned voice info */}
        <div className="mt-4 p-3 rounded-xl bg-neutral-50 dark:bg-neutral-800/50 border border-neutral-200/60 dark:border-neutral-700/60 flex items-center justify-between text-xs">
          <div className="flex items-center gap-2 text-neutral-600 dark:text-neutral-300">
            <Mic className="h-3.5 w-3.5 text-neutral-500" />
            <span className="font-medium">{voiceName}</span>
          </div>
          <span className="text-neutral-500 uppercase">{agent.language}</span>
        </div>

        {/* Prompt snippet */}
        <div className="mt-3">
          <p className="text-xs text-neutral-500 line-clamp-2 italic">
            &ldquo;{agent.system_prompt}&rdquo;
          </p>
        </div>
      </div>

      <div className="mt-6 pt-4 border-t border-neutral-100 dark:border-neutral-800 flex items-center justify-between">
        <Link
          href={`/agents/${agent.id}/playground`}
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-neutral-900 dark:bg-white text-white dark:text-neutral-900 text-xs font-medium hover:bg-neutral-800 dark:hover:bg-neutral-100 transition-colors shadow-xs"
        >
          <PhoneCall className="h-3.5 w-3.5" />
          <span>Launch Playground</span>
        </Link>

        <button
          onClick={handleDelete}
          disabled={isDeleting}
          title="Delete agent"
          className="p-2 rounded-lg text-neutral-400 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-950/40 transition-colors"
        >
          <Trash2 className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}
