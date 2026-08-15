"use client";

import { ArrowRight, ShieldCheck } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { RobotScene } from "./RobotScene";

const BOOT_LINES = [
  "Waking the analysis engine",
  "Loading embedding model",
  "Connecting to the vector store",
  "Calibrating security heuristics",
  "Ready",
];

const TITLE = "SpecGuard";

/** Full run of the opening. Skipping or reduced motion cuts straight to the end. */
const RUN_MS = 4600;
const FADE_MS = 500;

/**
 * The opening sequence.
 *
 * It is skippable and self-limiting: an animation this long is a delight the first
 * time and an obstacle every time after, so there is always a visible Skip control,
 * Escape and Enter both dismiss it, and anyone who has asked for reduced motion is
 * handed the app immediately rather than being shown a frozen tableau.
 */
export function Splash({ onDone }: { onDone: () => void }) {
  const [step, setStep] = useState(0);
  const [leaving, setLeaving] = useState(false);
  // onDone triggers a state change in the parent; guarding means a skip landing in
  // the same tick as the timer cannot fire the handoff twice.
  const finished = useRef(false);

  const finish = useCallback(() => {
    if (finished.current) return;
    finished.current = true;
    setLeaving(true);
    setTimeout(onDone, FADE_MS);
  }, [onDone]);

  useEffect(() => {
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduced) {
      finished.current = true;
      onDone();
      return;
    }

    const perLine = RUN_MS / (BOOT_LINES.length + 1);
    const timers: ReturnType<typeof setTimeout>[] = BOOT_LINES.map((_, i) =>
      setTimeout(() => setStep(i), perLine * (i + 1)),
    );
    timers.push(setTimeout(finish, RUN_MS));

    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape" || event.key === "Enter") finish();
    };
    window.addEventListener("keydown", onKey);

    return () => {
      timers.forEach(clearTimeout);
      window.removeEventListener("keydown", onKey);
    };
  }, [finish, onDone]);

  return (
    <div
      className={`fixed inset-0 z-50 flex flex-col items-center justify-center overflow-hidden bg-base px-5 transition-opacity duration-500 ${
        leaving ? "opacity-0" : "opacity-100"
      }`}
    >
      {/* Vignette so the scene sits in depth rather than flat on the background */}
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_50%_38%,rgba(75,142,255,0.10),transparent_62%)]" />

      <button
        type="button"
        onClick={finish}
        className="sg-fade-in absolute right-5 top-5 z-10 flex items-center gap-1.5 rounded-full border border-line bg-panel/80 px-3.5 py-1.5 font-mono text-[11px] uppercase tracking-[0.14em] text-ink-muted backdrop-blur transition-colors hover:border-accent/40 hover:text-ink focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
        style={{ animationDelay: "1.2s" }}
      >
        Skip <ArrowRight size={13} />
      </button>

      <div className="relative flex w-full max-w-3xl flex-col items-center">
        <RobotScene className="w-full max-w-2xl" />

        <div className="-mt-2 flex flex-col items-center text-center">
          <div
            className="sg-rise flex items-center gap-3"
            style={{ "--sg-delay": "2.9s" } as React.CSSProperties}
          >
            <div className="sg-pulse flex h-11 w-11 items-center justify-center rounded-xl border border-accent/30 bg-panel">
              <ShieldCheck className="text-accent" size={22} strokeWidth={1.7} />
            </div>
            <h1 className="text-4xl font-bold tracking-tight text-ink sm:text-5xl">
              {/* Per-character reveal; the whole word stays in one accessible node */}
              <span aria-hidden="true">
                {TITLE.split("").map((char, i) => (
                  <span
                    key={i}
                    className="sg-char"
                    style={{ "--sg-delay": `${3.05 + i * 0.045}s` } as React.CSSProperties}
                  >
                    {char}
                  </span>
                ))}
              </span>
              <span
                className="sg-char sg-hue ml-2.5 bg-linear-to-r from-accent via-low to-accent bg-clip-text text-transparent"
                style={{ "--sg-delay": `${3.05 + TITLE.length * 0.045}s` } as React.CSSProperties}
                aria-hidden="true"
              >
                AI
              </span>
              <span className="sr-only">SpecGuard AI</span>
            </h1>
          </div>

          <p
            className="sg-rise mt-3 font-mono text-[11px] uppercase tracking-[0.24em] text-ink-muted sm:text-[12px]"
            style={{ "--sg-delay": "3.5s" } as React.CSSProperties}
          >
            Requirement &amp; Security Assurance
          </p>

          <div
            className="sg-fade-in mt-8 h-px w-64 max-w-full overflow-hidden bg-line"
            style={{ animationDelay: "0.4s" }}
          >
            <div className="sg-sweep h-full w-1/3 bg-accent" />
          </div>

          <p
            aria-live="polite"
            className="mt-4 h-4 font-mono text-[11.5px] text-ink-faint sm:text-[12px]"
          >
            {BOOT_LINES[Math.min(step, BOOT_LINES.length - 1)]}
            <span className="animate-pulse">_</span>
          </p>
        </div>
      </div>
    </div>
  );
}
