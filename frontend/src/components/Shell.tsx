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
      {NAV.map((item, index) => {
        const disabled = NEEDS_RESULTS.includes(item.key) && !hasResults;
        const active = view === item.key;
        return (
          <button
            key={item.key}
            type="button"
            disabled={disabled}
            onClick={() => onNavigate(item.key)}
            title={disabled ? "Run an analysis first" : undefined}
            style={{ "--sg-delay": `${0.05 + index * 0.05}s` } as React.CSSProperties}
            className={`sg-rise group relative flex w-full items-center gap-3 overflow-hidden rounded-DEFAULT px-3 py-2.5 text-left text-[13.5px] transition-all duration-200 ${
              active
                ? "bg-accent/15 font-medium text-accent-soft"
                : disabled
                  ? "cursor-not-allowed text-ink-faint/60"
                  : "cursor-pointer text-ink-dim hover:translate-x-0.5 hover:bg-white/[0.05] hover:text-ink"
            }`}
          >
            {/* Active marker, drawn as a scaling bar so it grows into place */}
            <span
              className={`absolute left-0 top-1/2 h-6 w-[3px] -translate-y-1/2 rounded-r-full bg-accent transition-transform duration-300 ${
                active ? "scale-y-100" : "scale-y-0"
              }`}
            />
            <span
              className={`transition-transform duration-200 ${
                active ? "text-accent" : ""
              } ${disabled ? "" : "group-hover:scale-110"}`}
            >
              {item.icon}
            </span>
            {item.label}
          </button>
        );
      })}
    </div>
  );
}

function Brand() {
  return (
    <div className="group flex items-center gap-2.5">
      <div className="relative flex h-8 w-8 items-center justify-center rounded-DEFAULT border border-accent/30 bg-accent/10 transition-transform duration-300 group-hover:scale-105">
        {/* Halo that only breathes on hover, so the sidebar is calm at rest */}
        <span className="absolute inset-0 rounded-DEFAULT bg-accent/20 opacity-0 blur-md transition-opacity duration-300 group-hover:opacity-100" />
        <ShieldCheck className="relative text-accent" size={17} />
      </div>
      <div>
        <p className="text-[15px] font-semibold leading-tight text-ink">
          SpecGuard{" "}
          <span className="sg-hue bg-linear-to-r from-accent via-low to-accent bg-clip-text text-transparent">
            AI
          </span>
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
    <div className="relative flex min-h-screen bg-base">
      {/* Ambient wash. Fixed and non-interactive so it never enters hit-testing
          or scrolls with the content. */}
      <div
        aria-hidden="true"
        className="pointer-events-none fixed inset-0 z-0 bg-[radial-gradient(circle_at_18%_0%,rgba(75,142,255,0.07),transparent_45%),radial-gradient(circle_at_88%_8%,rgba(126,226,184,0.05),transparent_42%)]"
      />

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

      {/* Positioned above the ambient wash: a fixed z-0 layer paints over
          non-positioned siblings, which would otherwise tint the panels. */}
      <div className="relative z-10 flex min-h-screen w-full flex-col md:pl-60">
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
          {/* Keyed on the view so React remounts on navigation and the entrance
              animation replays, giving each tab switch a transition. */}
          <div key={view} className="sg-rise mx-auto w-full max-w-[1440px]">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}
