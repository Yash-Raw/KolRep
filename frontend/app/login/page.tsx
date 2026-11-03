"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowRight, Bot, Lock, Mail, Mic2, Sparkles } from "lucide-react";
import { setAuthToken } from "@/lib/api";
import { isSupabaseConfigured, supabase } from "@/lib/supabase";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const handleDemoLogin = () => {
    // Generate a valid JWT payload for the test user
    // { sub: "11111111-1111-1111-1111-111111111111", email: "demo@voicerep.local" }
    const demoToken =
      "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMTExMTExMS0xMTExLTExMTEtMTExMS0xMTExMTExMTExMTEiLCJlbWFpbCI6ImRlbW9Adm9pY2VyZXAubG9jYWwifQ.jl57JKy4e9wZsUXkdw71R5m-1kkTqm3W7HCPGPFvZwQ";
    setAuthToken(demoToken);
    router.push("/dashboard");
  };

  const handleSupabaseAuth = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !password) return;

    if (!isSupabaseConfigured || !supabase) {
      // Local fallback
      handleDemoLogin();
      return;
    }

    setIsLoading(true);
    setErrorMessage(null);

    try {
      const { data, error } = await supabase.auth.signInWithPassword({
        email,
        password,
      });

      if (error) {
        // Try sign-up if user doesn't exist
        const signUpRes = await supabase.auth.signUp({ email, password });
        if (signUpRes.error) {
          throw new Error(signUpRes.error.message);
        }
        if (signUpRes.data.session?.access_token) {
          setAuthToken(signUpRes.data.session.access_token);
          router.push("/dashboard");
          return;
        }
      }

      if (data.session?.access_token) {
        setAuthToken(data.session.access_token);
        router.push("/dashboard");
      }
    } catch (err: any) {
      setErrorMessage(err.message || "Failed to authenticate.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex-1 flex items-center justify-center p-4">
      <div className="w-full max-w-md bg-white dark:bg-neutral-900 border border-neutral-200 dark:border-neutral-800 rounded-3xl p-8 shadow-xl space-y-6">
        <div className="text-center space-y-2">
          <div className="h-12 w-12 rounded-2xl bg-neutral-900 dark:bg-white text-white dark:text-neutral-900 flex items-center justify-center mx-auto shadow-sm">
            <Mic2 className="h-6 w-6" />
          </div>
          <h2 className="text-2xl font-bold tracking-tight text-neutral-900 dark:text-white">Welcome to VoiceRep</h2>
          <p className="text-xs text-neutral-500">Sign in to manage your cloned voices and AI agents.</p>
        </div>

        {errorMessage && (
          <div className="p-3 rounded-xl bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-800 text-xs text-red-600 dark:text-red-400">
            {errorMessage}
          </div>
        )}

        <form onSubmit={handleSupabaseAuth} className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-neutral-700 dark:text-neutral-300 mb-1">
              Email Address
            </label>
            <div className="relative">
              <Mail className="h-4 w-4 absolute left-3.5 top-3 text-neutral-400" />
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="name@company.com"
                className="w-full pl-10 pr-3.5 py-2.5 rounded-xl border border-neutral-200 dark:border-neutral-800 bg-neutral-50 dark:bg-neutral-950 text-sm focus:outline-hidden focus:ring-2 focus:ring-neutral-900 dark:focus:ring-white"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-neutral-700 dark:text-neutral-300 mb-1">
              Password
            </label>
            <div className="relative">
              <Lock className="h-4 w-4 absolute left-3.5 top-3 text-neutral-400" />
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full pl-10 pr-3.5 py-2.5 rounded-xl border border-neutral-200 dark:border-neutral-800 bg-neutral-50 dark:bg-neutral-950 text-sm focus:outline-hidden focus:ring-2 focus:ring-neutral-900 dark:focus:ring-white"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={isLoading}
            className="w-full py-3 rounded-xl bg-neutral-900 dark:bg-white text-white dark:text-neutral-900 text-sm font-medium hover:bg-neutral-800 dark:hover:bg-neutral-100 transition-colors shadow-sm disabled:opacity-50"
          >
            {isLoading ? "Signing in..." : "Sign In with Email"}
          </button>
        </form>

        <div className="relative flex items-center justify-center">
          <div className="border-t border-neutral-200 dark:border-neutral-800 w-full"></div>
          <span className="bg-white dark:bg-neutral-900 px-3 text-xs text-neutral-400 uppercase tracking-wider">
            or
          </span>
        </div>

        <button
          type="button"
          onClick={handleDemoLogin}
          className="w-full py-3 rounded-xl border border-neutral-200 dark:border-neutral-800 bg-neutral-50 dark:bg-neutral-950 hover:bg-neutral-100 dark:hover:bg-neutral-800 text-sm font-medium text-neutral-900 dark:text-white transition-colors flex items-center justify-center gap-2 shadow-2xs"
        >
          <Sparkles className="h-4 w-4 text-emerald-500" />
          <span>Continue as Demo User</span>
        </button>

        <p className="text-[11px] text-center text-neutral-400">
          By signing in, you agree to our Terms of Use and confirm strict compliance with speaker consent requirements.
        </p>
      </div>
    </div>
  );
}
