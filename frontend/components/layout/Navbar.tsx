"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Activity,
  Bot,
  History,
  Laptop,
  Mic2,
  ShieldCheck,
  Sliders,
  Sparkles,
} from "lucide-react";

const navItems = [
  { href: "/dashboard", label: "Dashboard", icon: Activity },
  { href: "/voices", label: "Voice Library", icon: Mic2 },
  { href: "/studio", label: "Voice Studio", icon: Sparkles },
  { href: "/agents", label: "Voice Agents", icon: Bot, badge: "v1.1" },
  { href: "/history", label: "History", icon: History },
  { href: "/verify", label: "Verify AI", icon: ShieldCheck, badge: "C2PA" },
  { href: "/settings", label: "Settings", icon: Sliders },
];

export function Navbar() {
  const pathname = usePathname();

  // Landing page view
  if (pathname === "/") {
    return (
      <header className="sticky top-0 z-50 border-b border-neutral-200 dark:border-neutral-800 bg-white/80 dark:bg-neutral-950/80 backdrop-blur-md">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2.5 font-semibold text-lg tracking-tight">
            <div className="h-9 w-9 rounded-xl bg-neutral-900 dark:bg-white flex items-center justify-center text-white dark:text-neutral-900 shadow-sm">
              <Mic2 className="h-5 w-5" />
            </div>
            <span>VoiceRep</span>
          </Link>

          <div className="flex items-center gap-3">
            <div className="hidden sm:flex items-center gap-1.5 px-3 py-1 rounded-full border border-neutral-200 dark:border-neutral-800 bg-neutral-50 dark:bg-neutral-900 text-xs text-neutral-600 dark:text-neutral-400 font-medium">
              <Laptop className="h-3.5 w-3.5 text-neutral-500" />
              <span>100% On-Device</span>
            </div>
            <Link
              href="/studio"
              className="px-4 py-2 text-sm font-medium rounded-lg bg-neutral-900 dark:bg-white text-white dark:text-neutral-900 hover:bg-neutral-800 dark:hover:bg-neutral-100 transition-colors shadow-sm"
            >
              Open Studio
            </Link>
          </div>
        </div>
      </header>
    );
  }

  return (
    <header className="sticky top-0 z-50 border-b border-neutral-200 dark:border-neutral-800 bg-white/90 dark:bg-neutral-950/90 backdrop-blur-md">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        <div className="flex items-center gap-8">
          <Link href="/dashboard" className="flex items-center gap-2.5 font-semibold text-lg tracking-tight">
            <div className="h-9 w-9 rounded-xl bg-neutral-900 dark:bg-white flex items-center justify-center text-white dark:text-neutral-900 shadow-sm">
              <Mic2 className="h-5 w-5" />
            </div>
            <span>VoiceRep</span>
          </Link>

          <nav className="hidden md:flex items-center gap-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = pathname === item.href || (item.href !== "/dashboard" && pathname.startsWith(item.href));
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-sm font-medium transition-all ${
                    isActive
                      ? "bg-neutral-100 dark:bg-neutral-800 text-neutral-900 dark:text-white shadow-xs"
                      : "text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-white hover:bg-neutral-50 dark:hover:bg-neutral-900"
                  }`}
                >
                  <Icon className={`h-4 w-4 ${isActive ? "text-neutral-900 dark:text-white" : "text-neutral-500"}`} />
                  <span>{item.label}</span>
                  {item.badge && (
                    <span className="px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wider rounded-md bg-amber-100 text-amber-800 dark:bg-amber-950/60 dark:text-amber-300">
                      {item.badge}
                    </span>
                  )}
                </Link>
              );
            })}
          </nav>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-full border border-neutral-200 dark:border-neutral-800 bg-neutral-100/70 dark:bg-neutral-900 text-xs text-neutral-700 dark:text-neutral-300 font-medium">
            <Laptop className="h-3.5 w-3.5 text-emerald-500" />
            <span>Local Mode</span>
          </div>
        </div>
      </div>
    </header>
  );
}
