"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { AlertCircle, Check, Copy, Download, FolderOpen, Link as LinkIcon, Loader2, Mic2, Play, RotateCcw, Sparkles, Volume2 } from "lucide-react";
import { PageHeader, SectionTitle } from "@/components/ui/StudioUI";
import { api } from "@/lib/api";
import { Generation, Voice, VoiceSettings } from "@/types";
import { AudioPlayer } from "@/components/audio/AudioPlayer";
import { VoiceSettingsForm } from "@/components/studio/VoiceSettingsForm";
import { copyToClipboard, downloadAudioFile, formatAudioFilename } from "@/lib/download";

const DEFAULT_SAMPLE_TEXT =
  "Welcome to VoiceRep. By replicating verified voices with high precision, you can generate natural sounding studio narration for podcasts, audiobooks, and video voiceovers in seconds.";

export default function StudioPage() {
  const searchParams = useSearchParams();
  const preselectedVoiceId = searchParams.get("voice");

  const [voices, setVoices] = useState<Voice[]>([]);
  const [selectedVoiceId, setSelectedVoiceId] = useState<string>("");
  const [inputText, setInputText] = useState(DEFAULT_SAMPLE_TEXT);
  const [modelId, setModelId] = useState("F5TTS_v1_Base");
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
  const [copiedAction, setCopiedAction] = useState<string | null>(null);
  const [downloadingId, setDownloadingId] = useState<string | null>(null);

  const handleCopy = async (text: string, actionKey: string) => {
    const success = await copyToClipboard(text);
    if (success) {
      setCopiedAction(actionKey);
      setTimeout(() => setCopiedAction(null), 2000);
    }
  };

  const handleDownloadItem = async (gen: Generation) => {
    if (!gen.audio_url || downloadingId) return;
    setDownloadingId(gen.id);
    const voiceName = voices.find((v) => v.id === gen.voice_id)?.name;
    const filename = formatAudioFilename({
      voiceName,
      text: gen.input_text,
      id: gen.id,
    });
    try {
      await downloadAudioFile(gen.audio_url, filename);
    } finally {
      setDownloadingId(null);
    }
  };

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
    <div className="page studio-page">
      <PageHeader number="01" label="Production" title="Voice studio" description="Write the words. Find the delivery. Make it sound like you." />
      {errorMessage && <div role="alert" className="flex items-center gap-2 p-4 mb-6 border border-red-200 bg-red-50 text-sm text-red-700"><AlertCircle size={16} /><span>{errorMessage}</span></div>}
      <div className="studio-layout"><div className="min-w-0">
        <section className="studio-canvas" aria-label="Speech editor">
          <div className="voice-selector"><div className="flex items-center gap-3 min-w-0"><span className="record-mark shrink-0"><Mic2 size={20} strokeWidth={1.5} /></span><div className="min-w-0"><label htmlFor="studio-voice" className="eyebrow block">VOICE PROFILE</label>{loadingVoices ? <span className="text-xs text-muted">Loading voices…</span> : voices.length === 0 ? <span className="text-xs text-amber-700">No ready voices found. Please clone a voice first.</span> : <select id="studio-voice" value={selectedVoiceId} onChange={(e) => setSelectedVoiceId(e.target.value)}>{voices.map(v => <option key={v.id} value={v.id}>{v.name} ({v.language || "English"})</option>)}</select>}</div></div><span className="eyebrow shrink-0">LOCAL TTS</span></div>
          <div className="script-label"><label htmlFor="studio-script" className="eyebrow">01 / YOUR SCRIPT</label><span className="eyebrow">{inputText.length} CHARACTERS</span></div>
          <textarea id="studio-script" rows={8} value={inputText} onChange={(e) => setInputText(e.target.value)} placeholder="Enter text to convert into spoken speech..." className="script-editor" />
          <div className="studio-transport"><button type="button" onClick={() => setInputText("")} className="flex items-center gap-2 text-xs text-muted"><RotateCcw size={13} />Clear script</button><button type="button" onClick={handleGenerate} disabled={isGenerating || !selectedVoiceId || !inputText.trim()} className="btn btn-primary disabled:opacity-50">{isGenerating ? <Loader2 size={16} className="animate-spin" /> : <Sparkles size={16} />}{isGenerating ? "Synthesizing…" : "Generate speech"}</button></div>
        </section>
        {currentGeneration?.audio_url ? (() => {
          const activeVoice = voices.find(v => v.id === currentGeneration.voice_id);
          const formattedFilename = formatAudioFilename({ voiceName: activeVoice?.name, text: currentGeneration.input_text, id: currentGeneration.id });
          return <section className="studio-output panel"><div className="panel-heading"><h2>Generated audio</h2><span className="eyebrow">{currentGeneration.duration_seconds ? `${currentGeneration.duration_seconds.toFixed(1)} SECONDS` : "OUTPUT"}</span></div><div className="panel-body space-y-4"><AudioPlayer src={currentGeneration.audio_url} filename={formattedFilename} autoPlay={true} /><div className="flex flex-wrap gap-2">
            <button type="button" onClick={() => handleDownloadItem(currentGeneration)} disabled={downloadingId === currentGeneration.id} className="btn btn-secondary text-xs">{downloadingId === currentGeneration.id ? <Loader2 size={14} className="animate-spin" /> : <Download size={14} />}Download MP3</button>
            <button type="button" onClick={() => handleCopy(currentGeneration.audio_url || "", `url-${currentGeneration.id}`)} className="btn btn-secondary text-xs">{copiedAction === `url-${currentGeneration.id}` ? <Check size={14} /> : <LinkIcon size={14} />}{copiedAction === `url-${currentGeneration.id}` ? "URL copied" : "Copy audio URL"}</button>
            {currentGeneration.local_file_path && <button type="button" onClick={() => handleCopy(currentGeneration.local_file_path || "", `path-${currentGeneration.id}`)} className="btn btn-secondary text-xs">{copiedAction === `path-${currentGeneration.id}` ? <Check size={14} /> : <Copy size={14} />}{copiedAction === `path-${currentGeneration.id}` ? "Path copied" : "Copy local path"}</button>}
          </div>{currentGeneration.local_file_path && <div className="flex items-center gap-2 text-[10px] text-muted font-mono border-t border-line pt-3"><FolderOpen size={14} className="shrink-0" /><span className="truncate select-all">{currentGeneration.local_file_path}</span></div>}</div></section>;
        })() : <div className="py-8 flex items-center gap-3 text-muted"><Volume2 size={20} strokeWidth={1} /><p className="text-xs">Your generated audio will appear here. Make your first take above.</p></div>}
      </div><aside className="min-w-0"><VoiceSettingsForm settings={settings} onChange={setSettings} modelId={modelId} onModelChange={setModelId} /><section className="recent-takes"><SectionTitle aside={<span className="eyebrow">LAST 10</span>}>Recent takes</SectionTitle>{history.length === 0 ? <p className="py-6 text-xs text-muted">No previous generations recorded.</p> : <div className="max-h-[400px] overflow-y-auto">{history.map(item => <div key={item.id} className="recent-take"><p className="line-clamp-2">{item.input_text}</p><div className="recent-take-footer"><span className="text-muted font-mono">{item.character_count} CHARS</span>{item.audio_url && <div className="flex gap-3"><button onClick={() => setCurrentGeneration(item)} className="flex items-center gap-1"><Play size={11} />Play</button><button onClick={() => handleDownloadItem(item)} disabled={downloadingId === item.id} aria-label="Download take">{downloadingId === item.id ? <Loader2 size={13} className="animate-spin" /> : <Download size={13} />}</button></div>}</div></div>)}</div>}</section></aside></div>
    </div>
  );
}
