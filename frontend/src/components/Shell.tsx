"use client";

import {
  CircleDot,
  FileText,
  FlaskConical,
  History,
  LayoutDashboard,
  PlusCircle,
  ShieldCheck,
  ShieldHalf,
} from "lucide-react";
import { ReactNode } from "react";

export type ViewKey =
  | "dashboard"
  | "new"
  | "history"
  | "requirements"
  | "security"
  | "tests";

const NAV: { key: ViewKey; label: string; icon: ReactNode }[] = [
  { key: "dashboard", label: "Dashboard", icon: <LayoutDashboard size={18} /> },
  { key: "new", label: "New Analysis", icon: <PlusCircle size={18} /> },
  { key: "history", label: "Analyses", icon: <History size={18} /> },
  { key: "requirements", label: "Requirements", icon: <FileText size={18} /> },
  { key: "security", label: "Security", icon: <ShieldHalf size={18} /> },
  { key: "tests", label: "Test Cases", icon: <FlaskConical size={18} /> },
];

export function Shell({
  view,
  onNavigate,
  breadcrumb,
  hasResults,
  running,
  children,
}: {
  view: ViewKey;
  onNavigate: (view: ViewKey) => void;
  breadcrumb: string;
  hasResults: boolean;
  running: boolean;
  children: ReactNode;
}) {
  // Result views are meaningless without an analysis, so they stay disabled until one exists.
  const needsResults: ViewKey[] = ["requirements", "security", "tests"];

  return (
    <div className="flex min-h-screen bg-base">
      <nav className="fixed left-0 top-0 z-40 hidden h-screen w-60 flex-col border-r border-line bg-surface px-3 py-5 md:flex">
        <div className="mb-8 flex items-center gap-2.5 px-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-DEFAULT border border-accent/30 bg-accent/10">
            <ShieldCheck className="text-accent" size={17} />
          </div>
          <div>
            <p className="text-[15px] font-semibold leading-tight text-ink">
              SpecGuard AI
            </p>
            <p className="font-mono text-[10px] uppercase tracking-[0.12em] text-ink-faint">
              Assurance Engine
            </p>
          </div>
        </div>

        <div className="flex-1 space-y-1">
          {NAV.map((item) => {
            const disabled = needsResults.includes(item.key) && !hasResults;
            const active = view === item.key;
            return (
              <button
                key={item.key}
                type="button"
                disabled={disabled}
                onClick={() => onNavigate(item.key)}
                title={disabled ? "Run an analysis first" : undefined}
                className={`flex w-full items-center gap-3 rounded-DEFAULT px-3 py-2 text-left text-[13px] transition-colors ${
                  active
                    ? "bg-accent/15 font-medium text-accent-soft"
                    : disabled
                      ? "cursor-not-allowed text-ink-faint/60"
                      : "text-ink-dim hover:bg-white/[0.04] hover:text-ink"
                }`}
              >
                <span className={active ? "text-accent" : ""}>{item.icon}</span>
                {item.label}
              </button>
            );
          })}
        </div>

        <div className="mt-auto rounded-DEFAULT border border-line bg-panel px-3 py-2.5">
          <div className="flex items-center gap-2">
            <CircleDot
              size={13}
              className={running ? "animate-pulse text-accent" : "text-ok"}
            />
            <span className="font-mono text-[11px] text-ink-muted">
              {running ? "Analysis running" : "Idle"}
            </span>
          </div>
        </div>
      </nav>

      <div className="flex min-h-screen w-full flex-col md:pl-60">
        <header className="sticky top-0 z-30 flex h-14 items-center justify-between border-b border-line bg-surface/85 px-5 backdrop-blur-md">
          <p className="truncate font-mono text-[12px] text-ink-muted">
            {breadcrumb}
          </p>
          <div className="flex items-center gap-3">
            {running ? (
              <span className="flex items-center gap-1.5 rounded-full border border-accent/30 bg-accent/10 px-2.5 py-1 font-mono text-[10px] uppercase tracking-wider text-accent-soft">
                <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-accent" />
                Live
              </span>
            ) : null}
          </div>
        </header>

        <main className="flex-1 px-5 py-6">
          <div className="mx-auto w-full max-w-[1440px]">{children}</div>
        </main>
      </div>
    </div>
  );
}

/** Mobile nav — the sidebar is hidden below md. */
export function MobileNav({
  view,
  onNavigate,
  hasResults,
}: {
  view: ViewKey;
  onNavigate: (view: ViewKey) => void;
  hasResults: boolean;
}) {
  const needsResults: ViewKey[] = ["requirements", "security", "tests"];
  return (
    <div className="mb-5 flex gap-2 overflow-x-auto pb-1 md:hidden">
      {NAV.map((item) => {
        const disabled = needsResults.includes(item.key) && !hasResults;
        return (
          <button
            key={item.key}
            type="button"
            disabled={disabled}
            onClick={() => onNavigate(item.key)}
            className={`shrink-0 rounded-full border px-3 py-1.5 text-[12px] transition-colors ${
              view === item.key
                ? "border-accent/40 bg-accent/15 text-accent-soft"
                : "border-line text-ink-muted disabled:opacity-40"
            }`}
          >
            {item.label}
          </button>
        );
      })}
    </div>
  );
}
