"use client";

import {
  CircleDot,
  FileText,
  FlaskConical,
  History,
  LayoutDashboard,
  Menu,
  ShieldCheck,
  ShieldHalf,
  X,
} from "lucide-react";
import { ReactNode, useState } from "react";

export type ViewKey =
  | "dashboard"
  | "history"
  | "requirements"
  | "security"
  | "tests";

const NAV: { key: ViewKey; label: string; icon: ReactNode }[] = [
  { key: "dashboard", label: "Dashboard", icon: <LayoutDashboard size={18} /> },
  { key: "history", label: "Analyses", icon: <History size={18} /> },
  { key: "requirements", label: "Requirements", icon: <FileText size={18} /> },
  { key: "security", label: "Security", icon: <ShieldHalf size={18} /> },
  { key: "tests", label: "Test Cases", icon: <FlaskConical size={18} /> },
];

// Result views have nothing to show until an analysis exists.
const NEEDS_RESULTS: ViewKey[] = ["requirements", "security", "tests"];

function NavList({
  view,
  onNavigate,
  hasResults,
}: {
  view: ViewKey;
  onNavigate: (view: ViewKey) => void;
  hasResults: boolean;
}) {
  return (
    <div className="space-y-1">
      {NAV.map((item) => {
        const disabled = NEEDS_RESULTS.includes(item.key) && !hasResults;
        const active = view === item.key;
        return (
          <button
            key={item.key}
            type="button"
            disabled={disabled}
            onClick={() => onNavigate(item.key)}
            title={disabled ? "Run an analysis first" : undefined}
            className={`flex w-full items-center gap-3 rounded-DEFAULT px-3 py-2.5 text-left text-[13.5px] transition-colors ${
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
  );
}

function Brand() {
  return (
    <div className="flex items-center gap-2.5">
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
  );
}

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
  const [drawerOpen, setDrawerOpen] = useState(false);

  function navigate(next: ViewKey) {
    onNavigate(next);
    setDrawerOpen(false);
  }

  return (
    <div className="flex min-h-screen bg-base">
      {/* Desktop sidebar */}
      <nav className="fixed left-0 top-0 z-40 hidden h-screen w-60 flex-col border-r border-line bg-surface px-3 py-5 md:flex">
        <div className="mb-8 px-2">
          <Brand />
        </div>
        <div className="flex-1">
          <NavList view={view} onNavigate={navigate} hasResults={hasResults} />
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

      {/* Mobile drawer — a real sidebar rather than a row of scrolling pills */}
      {drawerOpen ? (
        <div className="fixed inset-0 z-50 md:hidden">
          <button
            type="button"
            aria-label="Close menu"
            onClick={() => setDrawerOpen(false)}
            className="absolute inset-0 bg-black/60 backdrop-blur-[2px]"
          />
          <nav className="sg-fade-in absolute left-0 top-0 flex h-full w-[74vw] max-w-[280px] flex-col border-r border-line bg-surface px-3 py-5">
            <div className="mb-7 flex items-center justify-between px-2">
              <Brand />
              <button
                type="button"
                onClick={() => setDrawerOpen(false)}
                aria-label="Close menu"
                className="rounded-DEFAULT p-1.5 text-ink-muted hover:bg-white/[0.06] hover:text-ink"
              >
                <X size={18} />
              </button>
            </div>
            <NavList view={view} onNavigate={navigate} hasResults={hasResults} />
          </nav>
        </div>
      ) : null}

      <div className="flex min-h-screen w-full flex-col md:pl-60">
        <header className="sticky top-0 z-30 flex h-14 items-center gap-3 border-b border-line bg-surface/85 px-4 backdrop-blur-md md:px-5">
          <button
            type="button"
            onClick={() => setDrawerOpen(true)}
            aria-label="Open menu"
            className="-ml-1 rounded-DEFAULT p-2 text-ink-dim hover:bg-white/[0.05] hover:text-ink md:hidden"
          >
            <Menu size={19} />
          </button>
          <p className="min-w-0 flex-1 truncate font-mono text-[12px] text-ink-muted">
            {breadcrumb}
          </p>
          {running ? (
            <span className="flex shrink-0 items-center gap-1.5 rounded-full border border-accent/30 bg-accent/10 px-2.5 py-1 font-mono text-[10px] uppercase tracking-wider text-accent-soft">
              <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-accent" />
              Live
            </span>
          ) : null}
        </header>

        <main className="flex-1 px-4 py-5 md:px-5 md:py-6">
          <div className="mx-auto w-full max-w-[1440px]">{children}</div>
        </main>
      </div>
    </div>
  );
}
