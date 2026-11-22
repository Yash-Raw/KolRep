"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { Laptop, Sparkles } from "lucide-react";

export default function LoginPage() {
  const router = useRouter();

  useEffect(() => {
    // KolRep is 100% on-device and single-user. No login required.
    router.replace("/dashboard");
  }, [router]);

  return (
    <div className="flex-1 flex items-center justify-center p-4">
      <div className="panel w-full max-w-sm p-8 text-center space-y-4"><p className="eyebrow">KOLREP / LOCAL WORKSPACE</p>
        <div className="h-12 w-12 rounded-lg bg-accent  text-white  flex items-center justify-center mx-auto ">
          <Laptop className="h-6 w-6 text-emerald-500" />
        </div>
        <h2 className="text-xl font-bold tracking-tight text-ink ">
          Pure Local Mode
        </h2>
        <p className="text-xs text-muted leading-relaxed">
          KolRep runs completely on your local workstation. No cloud account or sign-in is required. Redirecting to your dashboard...
        </p>
        <div className="flex items-center justify-center gap-2 text-xs text-emerald-600 dark:text-emerald-400 font-medium pt-2">
          <Sparkles className="h-3.5 w-3.5 animate-spin" />
          <span>Opening Dashboard...</span>
        </div>
      </div>
    </div>
  );
}
