import {
  Generation,
  UsageStats,
  VerificationReport,
  Voice,
  VoiceSettings,
} from "@/types";

export function getBackendUrl(): string {
  if (typeof window !== "undefined" && (window as any).__KOLREP_BACKEND_URL__) {
    return (window as any).__KOLREP_BACKEND_URL__;
  }
  return process.env.NEXT_PUBLIC_BACKEND_URL || "http://127.0.0.1:8000";
}

const DEFAULT_DEV_TOKEN =
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMTExMTExMS0xMTExLTExMTEtMTExMS0xMTExMTExMTExMTEiLCJlbWFpbCI6ImRlbW9Aa29scmVwLmxvY2FsIn0.Sp2pIv4Jw_7sEC7oTxSkKKGhZbs1CMhZ5DttDsvrzMM";

export function getAuthToken(): string {
  if (typeof window === "undefined") return DEFAULT_DEV_TOKEN;
  return localStorage.getItem("kolrep_auth_token") || DEFAULT_DEV_TOKEN;
}

export function setAuthToken(token: string): void {
  if (typeof window !== "undefined") {
    localStorage.setItem("kolrep_auth_token", token);
  }
}

export function clearAuthToken(): void {
  if (typeof window !== "undefined") {
    localStorage.removeItem("kolrep_auth_token");
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

  let response: Response;
  try {
    response = await fetch(`${getBackendUrl()}${endpoint}`, {
      ...options,
      headers,
    });
  } catch (err: any) {
    if (err?.message === "Load failed" || err?.message === "Failed to fetch") {
      throw new Error(
        `Unable to reach KolRep backend at ${getBackendUrl()}. Ensure the local engine is active.`
      );
    }
    throw err;
  }

  if (!response.ok) {
    let errorDetail = `Request failed (${response.status})`;
    try {
      const errorJson = await response.json();
      if (typeof errorJson.detail === "string") {
        errorDetail = errorJson.detail;
      } else if (Array.isArray(errorJson.detail)) {
        errorDetail = errorJson.detail.map((e: any) => e.msg || e.message || JSON.stringify(e)).join(", ");
      } else if (typeof errorJson.detail === "object" && errorJson.detail !== null) {
        errorDetail = errorJson.detail.message || JSON.stringify(errorJson.detail);
      } else if (errorJson.message) {
        errorDetail = errorJson.message;
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

  // Usage & Metrics
  getUsage: async (): Promise<UsageStats> => {
    return request<UsageStats>("/api/v1/usage");
  },

  // C2PA & Deepfake Verification
  verifyAudio: async (file: File): Promise<VerificationReport> => {
    const formData = new FormData();
    formData.append("file", file);
    return request<VerificationReport>("/api/v1/verify", {
      method: "POST",
      body: formData,
    });
  },

  getGenerationCertificate: async (generationId: string): Promise<any> => {
    return request<any>(`/api/v1/verify/certificate/${generationId}`);
  },

  getPublicCertificate: async (): Promise<string> => {
    const res = await fetch(`${getBackendUrl()}/api/v1/verify/public-key`);
    return res.text();
  },

  // Desktop System & Models
  getDesktopStatus: async (): Promise<any> => {
    return request<any>("/api/v1/desktop/status");
  },

  triggerModelDownload: async (): Promise<any> => {
    return request<any>("/api/v1/desktop/download-models", {
      method: "POST",
    });
  },

  getModelDownloadStatus: async (): Promise<any> => {
    return request<any>("/api/v1/desktop/download-status");
  },

  getDesktopJobs: async (): Promise<{ jobs: any[] }> => {
    return request<{ jobs: any[] }>("/api/v1/desktop/jobs");
  },

  cancelDesktopJob: async (jobId: string): Promise<any> => {
    return request<any>(`/api/v1/desktop/jobs/${jobId}/cancel`, {
      method: "POST",
    });
  },
};
