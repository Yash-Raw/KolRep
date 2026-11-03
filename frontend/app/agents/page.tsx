"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { AlertCircle, Bot, Loader2, Plus, Sparkles } from "lucide-react";
import { api } from "@/lib/api";
import { Agent, Voice } from "@/types";
import { AgentCard } from "@/components/agents/AgentCard";
import { CreateAgentModal } from "@/components/agents/CreateAgentModal";

export default function AgentsPage() {
  const searchParams = useSearchParams();
  const openNewModal = searchParams.get("new") === "true";
  const initialVoiceId = searchParams.get("voice") || undefined;

  const [agents, setAgents] = useState<Agent[]>([]);
  const [voices, setVoices] = useState<Voice[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(openNewModal);

  useEffect(() => {
    loadAgentsAndVoices();
  }, []);

  const loadAgentsAndVoices = async () => {
    setLoading(true);
    setError(null);
    try {
      const [agentRes, voiceRes] = await Promise.all([
        api.getAgents(),
        api.getVoices(),
      ]);
      setAgents(agentRes.items);
      setVoices(voiceRes.items);
    } catch (err: any) {
      setError(err.message || "Failed to load voice agents.");
    } finally {
      setLoading(false);
    }
  };

  const handleAgentCreated = (newAgent: Agent) => {
    setAgents((prev) => [newAgent, ...prev]);
  };

  const handleDeleteAgent = async (agentId: string) => {
    try {
      await api.deleteAgent(agentId);
      setAgents((prev) => prev.filter((a) => a.id !== agentId));
    } catch (err: any) {
      alert(`Failed to delete agent: ${err.message}`);
    }
  };

  const getVoiceName = (voiceId: string) => {
    const found = voices.find((v) => v.id === voiceId);
    return found ? found.name : "Cloned Voice";
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10 w-full space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-neutral-900 dark:text-white">Voice Agents</h1>
          <p className="text-sm text-neutral-500 mt-1">
            Build and talk with real-time Conversational AI agents speaking with your verified cloned voices.
          </p>
        </div>

        <button
          onClick={() => setIsModalOpen(true)}
          className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-neutral-900 dark:bg-white text-white dark:text-neutral-900 text-sm font-medium hover:bg-neutral-800 dark:hover:bg-neutral-100 transition-colors shadow-xs"
        >
          <Plus className="h-4 w-4" />
          <span>Create New Agent</span>
        </button>
      </div>

      {error && (
        <div className="flex items-center gap-2 p-4 rounded-xl bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-800 text-sm text-red-600 dark:text-red-400">
          <AlertCircle className="h-4 w-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Grid or Empty State */}
      {loading ? (
        <div className="py-24 text-center space-y-3">
          <Loader2 className="h-8 w-8 animate-spin mx-auto text-neutral-400" />
          <p className="text-sm text-neutral-500">Loading your voice agents...</p>
        </div>
      ) : agents.length === 0 ? (
        <div className="py-20 text-center border-2 border-dashed border-neutral-200 dark:border-neutral-800 rounded-3xl p-8 space-y-4">
          <div className="h-12 w-12 rounded-2xl bg-neutral-100 dark:bg-neutral-800 text-neutral-600 dark:text-neutral-300 flex items-center justify-center mx-auto">
            <Bot className="h-6 w-6" />
          </div>
          <div>
            <h3 className="font-semibold text-base text-neutral-900 dark:text-white">No agents created yet</h3>
            <p className="text-xs text-neutral-500 max-w-sm mx-auto mt-1">
              Select one of your cloned voices, give your agent instructions, and talk to it in real time.
            </p>
          </div>
          <button
            onClick={() => setIsModalOpen(true)}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-neutral-900 dark:bg-white text-white dark:text-neutral-900 text-xs font-medium hover:bg-neutral-800 dark:hover:bg-neutral-100 transition-colors shadow-xs"
          >
            <Plus className="h-3.5 w-3.5" />
            <span>Create First Agent</span>
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {agents.map((agent) => (
            <AgentCard
              key={agent.id}
              agent={agent}
              voiceName={getVoiceName(agent.voice_id)}
              onDelete={handleDeleteAgent}
            />
          ))}
        </div>
      )}

      {/* Modal */}
      <CreateAgentModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onSuccess={handleAgentCreated}
        initialVoiceId={initialVoiceId}
      />
    </div>
  );
}
