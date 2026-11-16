"use client";

import { useEffect, useState } from "react";
import { AlertCircle, Loader2, Mic2, Plus } from "lucide-react";
import { PageHeader } from "@/components/ui/StudioUI";
import { DialogFrame } from "@/components/ui/DialogFrame";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
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
  const [renameError, setRenameError] = useState<string | null>(null);
  const [voiceToDelete, setVoiceToDelete] = useState<Voice | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

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

  const handleConfirmDelete = async () => {
    if (!voiceToDelete) return;
    setIsDeleting(true);
    setDeleteError(null);
    try {
      await api.deleteVoice(voiceToDelete.id);
      setVoices((prev) => prev.filter((v) => v.id !== voiceToDelete.id));
      setVoiceToDelete(null);
    } catch (err: any) {
      setDeleteError(err.message || "Failed to delete voice profile");
    } finally {
      setIsDeleting(false);
    }
  };

  const handleOpenRename = (voice: Voice) => {
    setEditingVoice(voice);
    setNewName(voice.name);
    setRenameError(null);
  };

  const handleSaveRename = async () => {
    if (!editingVoice || !newName.trim()) return;
    setRenameError(null);
    try {
      const updated = await api.updateVoice(editingVoice.id, { name: newName.trim() });
      setVoices((prev) => prev.map((v) => (v.id === updated.id ? updated : v)));
      setEditingVoice(null);
    } catch (err: any) {
      setRenameError(err.message || "Failed to rename voice");
    }
  };

  return (
    <div className="page voices-page">
      <PageHeader number="02" label="Voice collection" title="The voice library" description="A collection of original voices. Ready for your next production." actions={<button onClick={() => setIsModalOpen(true)} className="btn btn-primary"><Plus size={16} />Clone a new voice</button>} />

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
          <p className="text-sm text-muted">Loading your voice profiles...</p>
        </div>
      ) : voices.length === 0 ? (
        <div className="empty-state">
          <div className="h-12 w-12 rounded-lg bg-soft  text-muted  flex items-center justify-center mx-auto">
            <Mic2 className="h-6 w-6" />
          </div>
          <div>
            <h3 className="font-semibold text-base text-ink ">No voice profiles yet</h3>
            <p className="text-xs text-muted max-w-sm mx-auto mt-1">
              Upload a 60-120 second recording of yourself or authorized speaker to create your first voice clone.
            </p>
          </div>
          <button
            onClick={() => setIsModalOpen(true)}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-md bg-accent  text-white  text-xs font-medium hover:bg-soft  transition-colors "
          >
            <Plus className="h-3.5 w-3.5" />
            <span>Clone Voice Now</span>
          </button>
        </div>
      ) : (
        <div className="library-grid">
          {voices.map((voice) => (
            <VoiceCard
              key={voice.id}
              voice={voice}
              onRename={handleOpenRename}
              onDelete={setVoiceToDelete}
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

      {/* Delete Confirmation Dialog */}
      <ConfirmDialog
        isOpen={!!voiceToDelete}
        title="Delete Voice Profile"
        description={
          deleteError
            ? `Error deleting voice: ${deleteError}`
            : `Are you sure you want to permanently delete "${voiceToDelete?.name}"? This will remove its acoustic profile, reference audio, and stored model weights from your device.`
        }
        confirmLabel="Delete Voice"
        isLoading={isDeleting}
        onConfirm={handleConfirmDelete}
        onCancel={() => {
          if (!isDeleting) {
            setVoiceToDelete(null);
            setDeleteError(null);
          }
        }}
      />

      {/* Rename Dialog */}
      {editingVoice && (
        <DialogFrame onClose={() => setEditingVoice(null)}>
          <div className="dialog-panel max-w-md p-6 space-y-4" role="dialog" aria-modal="true" aria-label="Rename voice">
            <h3 className="font-semibold text-lg text-ink ">Rename Voice</h3>
            {renameError && (
              <div className="flex items-center gap-2 p-3 rounded-md bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-800 text-xs text-red-600 dark:text-red-400">
                <AlertCircle className="h-4 w-4 shrink-0" />
                <span>{renameError}</span>
              </div>
            )}
            <input
              aria-label="Voice name"
              type="text"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              className="w-full px-3.5 py-2.5 rounded-lg border border-line  bg-canvas  text-sm focus:outline-hidden focus:ring-2 focus:ring-accent "
            />
            <div className="flex justify-end gap-3 pt-2">
              <button
                onClick={() => setEditingVoice(null)}
                className="px-4 py-2 text-sm text-muted  hover:text-ink"
              >
                Cancel
              </button>
              <button
                onClick={handleSaveRename}
                className="px-4 py-2 rounded-lg bg-accent  text-white  text-sm font-medium hover:bg-soft"
              >
                Save Changes
              </button>
            </div>
          </div>
        </DialogFrame>
      )}
    </div>
  );
}
