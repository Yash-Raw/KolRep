"use client";

import { useEffect, useState } from "react";
import { AlertCircle, Loader2, Mic2, Plus, Sparkles } from "lucide-react";
import { api } from "@/lib/api";
import { Voice } from "@/types";
import { CreateVoiceModal } from "@/components/voices/CreateVoiceModal";
import { VoiceCard } from "@/components/voices/VoiceCard";

export default function VoicesPage() {
  const [voices, setVoices] = useState<Voice[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingVoice, setEditingVoice] = useState<Voice | null>(null);
  const [newName, setNewName] = useState("");

  useEffect(() => {
    loadVoices();
  }, []);

  const loadVoices = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.getVoices();
      setVoices(res.items);
    } catch (err: any) {
      setError(err.message || "Failed to load voice profiles");
    } finally {
      setLoading(false);
    }
  };

  const handleVoiceCreated = (newVoice: Voice) => {
    setVoices((prev) => [newVoice, ...prev]);
  };

  const handleDeleteVoice = async (voiceId: string) => {
    try {
      await api.deleteVoice(voiceId);
      setVoices((prev) => prev.filter((v) => v.id !== voiceId));
    } catch (err: any) {
      alert(`Failed to delete voice: ${err.message}`);
    }
  };

  const handleOpenRename = (voice: Voice) => {
    setEditingVoice(voice);
    setNewName(voice.name);
  };

  const handleSaveRename = async () => {
    if (!editingVoice || !newName.trim()) return;
    try {
      const updated = await api.updateVoice(editingVoice.id, { name: newName.trim() });
      setVoices((prev) => prev.map((v) => (v.id === updated.id ? updated : v)));
      setEditingVoice(null);
    } catch (err: any) {
      alert(`Failed to rename voice: ${err.message}`);
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10 w-full space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-neutral-900 dark:text-white">Voice Library</h1>
          <p className="text-sm text-neutral-500 mt-1">
            Manage your verified acoustic clones. Upload an authorized sample once to power studio generation and conversational agents.
          </p>
        </div>

        <button
          onClick={() => setIsModalOpen(true)}
          className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-neutral-900 dark:bg-white text-white dark:text-neutral-900 text-sm font-medium hover:bg-neutral-800 dark:hover:bg-neutral-100 transition-colors shadow-xs"
        >
          <Plus className="h-4 w-4" />
          <span>Clone New Voice</span>
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
          <p className="text-sm text-neutral-500">Loading your voice profiles...</p>
        </div>
      ) : voices.length === 0 ? (
        <div className="py-20 text-center border-2 border-dashed border-neutral-200 dark:border-neutral-800 rounded-3xl p-8 space-y-4">
          <div className="h-12 w-12 rounded-2xl bg-neutral-100 dark:bg-neutral-800 text-neutral-600 dark:text-neutral-300 flex items-center justify-center mx-auto">
            <Mic2 className="h-6 w-6" />
          </div>
          <div>
            <h3 className="font-semibold text-base text-neutral-900 dark:text-white">No voice profiles yet</h3>
            <p className="text-xs text-neutral-500 max-w-sm mx-auto mt-1">
              Upload a 60-120 second recording of yourself or authorized speaker to create your first voice clone.
            </p>
          </div>
          <button
            onClick={() => setIsModalOpen(true)}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-neutral-900 dark:bg-white text-white dark:text-neutral-900 text-xs font-medium hover:bg-neutral-800 dark:hover:bg-neutral-100 transition-colors shadow-xs"
          >
            <Plus className="h-3.5 w-3.5" />
            <span>Clone Voice Now</span>
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {voices.map((voice) => (
            <VoiceCard
              key={voice.id}
              voice={voice}
              onRename={handleOpenRename}
              onDelete={handleDeleteVoice}
            />
          ))}
        </div>
      )}

      {/* Voice Creation Modal */}
      <CreateVoiceModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onSuccess={handleVoiceCreated}
      />

      {/* Rename Dialog */}
      {editingVoice && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4">
          <div className="w-full max-w-md bg-white dark:bg-neutral-900 border border-neutral-200 dark:border-neutral-800 rounded-2xl p-6 shadow-xl space-y-4">
            <h3 className="font-semibold text-lg text-neutral-900 dark:text-white">Rename Voice</h3>
            <input
              type="text"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              className="w-full px-3.5 py-2.5 rounded-lg border border-neutral-200 dark:border-neutral-800 bg-neutral-50 dark:bg-neutral-950 text-sm focus:outline-hidden focus:ring-2 focus:ring-neutral-900 dark:focus:ring-white"
            />
            <div className="flex justify-end gap-3 pt-2">
              <button
                onClick={() => setEditingVoice(null)}
                className="px-4 py-2 text-sm text-neutral-600 dark:text-neutral-400 hover:text-neutral-900"
              >
                Cancel
              </button>
              <button
                onClick={handleSaveRename}
                className="px-4 py-2 rounded-lg bg-neutral-900 dark:bg-white text-white dark:text-neutral-900 text-sm font-medium hover:bg-neutral-800"
              >
                Save Changes
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
