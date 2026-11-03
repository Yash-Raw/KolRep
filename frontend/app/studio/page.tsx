"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import {
  AlertCircle,
  Download,
  History,
  Loader2,
  Mic2,
  Play,
  RotateCcw,
  Sparkles,
  Volume2,
} from "lucide-react";
import { api } from "@/lib/api";
import { Generation, Voice, VoiceSettings } from "@/types";
import { AudioPlayer } from "@/components/audio/AudioPlayer";
import { VoiceSettingsForm } from "@/components/studio/VoiceSettingsForm";

const DEFAULT_SAMPLE_TEXT =
  "Welcome to VoiceRep. By replicating verified voices with high precision, you can generate natural sounding studio narration for podcasts, audiobooks, and video voiceovers in seconds.";

export default function StudioPage() {
  const searchParams = useSearchParams();
  const preselectedVoiceId = searchParams.get("voice");

  const [voices, setVoices] = useState<Voice[]>([]);
  const [selectedVoiceId, setSelectedVoiceId] = useState<string>("");
  const [inputText, setInputText] = useState(DEFAULT_SAMPLE_TEXT);
  const [modelId, setModelId] = useState("eleven_multilingual_v2");
  const [settings, setSettings] = useState<VoiceSettings>({
    stability: 0.5,
    similarity_boost: 0.75,
    speed: 1.0,
    style: 0.0,
  });

  const [isGenerating, setIsGenerating] = useState(false);
  const [currentGeneration, setCurrentGeneration] = useState<Generation | null>(null);
  const [history, setHistory] = useState<Generation[]>([]);
  const [loadingVoices, setLoadingVoices] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    loadVoicesAndHistory();
  }, []);

  const loadVoicesAndHistory = async () => {
    setLoadingVoices(true);
    try {
      const [voicesRes, genRes] = await Promise.all([
        api.getVoices(),
        api.getGenerations(1, 10),
      ]);

      const readyVoices = voicesRes.items.filter((v) => v.status === "ready");
      setVoices(readyVoices);
      setHistory(genRes.items);

      if (preselectedVoiceId && readyVoices.some((v) => v.id === preselectedVoiceId)) {
        setSelectedVoiceId(preselectedVoiceId);
      } else if (readyVoices.length > 0) {
        setSelectedVoiceId(readyVoices[0].id);
      }
    } catch (err: any) {
      setErrorMessage(err.message || "Failed to load studio data.");
    } finally {
      setLoadingVoices(false);
    }
  };

  const handleGenerate = async () => {
    if (!selectedVoiceId) {
      setErrorMessage("Please select a ready voice before generating.");
      return;
    }
    if (!inputText.trim()) {
      setErrorMessage("Please enter text to generate speech.");
      return;
    }

    setIsGenerating(true);
    setErrorMessage(null);

    try {
      const result = await api.createGeneration({
        voice_id: selectedVoiceId,
        input_text: inputText.trim(),
        model_id: modelId,
        voice_settings: settings,
      });

      setCurrentGeneration(result);
      setHistory((prev) => [result, ...prev]);
    } catch (err: any) {
      setErrorMessage(err.message || "Speech synthesis failed.");
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10 w-full space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-neutral-900 dark:text-white">Voice Studio</h1>
        <p className="text-sm text-neutral-500 mt-1">
          Synthesize lifelike speech using your cloned voice profiles with precision acoustic controls.
        </p>
      </div>

      {errorMessage && (
        <div className="flex items-center gap-2 p-4 rounded-xl bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-800 text-sm text-red-600 dark:text-red-400">
          <AlertCircle className="h-4 w-4 shrink-0" />
          <span>{errorMessage}</span>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Main Text Editor & Generation Area */}
        <div className="lg:col-span-2 space-y-6">
          {/* Voice Selector Bar */}
          <div className="p-4 rounded-2xl border border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-900 flex flex-col sm:flex-row sm:items-center justify-between gap-3 shadow-xs">
            <div className="flex items-center gap-3">
              <div className="h-9 w-9 rounded-xl bg-neutral-100 dark:bg-neutral-800 flex items-center justify-center text-neutral-700 dark:text-neutral-300">
                <Mic2 className="h-4 w-4" />
              </div>
              <div className="min-w-0">
                <label className="text-xs text-neutral-500 block">Selected Voice Profile</label>
                {loadingVoices ? (
                  <span className="text-xs text-neutral-400">Loading voices...</span>
                ) : voices.length === 0 ? (
                  <span className="text-xs text-amber-600 dark:text-amber-400 font-medium">
                    No ready voices found. Please clone a voice first.
                  </span>
                ) : (
                  <select
                    value={selectedVoiceId}
                    onChange={(e) => setSelectedVoiceId(e.target.value)}
                    className="font-semibold text-sm bg-transparent border-0 p-0 text-neutral-900 dark:text-white focus:ring-0 cursor-pointer"
                  >
                    {voices.map((v) => (
                      <option key={v.id} value={v.id} className="bg-white dark:bg-neutral-900">
                        {v.name} ({v.language || "English"})
                      </option>
                    ))}
                  </select>
                )}
              </div>
            </div>

            <div className="text-xs font-mono text-neutral-500">
              {inputText.length} characters
            </div>
          </div>

          {/* Text Editor Box */}
          <div className="relative rounded-2xl border border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-900 shadow-xs overflow-hidden">
            <textarea
              rows={8}
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              placeholder="Enter text to convert into spoken speech..."
              className="w-full p-6 bg-transparent text-neutral-900 dark:text-white text-base leading-relaxed placeholder:text-neutral-400 focus:outline-hidden resize-y min-h-[200px]"
            />

            <div className="p-4 border-t border-neutral-100 dark:border-neutral-800 bg-neutral-50/50 dark:bg-neutral-900/50 flex items-center justify-between">
              <button
                type="button"
                onClick={() => setInputText("")}
                className="text-xs text-neutral-500 hover:text-neutral-900 dark:hover:text-white flex items-center gap-1.5"
              >
                <RotateCcw className="h-3 w-3" />
                <span>Clear</span>
              </button>

              <button
                type="button"
                onClick={handleGenerate}
                disabled={isGenerating || !selectedVoiceId || !inputText.trim()}
                className="flex items-center gap-2 px-6 py-2.5 rounded-xl bg-neutral-900 dark:bg-white text-white dark:text-neutral-900 text-sm font-medium hover:bg-neutral-800 dark:hover:bg-neutral-100 disabled:opacity-50 transition-all shadow-sm"
              >
                {isGenerating ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    <span>Synthesizing...</span>
                  </>
                ) : (
                  <>
                    <Sparkles className="h-4 w-4" />
                    <span>Generate Speech</span>
                  </>
                )}
              </button>
            </div>
          </div>

          {/* Active Audio Player Output */}
          {currentGeneration?.audio_url && (
            <div className="p-6 rounded-2xl border border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-900 shadow-sm space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
                  <h4 className="font-semibold text-sm text-neutral-900 dark:text-white">Generated Audio</h4>
                </div>
                {currentGeneration.duration_seconds && (
                  <span className="text-xs font-mono text-neutral-500">
                    Duration: {currentGeneration.duration_seconds.toFixed(1)}s
                  </span>
                )}
              </div>

              <AudioPlayer
                src={currentGeneration.audio_url}
                filename={`generation_${currentGeneration.id.slice(0, 8)}.mp3`}
                autoPlay={true}
              />
            </div>
          )}
        </div>

        {/* Sidebar: Acoustic Settings & Recent History */}
        <div className="space-y-6">
          <VoiceSettingsForm
            settings={settings}
            onChange={setSettings}
            modelId={modelId}
            onModelChange={setModelId}
          />

          {/* Generation History Drawer */}
          <div className="p-5 rounded-2xl border border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-900 space-y-3">
            <div className="flex items-center justify-between pb-2 border-b border-neutral-100 dark:border-neutral-800">
              <div className="flex items-center gap-2">
                <History className="h-4 w-4 text-neutral-500" />
                <h4 className="font-semibold text-xs text-neutral-900 dark:text-white uppercase tracking-wider">
                  Recent Studio Generations
                </h4>
              </div>
            </div>

            {history.length === 0 ? (
              <p className="text-xs text-neutral-400 py-4 text-center">No previous generations recorded.</p>
            ) : (
              <div className="space-y-2.5 max-h-[360px] overflow-y-auto">
                {history.map((item) => (
                  <div
                    key={item.id}
                    className="p-3 rounded-xl border border-neutral-100 dark:border-neutral-800 bg-neutral-50/50 dark:bg-neutral-800/40 text-xs space-y-2"
                  >
                    <p className="text-neutral-700 dark:text-neutral-300 line-clamp-2 italic">
                      &ldquo;{item.input_text}&rdquo;
                    </p>
                    <div className="flex items-center justify-between pt-1 border-t border-neutral-200/40 dark:border-neutral-700/40 text-[11px] text-neutral-500">
                      <span>{item.character_count} chars</span>
                      {item.audio_url && (
                        <button
                          onClick={() => setCurrentGeneration(item)}
                          className="font-medium text-neutral-900 dark:text-white flex items-center gap-1 hover:underline"
                        >
                          <Play className="h-3 w-3 fill-current" />
                          <span>Play</span>
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
