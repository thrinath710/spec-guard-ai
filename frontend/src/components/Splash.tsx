"use client";

import { ShieldCheck } from "lucide-react";
import { useEffect, useState } from "react";

const BOOT_LINES = [
  "Initializing analysis engine",
  "Loading embedding model",
  "Connecting to vector store",
  "Ready",
];

/** Opening sequence: shows the brand for ~2.4s, then hands off to the dashboard. */
export function Splash({ onDone }: { onDone: () => void }) {
  const [step, setStep] = useState(0);
  const [leaving, setLeaving] = useState(false);

  useEffect(() => {
    const timers = [
      setTimeout(() => setStep(1), 500),
      setTimeout(() => setStep(2), 1000),
      setTimeout(() => setStep(3), 1500),
      setTimeout(() => setLeaving(true), 2050),
      setTimeout(onDone, 2450),
    ];
    return () => timers.forEach(clearTimeout);
  }, [onDone]);

  return (
    <div
      className={`fixed inset-0 z-50 flex flex-col items-center justify-center bg-base transition-opacity duration-400 ${
        leaving ? "opacity-0" : "opacity-100"
      }`}
    >
      <div className="relative flex flex-col items-center">
        <div className="relative">
          <div className="absolute inset-0 rounded-2xl bg-accent/20 blur-2xl" />
          <div className="sg-pulse relative flex h-20 w-20 items-center justify-center rounded-2xl border border-accent/30 bg-panel">
            <ShieldCheck className="text-accent" size={38} strokeWidth={1.6} />
          </div>
        </div>

        <h1 className="sg-fade-up mt-7 text-4xl font-bold tracking-tight text-ink">
          SpecGuard <span className="text-accent">AI</span>
        </h1>
        <p className="sg-fade-up mt-2 font-mono text-[12px] uppercase tracking-[0.22em] text-ink-muted">
          Requirement &amp; Security Assurance
        </p>

        <div className="mt-9 h-px w-64 overflow-hidden bg-line">
          <div className="sg-sweep h-full w-1/3 bg-accent" />
        </div>

        <p className="mt-4 h-4 font-mono text-[12px] text-ink-faint">
          {BOOT_LINES[Math.min(step, BOOT_LINES.length - 1)]}
          <span className="animate-pulse">_</span>
        </p>
      </div>
    </div>
  );
}
