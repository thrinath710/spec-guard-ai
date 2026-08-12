"use client";

import { ReactNode } from "react";
import { severityClasses } from "@/lib/api";

export function Panel({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <section
      className={`rounded-md border border-line bg-panel/90 ${className}`}
    >
      {children}
    </section>
  );
}

export function PanelHeader({
  title,
  icon,
  count,
  action,
}: {
  title: string;
  icon?: ReactNode;
  count?: number;
  action?: ReactNode;
}) {
  return (
    <div className="flex items-center justify-between gap-3 border-b border-line px-4 py-3">
      <div className="flex items-center gap-2.5 text-ink">
        {icon ? <span className="text-ink-muted">{icon}</span> : null}
        <h2 className="text-[13px] font-semibold uppercase tracking-[0.09em] text-ink-dim">
          {title}
        </h2>
        {count !== undefined ? (
          <span className="rounded-full border border-line bg-panel-hi px-2 py-0.5 font-mono text-[11px] text-ink-muted">
            {count}
          </span>
        ) : null}
      </div>
      {action}
    </div>
  );
}

export function Badge({
  children,
  tone = "neutral",
}: {
  children: ReactNode;
  tone?: "neutral" | "accent" | "ok";
}) {
  const tones = {
    neutral: "border-line bg-panel-hi text-ink-muted",
    accent: "border-accent/30 bg-accent/10 text-accent-soft",
    ok: "border-ok/30 bg-ok/10 text-ok",
  } as const;
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2 py-0.5 font-mono text-[10px] uppercase tracking-wider ${tones[tone]}`}
    >
      {children}
    </span>
  );
}

export function SeverityPill({ severity }: { severity: string }) {
  return (
    <span
      className={`inline-flex shrink-0 items-center rounded-full border px-2 py-0.5 font-mono text-[10px] font-medium uppercase tracking-wider ${severityClasses(
        severity,
      )}`}
    >
      {severity}
    </span>
  );
}

export function ReqTag({ id }: { id: string }) {
  return (
    <span className="shrink-0 rounded border border-line bg-base px-1.5 py-0.5 font-mono text-[11px] text-accent-soft">
      {id}
    </span>
  );
}

export function EmptyState({
  icon,
  title,
  hint,
}: {
  icon?: ReactNode;
  title: string;
  hint?: string;
}) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 px-6 py-14 text-center">
      {icon ? <div className="text-ink-faint">{icon}</div> : null}
      <p className="text-sm font-medium text-ink-dim">{title}</p>
      {hint ? <p className="max-w-md text-[13px] text-ink-muted">{hint}</p> : null}
    </div>
  );
}

export function Button({
  children,
  onClick,
  variant = "primary",
  disabled,
  type = "button",
  className = "",
}: {
  children: ReactNode;
  onClick?: () => void;
  variant?: "primary" | "secondary" | "ghost" | "danger";
  disabled?: boolean;
  type?: "button" | "submit";
  className?: string;
}) {
  const variants = {
    primary:
      "bg-accent text-white hover:bg-accent/90 disabled:bg-accent/40 disabled:text-white/60",
    secondary:
      "border border-line bg-white/[0.03] text-ink hover:bg-white/[0.07] disabled:opacity-50",
    ghost: "text-ink-muted hover:bg-white/[0.05] hover:text-ink disabled:opacity-50",
    danger:
      "border border-critical/25 bg-critical/10 text-critical hover:bg-critical/20 disabled:opacity-50",
  } as const;
  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      className={`inline-flex items-center justify-center gap-2 rounded-DEFAULT px-3.5 py-2 text-[13px] font-medium transition-colors disabled:cursor-not-allowed focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent ${variants[variant]} ${className}`}
    >
      {children}
    </button>
  );
}

export function MetricTile({
  label,
  value,
  hint,
  tone = "",
}: {
  label: string;
  value: ReactNode;
  hint?: string;
  tone?: string;
}) {
  return (
    <div className="rounded-md border border-line bg-panel px-4 py-3">
      <p className="font-mono text-[11px] uppercase tracking-[0.09em] text-ink-muted">
        {label}
      </p>
      <p className={`mt-1.5 text-2xl font-semibold tracking-tight ${tone || "text-ink"}`}>
        {value}
      </p>
      {hint ? <p className="mt-0.5 text-[12px] text-ink-faint">{hint}</p> : null}
    </div>
  );
}

/** Horizontal distribution bar — used for severity and category breakdowns. */
export function DistributionBar({
  segments,
}: {
  segments: { label: string; value: number; className: string }[];
}) {
  const total = segments.reduce((sum, s) => sum + s.value, 0);
  if (!total) return null;
  return (
    <div>
      <div className="flex h-2 w-full overflow-hidden rounded-full bg-panel-hi">
        {segments
          .filter((s) => s.value > 0)
          .map((s) => (
            <div
              key={s.label}
              className={s.className}
              style={{ width: `${(s.value / total) * 100}%` }}
              title={`${s.label}: ${s.value}`}
            />
          ))}
      </div>
      <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1">
        {segments
          .filter((s) => s.value > 0)
          .map((s) => (
            <span
              key={s.label}
              className="flex items-center gap-1.5 font-mono text-[11px] text-ink-muted"
            >
              <span className={`h-2 w-2 rounded-full ${s.className}`} />
              {s.label} {s.value}
            </span>
          ))}
      </div>
    </div>
  );
}
