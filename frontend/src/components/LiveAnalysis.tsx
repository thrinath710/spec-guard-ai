"use client";

import {
  AlertTriangle,
  Check,
  CircleDashed,
  FileSearch,
  Loader2,
  Network,
  Radar,
  ScrollText,
  ShieldHalf,
  SlashIcon,
  Sparkles,
} from "lucide-react";
import { ReactNode, useEffect, useRef, useState } from "react";
import type { LogEvent, StageInfo, StatusData } from "@/lib/api";
import { Button, Panel, PanelHeader } from "./ui";

const STAGE_ICONS: Record<string, ReactNode> = {
  initialization: <FileSearch size={19} />,
  analysis: <Sparkles size={19} />,
  rag: <Network size={19} />,
  security_tests: <ShieldHalf size={19} />,
  scoring: <Radar size={19} />,
  persistence: <ScrollText size={19} />,
};

function ProgressRing({
  progress,
  status,
}: {
  progress: number;
  status: string;
}) {
  const radius = 45;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (Math.min(100, Math.max(0, progress)) / 100) * circumference;
  return (
    <div className="relative h-44 w-44">
      <svg className="h-full w-full -rotate-90" viewBox="0 0 100 100">
        <circle
          cx="50"
          cy="50"
          r={radius}
          fill="none"
          stroke="#1b2027"
          strokeWidth="7"
        />
        <circle
          cx="50"
          cy="50"
          r={radius}
          fill="none"
          stroke="#4b8eff"
          strokeWidth="7"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          style={{ transition: "stroke-dashoffset 0.6s ease" }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-4xl font-bold tracking-tight text-ink">
          {progress}
          <span className="text-2xl text-ink-muted">%</span>
        </span>
        <span className="mt-0.5 font-mono text-[11px] uppercase tracking-wider text-ink-muted">
          {status}
        </span>
      </div>
    </div>
  );
}

function StageRow({ stage }: { stage: StageInfo }) {
  const isRunning = stage.status === "running";
  const isDone = stage.status === "completed";
  const isFailed = stage.status === "failed";
  const isSkipped = stage.status === "skipped";

  const circle = isDone
    ? "border-accent/30 bg-panel-hier text-accent"
    : isRunning
      ? "sg-pulse border-accent bg-accent/10 text-accent"
      : isFailed
        ? "border-critical/40 bg-critical/10 text-critical"
        : "border-line bg-base text-ink-faint";

  return (
    <div
      className={`relative flex items-start gap-4 ${
        stage.status === "pending" || isSkipped ? "opacity-45" : ""
      }`}
    >
      <div
        className={`z-10 flex h-11 w-11 shrink-0 items-center justify-center rounded-full border ${circle}`}
      >
        {isDone ? (
          <Check size={19} />
        ) : isRunning ? (
          <Loader2 size={19} className="animate-spin" />
        ) : isFailed ? (
          <AlertTriangle size={18} />
        ) : isSkipped ? (
          <SlashIcon size={16} />
        ) : (
          STAGE_ICONS[stage.key] ?? <CircleDashed size={18} />
        )}
      </div>

      <div className="min-w-0 flex-1 pt-1 pb-1">
        <div className="flex items-center justify-between gap-3">
          <h4
            className={`text-[15px] font-semibold ${
              isRunning ? "text-accent-soft" : "text-ink"
            }`}
          >
            {stage.label}
          </h4>
          <span className="shrink-0 font-mono text-[11px] text-ink-muted">
            {isDone
              ? "100%"
              : isRunning
                ? `${stage.progress}%`
                : isFailed
                  ? "Failed"
                  : isSkipped
                    ? "Skipped"
                    : "Pending"}
          </span>
        </div>
        <p className="mt-0.5 text-[13px] leading-relaxed text-ink-muted">
          {stage.description}
        </p>
        {isRunning ? (
          <div className="mt-2.5 h-1 w-full overflow-hidden rounded-full bg-panel-hier">
            <div
              className="h-full rounded-full bg-accent transition-all duration-500"
              style={{ width: `${stage.progress}%` }}
            />
          </div>
        ) : null}
      </div>
    </div>
  );
}

/** Ticking elapsed timer. The clock is only read inside the interval callback, never during
 *  render, so the component stays pure and the value updates predictably once per second. */
function useElapsedSeconds(startedAt?: string | null) {
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    if (!startedAt) return;
    const start = new Date(startedAt).getTime();
    const timer = setInterval(
      () => setElapsed(Math.max(0, Math.floor((Date.now() - start) / 1000))),
      1000,
    );
    return () => clearInterval(timer);
  }, [startedAt]);

  return startedAt ? elapsed : null;
}

