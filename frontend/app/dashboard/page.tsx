"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowRight, Bot, History, Mic2, Plus, Sparkles } from "lucide-react";
import { PageHeader, SectionTitle } from "@/components/ui/StudioUI";
import { SignalArt } from "@/components/ui/SignalArt";
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
    <div className="page dashboard-page">
      <PageHeader number="00" label="Workspace" title="Good things start with a voice." description="Your voices, recordings, and creative tools. Ready when you are." actions={<Link href="/voices" className="btn btn-secondary"><Plus size={15} />Clone a voice</Link>} />
      <section className="overview-hero"><div className="overview-hero-copy"><p className="eyebrow">THE VOICE STUDIO</p><h2>Your next recording<br />starts right here.</h2><Link href="/studio" className="btn btn-primary">Open voice studio <ArrowRight size={16} /></Link></div><SignalArt /></section>
      <div className="metrics-strip">
        <div className="metric"><p className="eyebrow">VOICE PROFILES</p><span className="metric-value">{loading ? "—" : stats?.total_voices || 0}</span><p className="metric-note">{stats?.ready_voices || 0} ready for the studio</p></div>
        <div className="metric"><p className="eyebrow">RECORDINGS</p><span className="metric-value">{loading ? "—" : stats?.total_generations || 0}</span><p className="metric-note">{stats?.completed_generations || 0} completed generations</p></div>
        <div className="metric"><p className="eyebrow">CHARACTERS VOICED</p><span className="metric-value">{loading ? "—" : (stats?.total_characters_used || 0).toLocaleString()}</span><p className="metric-note">Characters rendered to speech</p></div>
        <div className="metric"><p className="eyebrow">VOICE AGENTS</p><span className="metric-value">{loading ? "—" : stats?.total_agents || 0}</span><p className="metric-note">{stats?.total_sessions || 0} calls completed</p></div>
      </div>
      {error && <div className="p-4 mb-6 border border-red-200 text-red-700 bg-red-50 text-sm" role="alert">{error}</div>}
      <div className="overview-bottom"><section><SectionTitle>Find your flow</SectionTitle>
        <Link href="/voices" className="workflow-row"><Mic2 size={20} strokeWidth={1.5} /><div><strong>Voice library</strong><p>Collect your original voices</p></div><ArrowRight size={16} /></Link>
        <Link href="/studio" className="workflow-row"><Sparkles size={20} strokeWidth={1.5} /><div><strong>Voice studio</strong><p>Turn your script into narration</p></div><ArrowRight size={16} /></Link>
        <Link href="/agents" className="workflow-row"><Bot size={20} strokeWidth={1.5} /><div><strong>Voice agents</strong><p>Explore the v1.1 preview</p></div><ArrowRight size={16} /></Link>
      </section><section><SectionTitle aside={<Link href="/history" className="eyebrow hover:underline">VIEW ALL ↗</Link>}>Recent recordings</SectionTitle>
        {loading ? <div className="py-14 text-center text-sm text-muted">Loading recordings…</div> : !stats?.recent_activity?.length ? <div className="py-14 flex flex-col items-center text-center gap-3"><History size={28} strokeWidth={1} className="text-muted" /><p className="text-sm text-muted">A clean slate. Your first take is waiting.</p><Link href="/studio" className="text-link">Create a recording <ArrowRight size={14} /></Link></div> : stats.recent_activity.map((act, index) => <div key={act.id} className="take-row"><span className="eyebrow">{String(index + 1).padStart(2, "0")}</span><div><p>Synthesized {act.characters} characters</p><time>{new Date(act.created_at).toLocaleString()}</time></div><span className="text-xs text-muted capitalize">{act.status}</span></div>)}
      </section></div>
    </div>
  );
}
