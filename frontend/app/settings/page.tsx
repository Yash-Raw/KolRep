"use client";

import { useEffect, useState } from "react";
import { CheckCircle2, Shield, Trash2, Key, Database, Server, Info } from "lucide-react";
import { clearAuthToken } from "@/lib/api";

export default function SettingsPage() {
  const [backendStatus, setBackendStatus] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000"}/api/v1/health`)
      .then((res) => res.json())
      .then((data) => setBackendStatus(data))
      .catch(() => setBackendStatus({ status: "offline" }))
      .finally(() => setLoading(false));
  }, []);

  const handleClearSession = () => {
    if (confirm("Reset current browser session and clear stored tokens?")) {
      clearAuthToken();
      window.location.href = "/login";
    }
  };

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-10 w-full space-y-8">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-neutral-900 dark:text-white">Settings</h1>
        <p className="text-sm text-neutral-500 mt-1">Platform connectivity, authentication, and security preferences.</p>
      </div>

      <div className="space-y-6">
        {/* System & Integration Status */}
        <div className="p-6 rounded-3xl border border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-900 shadow-xs space-y-4">
          <div className="flex items-center gap-2.5 pb-2 border-b border-neutral-100 dark:border-neutral-800">
            <Server className="h-5 w-5 text-neutral-500" />
            <h3 className="font-semibold text-base text-neutral-900 dark:text-white">System Infrastructure & Connectivity</h3>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-2">
            <div className="p-4 rounded-2xl bg-neutral-50 dark:bg-neutral-800/50 border border-neutral-200/60 dark:border-neutral-700/60 space-y-1">
              <span className="text-xs text-neutral-500 font-medium">FastAPI Backend</span>
              <p className="font-semibold text-sm capitalize text-emerald-600 dark:text-emerald-400 flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
                {backendStatus?.status === "ok" ? "Connected (v1.0.0)" : "Degraded / Offline"}
              </p>
            </div>

            <div className="p-4 rounded-2xl bg-neutral-50 dark:bg-neutral-800/50 border border-neutral-200/60 dark:border-neutral-700/60 space-y-1">
              <span className="text-xs text-neutral-500 font-medium">PostgreSQL Database</span>
              <p className="font-semibold text-sm capitalize text-emerald-600 dark:text-emerald-400 flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
                {backendStatus?.database === "healthy" ? "Healthy (Supabase PG)" : "Checking"}
              </p>
            </div>

            <div className="p-4 rounded-2xl bg-neutral-50 dark:bg-neutral-800/50 border border-neutral-200/60 dark:border-neutral-700/60 space-y-1">
              <span className="text-xs text-neutral-500 font-medium">Redis / ARQ Worker</span>
              <p className="font-semibold text-sm capitalize text-emerald-600 dark:text-emerald-400 flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
                {backendStatus?.redis === "healthy" ? "Healthy" : "Checking"}
              </p>
            </div>
          </div>
        </div>

        {/* Security & Speaker Verification Policy */}
        <div className="p-6 rounded-3xl border border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-900 shadow-xs space-y-4">
          <div className="flex items-center gap-2.5 pb-2 border-b border-neutral-100 dark:border-neutral-800">
            <Shield className="h-5 w-5 text-neutral-500" />
            <h3 className="font-semibold text-base text-neutral-900 dark:text-white">Voice Ownership & Compliance</h3>
          </div>

          <p className="text-xs text-neutral-600 dark:text-neutral-400 leading-relaxed">
            VoiceRep strictly enforces speaker verification and affirmative authorization. Synthetic voices generated from authorized recordings are restricted exclusively to your account.
          </p>

          <div className="p-4 rounded-2xl bg-neutral-50 dark:bg-neutral-800/40 border border-neutral-200 dark:border-neutral-700 text-xs text-neutral-600 dark:text-neutral-300 space-y-1">
            <p className="font-semibold text-neutral-900 dark:text-white">Revocation Guarantee:</p>
            <p>
              When you delete a voice in the Voice Library, VoiceRep immediately deletes the remote provider clone from ElevenLabs and terminates all associated conversational agent sessions.
            </p>
          </div>
        </div>

        {/* Data Management & Session Reset */}
        <div className="p-6 rounded-3xl border border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-900 shadow-xs space-y-4">
          <div className="flex items-center gap-2.5 pb-2 border-b border-neutral-100 dark:border-neutral-800">
            <Trash2 className="h-5 w-5 text-red-500" />
            <h3 className="font-semibold text-base text-neutral-900 dark:text-white">Account & Session Management</h3>
          </div>

          <div className="flex items-center justify-between">
            <div>
              <h4 className="text-sm font-semibold text-neutral-900 dark:text-white">Clear Local Session</h4>
              <p className="text-xs text-neutral-500">Signs out current user and clears authorization tokens from localStorage.</p>
            </div>
            <button
              onClick={handleClearSession}
              className="px-4 py-2 rounded-xl border border-neutral-200 dark:border-neutral-800 text-xs font-medium text-neutral-700 dark:text-neutral-300 hover:bg-neutral-100 dark:hover:bg-neutral-800 transition-colors"
            >
              Sign Out
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
