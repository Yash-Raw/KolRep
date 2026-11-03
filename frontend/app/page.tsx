import Link from "next/link";
import {
  ArrowRight,
  Bot,
  CheckCircle2,
  Lock,
  Mic2,
  ShieldCheck,
  Sparkles,
  Volume2,
  Zap,
} from "lucide-react";

export default function LandingPage() {
  return (
    <div className="flex-1 flex flex-col justify-between">
      {/* Hero Section */}
      <section className="relative overflow-hidden pt-20 pb-16 md:pt-32 md:pb-24">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 text-center space-y-8">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full border border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-900 text-xs font-medium text-neutral-600 dark:text-neutral-400 shadow-xs">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
            <span>Enterprise-Grade Voice Cloning & Conversational Agents</span>
          </div>

          <h1 className="text-4xl sm:text-6xl font-bold tracking-tight text-neutral-900 dark:text-white max-w-4xl mx-auto leading-tight">
            Clone your voice once. <br className="hidden sm:inline" />
            <span className="text-neutral-500 dark:text-neutral-400">Power both Studio narration and interactive AI agents.</span>
          </h1>

          <p className="text-lg text-neutral-600 dark:text-neutral-400 max-w-2xl mx-auto leading-relaxed">
            VoiceRep turns an authorized 60-second voice sample into a reusable synthetic profile. Generate long-form narration in seconds or hold live, real-time voice conversations with zero setup friction.
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-4 pt-4">
            <Link
              href="/dashboard"
              className="w-full sm:w-auto px-7 py-3.5 rounded-xl bg-neutral-900 dark:bg-white text-white dark:text-neutral-900 font-medium text-sm hover:bg-neutral-800 dark:hover:bg-neutral-100 transition-all shadow-md hover:shadow-lg flex items-center justify-center gap-2 group"
            >
              <span>Get Started</span>
              <ArrowRight className="h-4 w-4 group-hover:translate-x-0.5 transition-transform" />
            </Link>
            <Link
              href="/voices"
              className="w-full sm:w-auto px-7 py-3.5 rounded-xl border border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-900 text-neutral-900 dark:text-white font-medium text-sm hover:bg-neutral-50 dark:hover:bg-neutral-800 transition-colors shadow-xs"
            >
              View Voice Library
            </Link>
          </div>
        </div>
      </section>

      {/* Two Pillars Section */}
      <section className="py-16 border-y border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-900/50">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-12">
            <h2 className="text-2xl font-bold text-neutral-900 dark:text-white">One Shared Acoustic Profile, Two Core Modes</h2>
            <p className="text-sm text-neutral-500 mt-2">Never train or clone separate models for speech and chat.</p>
          </div>

          <div className="grid md:grid-cols-2 gap-8">
            {/* Pillar A: Studio */}
            <div className="p-8 rounded-2xl border border-neutral-200 dark:border-neutral-800 bg-neutral-50 dark:bg-neutral-900 flex flex-col justify-between">
              <div className="space-y-4">
                <div className="h-12 w-12 rounded-xl bg-neutral-900 dark:bg-white text-white dark:text-neutral-900 flex items-center justify-center shadow-xs">
                  <Sparkles className="h-6 w-6" />
                </div>
                <h3 className="text-xl font-bold text-neutral-900 dark:text-white">Module A: Voice Studio</h3>
                <p className="text-sm text-neutral-600 dark:text-neutral-400 leading-relaxed">
                  High-fidelity text-to-speech generation. Control stability, similarity boost, speaking tempo, and vocal expressiveness. Export pristine studio-ready audio files.
                </p>

                <ul className="space-y-2.5 pt-2 text-xs text-neutral-600 dark:text-neutral-300">
                  <li className="flex items-center gap-2">
                    <CheckCircle2 className="h-4 w-4 text-emerald-500 shrink-0" />
                    <span>Instant streaming synthesis with ElevenLabs V2 models</span>
                  </li>
                  <li className="flex items-center gap-2">
                    <CheckCircle2 className="h-4 w-4 text-emerald-500 shrink-0" />
                    <span>Fine-grained acoustic stability & similarity controls</span>
                  </li>
                  <li className="flex items-center gap-2">
                    <CheckCircle2 className="h-4 w-4 text-emerald-500 shrink-0" />
                    <span>Audio waveform playback, seeking, and direct download</span>
                  </li>
                </ul>
              </div>

              <div className="pt-8">
                <Link
                  href="/studio"
                  className="inline-flex items-center gap-2 text-xs font-semibold text-neutral-900 dark:text-white hover:underline"
                >
                  <span>Explore Voice Studio</span>
                  <ArrowRight className="h-3.5 w-3.5" />
                </Link>
              </div>
            </div>

            {/* Pillar B: Agents */}
            <div className="p-8 rounded-2xl border border-neutral-200 dark:border-neutral-800 bg-neutral-50 dark:bg-neutral-900 flex flex-col justify-between">
              <div className="space-y-4">
                <div className="h-12 w-12 rounded-xl bg-neutral-900 dark:bg-white text-white dark:text-neutral-900 flex items-center justify-center shadow-xs">
                  <Bot className="h-6 w-6" />
                </div>
                <h3 className="text-xl font-bold text-neutral-900 dark:text-white">Module B: Conversational Agents</h3>
                <p className="text-sm text-neutral-600 dark:text-neutral-400 leading-relaxed">
                  Build interactive AI voice agents that speak with your cloned voice. Real-time microphone audio input, full turn detection, live conversational transcripts, and agent interruption.
                </p>

                <ul className="space-y-2.5 pt-2 text-xs text-neutral-600 dark:text-neutral-300">
                  <li className="flex items-center gap-2">
                    <CheckCircle2 className="h-4 w-4 text-emerald-500 shrink-0" />
                    <span>Ultra-low latency WebSocket conversational protocol</span>
                  </li>
                  <li className="flex items-center gap-2">
                    <CheckCircle2 className="h-4 w-4 text-emerald-500 shrink-0" />
                    <span>Per-agent system instruction & greeting overrides</span>
                  </li>
                  <li className="flex items-center gap-2">
                    <CheckCircle2 className="h-4 w-4 text-emerald-500 shrink-0" />
                    <span>Natural speech interruption and turn management</span>
                  </li>
                </ul>
              </div>

              <div className="pt-8">
                <Link
                  href="/agents"
                  className="inline-flex items-center gap-2 text-xs font-semibold text-neutral-900 dark:text-white hover:underline"
                >
                  <span>Explore Voice Agents</span>
                  <ArrowRight className="h-3.5 w-3.5" />
                </Link>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Safety & Compliance */}
      <section className="py-16">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center space-y-6">
          <div className="h-12 w-12 mx-auto rounded-xl bg-neutral-100 dark:bg-neutral-800 flex items-center justify-center text-neutral-900 dark:text-white">
            <ShieldCheck className="h-6 w-6" />
          </div>
          <h3 className="text-xl font-bold text-neutral-900 dark:text-white">Strict Voice Authorization & Consent</h3>
          <p className="text-sm text-neutral-600 dark:text-neutral-400 max-w-xl mx-auto leading-relaxed">
            VoiceRep requires affirmative speaker consent before any voice profile is generated. Audio samples are validated for quality and speech ratio, encrypted at rest, and subject to immediate revocation.
          </p>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-neutral-200 dark:border-neutral-800 py-8 bg-white dark:bg-neutral-950">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-neutral-500">
          <div className="flex items-center gap-2 font-medium text-neutral-900 dark:text-white">
            <Mic2 className="h-4 w-4" />
            <span>VoiceRep Platform</span>
          </div>
          <p>© {new Date().getFullYear()} VoiceRep Inc. All rights reserved.</p>
        </div>
      </footer>
    </div>
  );
}
