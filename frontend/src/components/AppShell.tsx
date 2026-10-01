"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { api, type Health } from "@/lib/api";

const NAV = [
  { href: "/", label: "Agent Chat", icon: "M8 10h8M8 14h5m-5 8-4 3v-5a9 9 0 1 1 3 2" },
  { href: "/trace", label: "Tool Trace", icon: "M4 6h16M4 12h10M4 18h7" },
  { href: "/candidates", label: "Candidates", icon: "M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8Zm-7 8a7 7 0 0 1 14 0" },
  { href: "/jobs", label: "Jobs", icon: "M4 8h16v11H4zM9 8V6a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v2" },
  { href: "/approvals", label: "Approvals", icon: "M9 12l2 2 4-5M4 4h16v16H4z" },
  { href: "/activity", label: "Activity", icon: "M3 12h4l3-8 4 16 3-8h4" },
  { href: "/health", label: "System Health", icon: "M12 21s-7-4.5-9-9a5 5 0 0 1 9-3 5 5 0 0 1 9 3c-2 4.5-9 9-9 9Z" },
];

function NavIcon({ d }: { d: string }) {
  return (
    <svg viewBox="0 0 24 24" className="h-4 w-4 shrink-0" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d={d} />
    </svg>
  );
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [health, setHealth] = useState<Health | null>(null);
  const [unreachable, setUnreachable] = useState(false);

  useEffect(() => {
    let active = true;
    const load = () =>
      api
        .health()
        .then((value) => {
          if (active) {
            setHealth(value);
            setUnreachable(false);
          }
        })
        .catch(() => active && setUnreachable(true));
    load();
    const timer = setInterval(load, 30000);
    return () => {
      active = false;
      clearInterval(timer);
    };
  }, []);

  const demo = health?.ai.provider === "demo" || !health?.ai.api_key_configured;

  return (
    <div className="flex min-h-screen">
      <aside className="fixed inset-y-0 left-0 flex w-60 flex-col bg-slate-950 text-slate-300">
        <div className="flex items-center gap-2.5 px-5 py-5">
          <span className="grid h-8 w-8 place-items-center rounded-lg bg-emerald-500/15 text-emerald-400">
            <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round">
              <rect x="5" y="8" width="14" height="10" rx="3.5" />
              <circle cx="9.4" cy="13" r="1.1" fill="currentColor" stroke="none" />
              <circle cx="14.6" cy="13" r="1.1" fill="currentColor" stroke="none" />
              <path d="M9.5 16h5" />
              <path d="M12 8V5.6" />
            </svg>
          </span>
          <div>
            <p className="text-sm font-semibold text-white">RecruitAgent AI</p>
            <p className="text-[11px] text-slate-400">recruiting ops agent</p>
          </div>
        </div>
        <nav className="mt-2 flex-1 space-y-0.5 px-3">
          {NAV.map((item) => {
            const active = item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex items-center gap-2.5 rounded-lg px-3 py-2 text-[13px] font-medium transition-colors ${
                  active ? "bg-white/10 text-white" : "text-slate-400 hover:bg-white/5 hover:text-slate-200"
                }`}
              >
                <NavIcon d={item.icon} />
                {item.label}
              </Link>
            );
          })}
        </nav>
        <div className="border-t border-white/10 px-5 py-4">
          {unreachable ? (
            <p className="text-[11px] text-rose-400">API unreachable — is it running on {`${process.env.NEXT_PUBLIC_API_BASE_URL ?? "localhost:8000"}`}?</p>
          ) : (
            <div className="space-y-1">
              <span
                className={`inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-[10px] font-semibold ${
                  demo ? "bg-amber-500/15 text-amber-300" : "bg-emerald-500/15 text-emerald-300"
                }`}
              >
                <span className={`h-1.5 w-1.5 rounded-full ${demo ? "bg-amber-400" : "bg-emerald-400"}`} />
                {demo ? "DEMO AGENT · no API key" : "OPENAI · live tool calling"}
              </span>
              <p className="text-[10px] leading-relaxed text-slate-500">
                Local portfolio demo — no auth. Do not expose with real candidate data.
              </p>
            </div>
          )}
        </div>
      </aside>
      <main className="ml-60 flex-1">
        <div className="mx-auto max-w-6xl px-8 py-8">{children}</div>
      </main>
    </div>
  );
}
