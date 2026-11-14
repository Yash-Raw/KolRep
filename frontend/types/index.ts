export interface AudioQualityReport {
  duration_seconds: number;
  format: string;
  sample_rate: number;
  channels: number;
  quality: "good" | "acceptable" | "poor";
  speech_ratio?: number;
  has_clipping: boolean;
  warnings: string[];
  recommendation: string;
  is_clonable: boolean;
}

export interface Voice {
  id: string;
  owner_id: string;
  name: string;
  provider: string;
  provider_voice_id?: string;
  status:
    | "upload_pending"
    | "validating"
    | "awaiting_consent"
    | "cloning"
    | "verification_required"
    | "ready"
    | "failed"
    | "deleting"
    | "deleted";
  language?: string;
  audio_duration?: number;
  quality_report?: AudioQualityReport;
  sample_storage_key?: string;
  created_at: string;
  updated_at: string;
}

export interface VoiceConsent {
  id: string;
  voice_id: string;
  owner_id: string;
  speaker_relationship: "self" | "authorized_representative";
  consent_scope: {
    speech_generation: boolean;
    ai_agent?: boolean;
  };
  terms_version: string;
  consent_status: "granted" | "revoked" | "pending";
  consented_at: string;
}

export interface VoiceSettings {
  stability: number;
  similarity_boost: number;
  speed: number;
  style: number;
}

export interface Generation {
  id: string;
  owner_id: string;
  voice_id: string;
  input_text: string;
  model_id: string;
  voice_settings: VoiceSettings;
  status: "queued" | "processing" | "completed" | "failed";
  audio_storage_key?: string;
  audio_url?: string;
  local_file_path?: string;
  character_count: number;
  duration_seconds?: number;
  error_code?: string;
  is_watermarked?: boolean;
  watermark_payload?: Record<string, any>;
  c2pa_manifest?: Record<string, any>;
  created_at: string;
  completed_at?: string;
}

export interface VerificationReport {
  is_authentic: boolean;
  tamper_status: string;
  confidence_score: number;
  c2pa_valid: boolean;
  c2pa_manifest?: Record<string, any>;
  c2pa_error?: string;
  acoustic_watermark_detected: boolean;
  acoustic_payload?: {
    version: number;
    timestamp: number;
    user_hash: string;
    gen_hash: string;
    protocol?: string;
  };
  is_ai_generated: boolean;
  model_id?: string;
  timestamp?: number;
  created_at_iso?: string;
  generation_id?: string;
  user_hash?: string;
  license?: string;
  compliance: string[];
}

export interface UsageStats {
  total_voices: number;
  ready_voices: number;
  total_generations: number;
  completed_generations: number;
  total_characters_used: number;
  recent_activity: Array<{
    type: string;
    id: string;
    status: string;
    characters: number;
    created_at: string;
  }>;
}
