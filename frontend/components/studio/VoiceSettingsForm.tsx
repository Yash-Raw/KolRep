"use client";

import { SlidersHorizontal } from "lucide-react";
import { VoiceSettings } from "@/types";

interface VoiceSettingsFormProps {
  settings: VoiceSettings;
  onChange: (newSettings: VoiceSettings) => void;
  modelId: string;
  onModelChange: (modelId: string) => void;
}

export function VoiceSettingsForm({
  settings,
  onChange,
  modelId,
  onModelChange,
}: VoiceSettingsFormProps) {
  const updateField = (field: keyof VoiceSettings, value: number) => {
    onChange({
      ...settings,
      [field]: value,
    });
  };

  return (
    <section className="inspector" aria-label="Acoustic and model settings">
      <div className="inspector-heading"><h2>Delivery controls</h2><SlidersHorizontal size={15} className="text-muted" /></div>
      <div className="parameter"><label htmlFor="generation-model" className="eyebrow">GENERATION MODEL</label><select id="generation-model" value={modelId} onChange={(e) => onModelChange(e.target.value)} className="model-select"><option value="F5TTS_v1_Base">F5-TTS Base · Local</option><option value="F5TTS_v1_Fast">F5-TTS Fast · 16-step</option></select></div>
      {([
        { field: "stability", label: "Stability", min: 0, max: 1, low: "More expressive", high: "More consistent" },
        { field: "similarity_boost", label: "Similarity boost", min: 0, max: 1, low: "Low", high: "High fidelity" },
        { field: "speed", label: "Speaking speed", min: .5, max: 2, low: "0.5× slow", high: "2.0× fast" },
        { field: "style", label: "Style exaggeration", min: 0, max: 1, low: "Natural", high: "Exaggerated" },
      ] as const).map(({ field, label, min, max, low, high }) => <div className="parameter" key={field}><div className="parameter-top"><label htmlFor={`parameter-${field}`}>{label}</label><span className="parameter-value">{settings[field].toFixed(2)}{field === "speed" ? "×" : ""}</span></div><input id={`parameter-${field}`} type="range" min={min} max={max} step="0.05" value={settings[field]} onChange={(e) => updateField(field, parseFloat(e.target.value))} className="console-range" /><div className="parameter-endpoints"><span>{low}</span><span>{high}</span></div></div>)}
    </section>
  );
}