function LogConsole({ events }: { events: LogEvent[] }) {
  const endRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    endRef.current?.scrollIntoView({ block: "end" });
  }, [events.length]);

  const toneFor = (level: string) =>
    level === "success"
      ? "text-ok"
      : level === "warning"
        ? "text-medium"
        : level === "error"
          ? "text-critical"
          : "text-ink-muted";

  return (
    <Panel className="flex min-h-[280px] flex-1 flex-col overflow-hidden">
      <PanelHeader
        title="Execution Log"
        icon={<ScrollText size={15} />}
        action={
          <span className="flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-wider text-accent">
            <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-accent" />
            Live
          </span>
        }
      />
      <div className="flex-1 space-y-1 overflow-y-auto bg-black/40 p-3 font-mono text-[11.5px] leading-relaxed">
        {events.length === 0 ? (
          <p className="text-ink-faint">Waiting for engine output…</p>
        ) : (
          events.map((event, index) => (
            <div key={index} className={toneFor(event.level)}>
              <span className="text-ink-faint">
                [
                {new Date(event.timestamp).toLocaleTimeString("en-GB", {
                  hour12: false,
                })}
                ]
              </span>{" "}
              {event.message}
            </div>
          ))
        )}
        <div ref={endRef} />
      </div>
    </Panel>
  );
}

export function LiveAnalysis({
  filename,
  status,
  onCancel,
  cancelling,
}: {
  filename: string;
  status: StatusData;
  onCancel: () => void;
  cancelling: boolean;
}) {
  const label =
    status.status === "processing"
      ? "Running"
      : status.status === "queued"
        ? "Queued"
        : status.status;

  const elapsed = useElapsedSeconds(status.created_at);

  return (
    <div className="sg-fade-in space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-4 border-b border-line pb-4">
        <div className="min-w-0">
          <h1 className="truncate text-[22px] font-semibold tracking-tight text-ink">
            {filename}
          </h1>
          <p className="mt-1 font-mono text-[12px] text-ink-muted">
            Analysis ID: {status.analysis_id.slice(0, 8)}
          </p>
        </div>
        <Button variant="danger" onClick={onCancel} disabled={cancelling}>
          {cancelling ? <Loader2 size={15} className="animate-spin" /> : null}
          {cancelling ? "Cancelling" : "Cancel Analysis"}
        </Button>
      </div>

      <div className="grid gap-5 lg:grid-cols-3">
        <div className="flex flex-col gap-5">
          <Panel className="flex flex-col items-center px-5 py-6">
            <p className="mb-4 self-start font-mono text-[11px] uppercase tracking-[0.09em] text-ink-muted">
              Overall Progress
            </p>
            <ProgressRing progress={status.progress} status={label} />
            {elapsed !== null ? (
              <p className="mt-5 font-mono text-[11px] text-ink-faint">
                Elapsed {Math.floor(elapsed / 60)}:
                {String(elapsed % 60).padStart(2, "0")}
              </p>
            ) : null}
          </Panel>
          <LogConsole events={status.events ?? []} />
        </div>

        <Panel className="p-5 lg:col-span-2">
          <p className="mb-5 font-mono text-[11px] uppercase tracking-[0.09em] text-ink-muted">
            Analysis Pipeline
          </p>
          <div className="relative">
            <div className="absolute bottom-4 left-[21px] top-4 w-px bg-line" />
            <div className="relative space-y-5">
              {(status.stages ?? []).map((stage) => (
                <StageRow key={stage.key} stage={stage} />
              ))}
              {(status.stages ?? []).length === 0 ? (
                <p className="text-[13px] text-ink-muted">Starting engine…</p>
              ) : null}
            </div>
          </div>
        </Panel>
      </div>
    </div>
  );
}
