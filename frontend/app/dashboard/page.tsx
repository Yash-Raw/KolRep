"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  Activity,
  ArrowRight,
  Bot,
  Clock,
  History,
  Mic2,
  Plus,
  Sparkles,
  Volume2,
} from "lucide-react";
import { api } from "@/lib/api";
import { UsageStats } from "@/types";

export default function DashboardPage() {
  const [stats, setStats] = useState<UsageStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadDashboardData();
  }, []);

  const loadDashboardData = async () => {
    setLoading(true);
    try {
      const data = await api.getUsage();
      setStats(data);
    } catch (err: any) {
      setError(err.message || "Failed to load dashboard metrics");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10 w-full space-y-10">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-neutral-900 dark:text-white">Dashboard</h1>
          <p className="text-sm text-neutral-500 mt-1">Overview of your cloned voices, studio generations, and voice agents.</p>
        </div>

        <div className="flex items-center gap-3">
          <Link
            href="/voices"
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-neutral-900 dark:bg-white text-white dark:text-neutral-900 text-sm font-medium hover:bg-neutral-800 dark:hover:bg-neutral-100 transition-colors shadow-xs"
          >
            <Plus className="h-4 w-4" />
            <span>Clone Voice</span>
          </Link>
          <Link
            href="/studio"
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl border border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-900 text-neutral-900 dark:text-white text-sm font-medium hover:bg-neutral-50 dark:hover:bg-neutral-800 transition-colors shadow-xs"
          >
            <Sparkles className="h-4 w-4" />
            <span>Voice Studio</span>
          </Link>
        </div>
      </div>

      {/* Metrics Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        <div className="p-6 rounded-2xl border border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-900 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-neutral-500 uppercase tracking-wider">Voice Profiles</span>
            <div className="h-9 w-9 rounded-xl bg-neutral-100 dark:bg-neutral-800 flex items-center justify-center text-neutral-700 dark:text-neutral-300">
              <Mic2 className="h-4 w-4" />
            </div>
          </div>
          <div className="mt-4">
            <h3 className="text-3xl font-bold tracking-tight text-neutral-900 dark:text-white">
              {loading ? "—" : stats?.total_voices || 0}
            </h3>
            <p className="text-xs text-neutral-500 mt-1">
              {stats?.ready_voices || 0} active & ready for generation
            </p>
          </div>
        </div>

        <div className="p-6 rounded-2xl border border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-900 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-neutral-500 uppercase tracking-wider">Studio Audio Files</span>
            <div className="h-9 w-9 rounded-xl bg-neutral-100 dark:bg-neutral-800 flex items-center justify-center text-neutral-700 dark:text-neutral-300">
              <Volume2 className="h-4 w-4" />
            </div>
          </div>
          <div className="mt-4">
            <h3 className="text-3xl font-bold tracking-tight text-neutral-900 dark:text-white">
              {loading ? "—" : stats?.total_generations || 0}
            </h3>
            <p className="text-xs text-neutral-500 mt-1">
              {stats?.completed_generations || 0} completed generations
            </p>
          </div>
        </div>

        <div className="p-6 rounded-2xl border border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-900 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-neutral-500 uppercase tracking-wider">Characters Synthesized</span>
            <div className="h-9 w-9 rounded-xl bg-neutral-100 dark:bg-neutral-800 flex items-center justify-center text-neutral-700 dark:text-neutral-300">
              <Sparkles className="h-4 w-4" />
            </div>
          </div>
          <div className="mt-4">
            <h3 className="text-3xl font-bold tracking-tight text-neutral-900 dark:text-white">
              {loading ? "—" : (stats?.total_characters_used || 0).toLocaleString()}
            </h3>
            <p className="text-xs text-neutral-500 mt-1">Characters rendered to speech</p>
          </div>
        </div>

        <div className="p-6 rounded-2xl border border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-900 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-neutral-500 uppercase tracking-wider">Conversational Agents</span>
            <div className="h-9 w-9 rounded-xl bg-neutral-100 dark:bg-neutral-800 flex items-center justify-center text-neutral-700 dark:text-neutral-300">
              <Bot className="h-4 w-4" />
            </div>
          </div>
          <div className="mt-4">
            <h3 className="text-3xl font-bold tracking-tight text-neutral-900 dark:text-white">
              {loading ? "—" : stats?.total_agents || 0}
            </h3>
            <p className="text-xs text-neutral-500 mt-1">
              {stats?.total_sessions || 0} live calls completed
            </p>
          </div>
        </div>
      </div>

      {/* Quick Launch & Recent Activity */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Module Shortcuts */}
        <div className="lg:col-span-1 space-y-4">
          <h3 className="text-base font-semibold text-neutral-900 dark:text-white">Quick Workflows</h3>

          <Link
            href="/voices"
            className="flex items-center justify-between p-4 rounded-2xl border border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-900 hover:border-neutral-300 dark:hover:border-neutral-700 transition-all shadow-xs group"
          >
            <div className="flex items-center gap-3">
              <div className="h-10 w-10 rounded-xl bg-neutral-100 dark:bg-neutral-800 flex items-center justify-center text-neutral-900 dark:text-white">
                <Mic2 className="h-5 w-5" />
              </div>
              <div>
                <h4 className="text-sm font-semibold text-neutral-900 dark:text-white">Voice Library</h4>
                <p className="text-xs text-neutral-500">Upload and verify clone profiles</p>
              </div>
            </div>
            <ArrowRight className="h-4 w-4 text-neutral-400 group-hover:translate-x-1 transition-transform" />
          </Link>

          <Link
            href="/studio"
            className="flex items-center justify-between p-4 rounded-2xl border border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-900 hover:border-neutral-300 dark:hover:border-neutral-700 transition-all shadow-xs group"
          >
            <div className="flex items-center gap-3">
              <div className="h-10 w-10 rounded-xl bg-neutral-100 dark:bg-neutral-800 flex items-center justify-center text-neutral-900 dark:text-white">
                <Sparkles className="h-5 w-5" />
              </div>
              <div>
                <h4 className="text-sm font-semibold text-neutral-900 dark:text-white">Voice Studio</h4>
                <p className="text-xs text-neutral-500">Generate long-form narration</p>
              </div>
            </div>
            <ArrowRight className="h-4 w-4 text-neutral-400 group-hover:translate-x-1 transition-transform" />
          </Link>

          <Link
            href="/agents"
            className="flex items-center justify-between p-4 rounded-2xl border border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-900 hover:border-neutral-300 dark:hover:border-neutral-700 transition-all shadow-xs group"
          >
            <div className="flex items-center gap-3">
              <div className="h-10 w-10 rounded-xl bg-neutral-100 dark:bg-neutral-800 flex items-center justify-center text-neutral-900 dark:text-white">
                <Bot className="h-5 w-5" />
              </div>
              <div>
                <h4 className="text-sm font-semibold text-neutral-900 dark:text-white">Voice Agents</h4>
                <p className="text-xs text-neutral-500">Launch real-time AI conversations</p>
              </div>
            </div>
            <ArrowRight className="h-4 w-4 text-neutral-400 group-hover:translate-x-1 transition-transform" />
          </Link>
        </div>

        {/* Recent Activity Table */}
        <div className="lg:col-span-2 p-6 rounded-2xl border border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-900 shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between pb-4 border-b border-neutral-100 dark:border-neutral-800">
              <h3 className="text-base font-semibold text-neutral-900 dark:text-white">Recent Generations</h3>
              <Link href="/history" className="text-xs font-medium text-neutral-500 hover:text-neutral-900 dark:hover:text-white">
                View all
              </Link>
            </div>

            {loading ? (
              <div className="py-12 text-center text-xs text-neutral-500">Loading activity...</div>
            ) : !stats?.recent_activity || stats.recent_activity.length === 0 ? (
              <div className="py-12 text-center space-y-2">
                <Clock className="h-8 w-8 text-neutral-300 dark:text-neutral-700 mx-auto" />
                <p className="text-sm text-neutral-500">No speech generations yet.</p>
                <Link href="/studio" className="text-xs font-medium text-neutral-900 dark:text-white underline">
                  Create your first generation in Voice Studio
                </Link>
              </div>
            ) : (
              <div className="divide-y divide-neutral-100 dark:divide-neutral-800">
                {stats.recent_activity.map((act) => (
                  <div key={act.id} className="py-3.5 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className="h-8 w-8 rounded-lg bg-neutral-100 dark:bg-neutral-800 flex items-center justify-center text-neutral-700 dark:text-neutral-300">
                        <Volume2 className="h-4 w-4" />
                      </div>
                      <div>
                        <p className="text-xs font-medium text-neutral-900 dark:text-white">
                          Synthesized {act.characters} characters
                        </p>
                        <p className="text-[11px] text-neutral-500">
                          {new Date(act.created_at).toLocaleString()}
                        </p>
                      </div>
                    </div>

                    <span className="text-[11px] font-medium px-2 py-0.5 rounded-full bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-300 capitalize">
                      {act.status}
                    </span>
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
