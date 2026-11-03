"use client";

import { useEffect, useState } from "react";
import { AlertCircle, Bot, Loader2, X } from "lucide-react";
import { api } from "@/lib/api";
import { Agent, Voice } from "@/types";

interface CreateAgentModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (newAgent: Agent) => void;
  initialVoiceId?: string;
}

export function CreateAgentModal({
  isOpen,
  onClose,
  onSuccess,
  initialVoiceId,
}: CreateAgentModalProps) {
  const [voices, setVoices] = useState<Voice[]>([]);
  const [loadingVoices, setLoadingVoices] = useState(false);
  const [name, setName] = useState("");
  const [voiceId, setVoiceId] = useState(initialVoiceId || "");
  const [description, setDescription] = useState("");
  const [systemPrompt, setSystemPrompt] = useState(
    "You are a helpful, concise AI voice assistant. Speak naturally, be engaging, and provide direct answers."
  );
  const [firstMessage, setFirstMessage] = useState(
    "Hello! How can I help you today?"
  );
  const [language, setLanguage] = useState("en");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen) {
      loadVoices();
      if (initialVoiceId) {
        setVoiceId(initialVoiceId);
      }
    }
  }, [isOpen, initialVoiceId]);

  const loadVoices = async () => {
    setLoadingVoices(true);
    try {
      const res = await api.getVoices();
      const ready = res.items.filter((v) => v.status === "ready");
      setVoices(ready);
      if (!voiceId && ready.length > 0) {
        setVoiceId(ready[0].id);
      }
    } catch (err: any) {
      setErrorMessage(err.message || "Failed to load voices");
    } finally {
      setLoadingVoices(false);
    }
  };

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) {
      setErrorMessage("Please enter an agent name.");
      return;
    }
    if (!voiceId) {
      setErrorMessage("Please select a ready cloned voice for this agent.");
      return;
    }
    if (!systemPrompt.trim()) {
      setErrorMessage("Please provide system instructions.");
      return;
    }

    setIsSubmitting(true);
    setErrorMessage(null);

    try {
      const created = await api.createAgent({
        name: name.trim(),
        voice_id: voiceId,
        description: description.trim() || undefined,
        system_prompt: systemPrompt.trim(),
        first_message: firstMessage.trim(),
        language,
      });
      onSuccess(created);
      onClose();
    } catch (err: any) {
      setErrorMessage(err.message || "Failed to create agent.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4">
      <div className="w-full max-w-lg bg-white dark:bg-neutral-900 border border-neutral-200 dark:border-neutral-800 rounded-2xl shadow-xl overflow-hidden animate-in fade-in zoom-in-95 duration-150">
        <div className="flex items-center justify-between px-6 py-4 border-b border-neutral-200 dark:border-neutral-800">
          <div className="flex items-center gap-2.5">
            <div className="h-8 w-8 rounded-lg bg-neutral-900 dark:bg-white text-white dark:text-neutral-900 flex items-center justify-center">
              <Bot className="h-4 w-4" />
            </div>
            <h3 className="font-semibold text-lg text-neutral-900 dark:text-white">Create Voice Agent</h3>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-neutral-400 hover:text-neutral-900 dark:hover:text-white hover:bg-neutral-100 dark:hover:bg-neutral-800 transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {errorMessage && (
            <div className="flex items-center gap-2 p-3 rounded-lg bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-800 text-sm text-red-600 dark:text-red-400">
              <AlertCircle className="h-4 w-4 shrink-0" />
              <span>{errorMessage}</span>
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1">
              Agent Name
            </label>
            <input
              type="text"
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Research Specialist, Customer Companion"
              className="w-full px-3.5 py-2.5 rounded-lg border border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-950 text-neutral-900 dark:text-white text-sm focus:outline-hidden focus:ring-2 focus:ring-neutral-900 dark:focus:ring-white"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1">
              Assigned Cloned Voice
            </label>
            {loadingVoices ? (
              <div className="py-2 flex items-center gap-2 text-xs text-neutral-500">
                <Loader2 className="h-3 w-3 animate-spin" /> Loading voice library...
              </div>
            ) : voices.length === 0 ? (
              <p className="text-xs text-amber-600 dark:text-amber-400">
                No ready cloned voices found. Please clone a voice first in the Voice Library.
              </p>
            ) : (
              <select
                value={voiceId}
                onChange={(e) => setVoiceId(e.target.value)}
                className="w-full px-3.5 py-2.5 rounded-lg border border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-950 text-neutral-900 dark:text-white text-sm focus:outline-hidden focus:ring-2 focus:ring-neutral-900 dark:focus:ring-white"
              >
                {voices.map((v) => (
                  <option key={v.id} value={v.id}>
                    {v.name} ({v.language || "English"})
                  </option>
                ))}
              </select>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1">
              First Greeting
            </label>
            <input
              type="text"
              required
              value={firstMessage}
              onChange={(e) => setFirstMessage(e.target.value)}
              placeholder="e.g. Hello! What would you like to explore today?"
              className="w-full px-3.5 py-2.5 rounded-lg border border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-950 text-neutral-900 dark:text-white text-sm focus:outline-hidden focus:ring-2 focus:ring-neutral-900 dark:focus:ring-white"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1">
              System Instructions (Prompt)
            </label>
            <textarea
              rows={4}
              required
              value={systemPrompt}
              onChange={(e) => setSystemPrompt(e.target.value)}
              className="w-full px-3.5 py-2.5 rounded-lg border border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-950 text-neutral-900 dark:text-white text-sm focus:outline-hidden focus:ring-2 focus:ring-neutral-900 dark:focus:ring-white"
            />
          </div>

          <div className="flex justify-end gap-3 pt-3">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-white"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting || voices.length === 0}
              className="px-5 py-2.5 rounded-lg bg-neutral-900 dark:bg-white text-white dark:text-neutral-900 text-sm font-medium hover:bg-neutral-800 dark:hover:bg-neutral-100 disabled:opacity-50 transition-colors shadow-sm flex items-center gap-2"
            >
              {isSubmitting && <Loader2 className="h-4 w-4 animate-spin" />}
              <span>Create Agent</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
