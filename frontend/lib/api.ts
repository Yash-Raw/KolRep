import {
  Agent,
  AgentSessionConfig,
  Generation,
  UsageStats,
  Voice,
  VoiceSettings,
} from "@/types";

const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

const DEFAULT_DEV_TOKEN =
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMTExMTExMS0xMTExLTExMTEtMTExMS0xMTExMTExMTExMTEiLCJlbWFpbCI6ImRlbW9Adm9pY2VyZXAubG9jYWwifQ.jl57JKy4e9wZsUXkdw71R5m-1kkTqm3W7HCPGPFvZwQ";

export function getAuthToken(): string {
  if (typeof window === "undefined") return DEFAULT_DEV_TOKEN;
  return localStorage.getItem("voicerep_auth_token") || DEFAULT_DEV_TOKEN;
}

export function setAuthToken(token: string): void {
  if (typeof window !== "undefined") {
    localStorage.setItem("voicerep_auth_token", token);
  }
}

export function clearAuthToken(): void {
  if (typeof window !== "undefined") {
    localStorage.removeItem("voicerep_auth_token");
  }
}

async function request<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getAuthToken();
  const headers = new Headers(options.headers || {});

  if (!headers.has("Authorization") && token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(`${BACKEND_URL}${endpoint}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let errorDetail = `Request failed (${response.status})`;
    try {
      const errorJson = await response.json();
      if (typeof errorJson.detail === "string") {
        errorDetail = errorJson.detail;
      } else if (Array.isArray(errorJson.detail)) {
        errorDetail = errorJson.detail.map((e: any) => e.msg).join(", ");
      }
    } catch {
      errorDetail = await response.text();
    }
    throw new Error(errorDetail || `HTTP error ${response.status}`);
  }

  if (response.status === 204) {
    return {} as T;
  }

  return response.json();
}

export const api = {
  // Voices
  getVoices: async (page = 1, limit = 50): Promise<{ items: Voice[]; total: number }> => {
    return request<{ items: Voice[]; total: number }>(
      `/api/v1/voices?page=${page}&limit=${limit}`
    );
  },

  getVoice: async (id: string): Promise<Voice> => {
    return request<Voice>(`/api/v1/voices/${id}`);
  },

  createVoice: async (formData: FormData): Promise<Voice> => {
    return request<Voice>("/api/v1/voices", {
      method: "POST",
      body: formData,
    });
  },

  updateVoice: async (
    id: string,
    data: { name?: string; language?: string }
  ): Promise<Voice> => {
    return request<Voice>(`/api/v1/voices/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
  },

  deleteVoice: async (id: string): Promise<void> => {
    return request<void>(`/api/v1/voices/${id}`, {
      method: "DELETE",
    });
  },

  // Generations (Voice Studio)
  createGeneration: async (data: {
    voice_id: string;
    input_text: string;
    model_id?: string;
    voice_settings?: VoiceSettings;
  }): Promise<Generation> => {
    return request<Generation>("/api/v1/generations", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
  },

  getGenerations: async (
    page = 1,
    limit = 50
  ): Promise<{ items: Generation[]; total: number }> => {
    return request<{ items: Generation[]; total: number }>(
      `/api/v1/generations?page=${page}&limit=${limit}`
    );
  },

  getGenerationAudioUrl: async (id: string): Promise<{ audio_url: string }> => {
    return request<{ audio_url: string }>(`/api/v1/generations/${id}/audio`);
  },

  deleteGeneration: async (id: string): Promise<void> => {
    return request<void>(`/api/v1/generations/${id}`, {
      method: "DELETE",
    });
  },

  // Voice Agents
  getAgents: async (page = 1, limit = 50): Promise<{ items: Agent[]; total: number }> => {
    return request<{ items: Agent[]; total: number }>(
      `/api/v1/agents?page=${page}&limit=${limit}`
    );
  },

  getAgent: async (id: string): Promise<Agent> => {
    return request<Agent>(`/api/v1/agents/${id}`);
  },

  createAgent: async (data: {
    name: string;
    voice_id: string;
    description?: string;
    system_prompt: string;
    first_message: string;
    language?: string;
  }): Promise<Agent> => {
    return request<Agent>("/api/v1/agents", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
  },

  updateAgent: async (
    id: string,
    data: Partial<{
      name: string;
      voice_id: string;
      description: string;
      system_prompt: string;
      first_message: string;
      language: string;
      status: string;
    }>
  ): Promise<Agent> => {
    return request<Agent>(`/api/v1/agents/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
  },

  deleteAgent: async (id: string): Promise<void> => {
    return request<void>(`/api/v1/agents/${id}`, {
      method: "DELETE",
    });
  },

  startAgentSession: async (agentId: string): Promise<AgentSessionConfig> => {
    return request<AgentSessionConfig>(`/api/v1/agents/${agentId}/session`, {
      method: "POST",
    });
  },

  // Usage & Metrics
  getUsage: async (): Promise<UsageStats> => {
    return request<UsageStats>("/api/v1/usage");
  },
};
