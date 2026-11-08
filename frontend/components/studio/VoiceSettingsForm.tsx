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
    <div className="p-5 rounded-2xl border border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-900 space-y-5">
      <div className="flex items-center gap-2 pb-3 border-b border-neutral-100 dark:border-neutral-800">
        <SlidersHorizontal className="h-4 w-4 text-neutral-500" />
        <h4 className="font-semibold text-sm text-neutral-900 dark:text-white">Acoustic & Model Settings</h4>
      </div>

      {/* Model Selection */}
      <div className="space-y-1.5">
        <label className="text-xs font-medium text-neutral-700 dark:text-neutral-300">
          Generation Model
        </label>
        <select
          value={modelId}
          onChange={(e) => onModelChange(e.target.value)}
          className="w-full px-3 py-2 rounded-lg border border-neutral-200 dark:border-neutral-800 bg-neutral-50 dark:bg-neutral-950 text-xs font-medium text-neutral-900 dark:text-white focus:outline-hidden"
        >
          <option value="F5TTS_v1_Base">F5-TTS (Self-Hosted Zero-Shot Local Engine)</option>
          <option value="eleven_multilingual_v2">Eleven Multilingual v2 (Cloud High Quality)</option>
          <option value="eleven_turbo_v2_5">Eleven Turbo v2.5 (Cloud Fast / Low Latency)</option>
        </select>
      </div>

      {/* Stability Slider */}
      <div className="space-y-1.5">
        <div className="flex justify-between text-xs">
          <span className="font-medium text-neutral-700 dark:text-neutral-300">Stability</span>
          <span className="font-mono text-neutral-500">{settings.stability.toFixed(2)}</span>
        </div>
        <input
          type="range"
          min="0"
          max="1"
          step="0.05"
          value={settings.stability}
          onChange={(e) => updateField("stability", parseFloat(e.target.value))}
          className="w-full h-1.5 bg-neutral-200 dark:bg-neutral-700 rounded-lg appearance-none cursor-pointer accent-neutral-900 dark:accent-white"
        />
        <div className="flex justify-between text-[10px] text-neutral-400">
          <span>More Expressive</span>
          <span>More Consistent</span>
        </div>
      </div>

      {/* Similarity Boost Slider */}
      <div className="space-y-1.5">
        <div className="flex justify-between text-xs">
          <span className="font-medium text-neutral-700 dark:text-neutral-300">Similarity Boost</span>
          <span className="font-mono text-neutral-500">{settings.similarity_boost.toFixed(2)}</span>
        </div>
        <input
          type="range"
          min="0"
          max="1"
          step="0.05"
          value={settings.similarity_boost}
          onChange={(e) => updateField("similarity_boost", parseFloat(e.target.value))}
          className="w-full h-1.5 bg-neutral-200 dark:bg-neutral-700 rounded-lg appearance-none cursor-pointer accent-neutral-900 dark:accent-white"
        />
        <div className="flex justify-between text-[10px] text-neutral-400">
          <span>Low</span>
          <span>High Fidelity</span>
        </div>
      </div>

      {/* Speed Slider */}
      <div className="space-y-1.5">
        <div className="flex justify-between text-xs">
          <span className="font-medium text-neutral-700 dark:text-neutral-300">Speaking Speed</span>
          <span className="font-mono text-neutral-500">{settings.speed.toFixed(2)}x</span>
        </div>
        <input
          type="range"
          min="0.5"
          max="2.0"
          step="0.05"
          value={settings.speed}
          onChange={(e) => updateField("speed", parseFloat(e.target.value))}
          className="w-full h-1.5 bg-neutral-200 dark:bg-neutral-700 rounded-lg appearance-none cursor-pointer accent-neutral-900 dark:accent-white"
        />
        <div className="flex justify-between text-[10px] text-neutral-400">
          <span>0.5x Slow</span>
          <span>2.0x Fast</span>
        </div>
      </div>

      {/* Style Slider */}
      <div className="space-y-1.5">
        <div className="flex justify-between text-xs">
          <span className="font-medium text-neutral-700 dark:text-neutral-300">Style Exaggeration</span>
          <span className="font-mono text-neutral-500">{settings.style.toFixed(2)}</span>
        </div>
        <input
          type="range"
          min="0"
          max="1"
          step="0.05"
          value={settings.style}
          onChange={(e) => updateField("style", parseFloat(e.target.value))}
          className="w-full h-1.5 bg-neutral-200 dark:bg-neutral-700 rounded-lg appearance-none cursor-pointer accent-neutral-900 dark:accent-white"
        />
        <div className="flex justify-between text-[10px] text-neutral-400">
          <span>Natural</span>
          <span>Exaggerated</span>
        </div>
      </div>
    </div>
  );
}
