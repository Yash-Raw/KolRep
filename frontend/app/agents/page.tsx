"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { AlertCircle, Bot, Loader2, Plus, Sparkles } from "lucide-react";
import { PageHeader } from "@/components/ui/StudioUI";
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
    <div className="page agents-page">
      <PageHeader number="04" label="Conversational tools" title="Voice agents" description="Give your voice a new role. Configure agents with your existing voice profiles." actions={<button onClick={() => setIsModalOpen(true)} className="btn btn-primary"><Plus size={16} />Create an agent</button>} />

      {/* v1.1 Milestone Notice */}
      <div className="flex items-center gap-3 mb-6 p-4 rounded-md border border-amber-200 dark:border-amber-800 bg-amber-50/70 dark:bg-amber-950/30 text-amber-900 dark:text-amber-200 text-sm">
        <Sparkles className="h-5 w-5 shrink-0 text-amber-600 dark:text-amber-400" />
        <div>
          <span className="font-semibold">v1.1 Milestone Preview:</span> The full-duplex conversational voice agent engine is queued for the v1.1 release. Instant Voice Cloning and Studio Narration are fully active and 100% self-hosted in v1.0.
        </div>
      </div>

      {error && (
        <div className="flex items-center gap-2 p-4 rounded-md bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-800 text-sm text-red-600 dark:text-red-400">
          <AlertCircle className="h-4 w-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Grid or Empty State */}
      {loading ? (
        <div className="py-24 text-center space-y-3">
          <Loader2 className="h-8 w-8 animate-spin mx-auto text-muted" />
          <p className="text-sm text-muted">Loading your voice agents...</p>
        </div>
      ) : agents.length === 0 ? (
        <div className="empty-state">
          <div className="h-12 w-12 rounded-lg bg-soft  text-muted  flex items-center justify-center mx-auto">
            <Bot className="h-6 w-6" />
          </div>
          <div>
            <h3 className="font-semibold text-base text-ink ">No agents created yet</h3>
            <p className="text-xs text-muted max-w-sm mx-auto mt-1">
              Select one of your cloned voices, give your agent instructions, and talk to it in real time.
            </p>
          </div>
          <button
            onClick={() => setIsModalOpen(true)}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-md bg-accent  text-white  text-xs font-medium hover:bg-soft  transition-colors "
          >
            <Plus className="h-3.5 w-3.5" />
            <span>Create First Agent</span>
          </button>
        </div>
      ) : (
        <div className="library-grid">
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
