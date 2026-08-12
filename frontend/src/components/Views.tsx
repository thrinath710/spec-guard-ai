"use client";

import {
  AlertTriangle,
  CheckCircle2,
  ChevronRight,
  FileText,
  FlaskConical,
  GitCompareArrows,
  History,
  Download,
  Lightbulb,
  Loader2,
  RotateCw,
  Search,
  ShieldHalf,
  Trash2,
  Waypoints,
  X,
} from "lucide-react";
import { useMemo, useState } from "react";
import {
  AnalysisResult,
  AnalysisSummary,
  Requirement,
  scoreTone,
  SEVERITY_ORDER,
  Severity,
} from "@/lib/api";
import {
  Badge,
  Button,
  DistributionBar,
  EmptyState,
  MetricTile,
  Panel,
  PanelHeader,
  ReqTag,
  SeverityPill,
} from "./ui";

const SEV_BAR: Record<Severity, string> = {
  critical: "bg-critical",
  high: "bg-high",
  medium: "bg-medium",
  low: "bg-low",
};

function severityRank(severity: string) {
  const index = SEVERITY_ORDER.indexOf(severity as Severity);
  return index === -1 ? 99 : index;
}

export function DegradedBanner({ reason }: { reason?: string | null }) {
  return (
    <div className="flex items-start gap-3 rounded-md border border-medium/30 bg-medium/[0.08] px-4 py-3">
      <AlertTriangle size={17} className="mt-0.5 shrink-0 text-medium" />
      <div>
        <p className="text-[13px] font-semibold text-medium">
          Partial AI analysis
        </p>
        <p className="mt-0.5 text-[13px] leading-relaxed text-ink-dim">
          Some stages could not reach the AI provider
          {reason ? ` (${reason})` : ""} and fell back to rule-based checks, so
          those sections repeat generic wording and are less thorough than a
          full run.
        </p>
      </div>
    </div>
  );
}

/* ---------------- Dashboard ---------------- */

function ScoreCard({
  label,
  value,
  accent,
}: {
  label: string;
  value: number;
  accent: string;
}) {
  return (
    <div className="rounded-md border border-line bg-panel p-4">
      <div className="flex items-baseline justify-between">
        <span className="font-mono text-[11px] uppercase tracking-[0.09em] text-ink-muted">
          {label}
        </span>
        <span className={`text-2xl font-semibold ${scoreTone(value)}`}>
          {value}
        </span>
      </div>
      <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-panel-hier">
        <div
          className={`h-full rounded-full ${accent} transition-all duration-700`}
          style={{ width: `${value}%` }}
        />
      </div>
    </div>
  );
}

export function DashboardView({
  result,
  filename,
  onOpen,
  onExport,
  onRerun,
  exporting,
  rerunning,
}: {
  result: AnalysisResult;
  filename: string;
  onOpen: (view: "requirements" | "security" | "tests") => void;
  onExport?: () => void;
  onRerun?: () => void;
  exporting?: boolean;
  rerunning?: boolean;
}) {
  const issues = result.quality.flatMap((q) => q.issues);
  const securityBySeverity = SEVERITY_ORDER.map((sev) => ({
    label: sev,
    value: result.security_findings.filter((f) => f.severity === sev).length,
    className: SEV_BAR[sev],
  }));
  const qualityBySeverity = SEVERITY_ORDER.map((sev) => ({
    label: sev,
    value: issues.filter((i) => i.severity === sev).length,
    className: SEV_BAR[sev],
  }));

  const topConflicts = [...result.conflicts].sort(
    (a, b) => severityRank(a.severity) - severityRank(b.severity),
  );

  return (
    <div className="sg-fade-in space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3 border-b border-line pb-4">
        <div className="min-w-0">
          <h1 className="truncate text-[22px] font-semibold tracking-tight text-ink">
            {filename}
          </h1>
          <p className="mt-1 font-mono text-[12px] text-ink-muted">
            {result.requirements.length} requirements analyzed ·{" "}
            <span className="uppercase">{result.score.risk_level} risk</span>
          </p>
        </div>
        <div className="flex shrink-0 gap-2 print:hidden">
          {onRerun ? (
            <Button variant="secondary" onClick={onRerun} disabled={rerunning}>
              {rerunning ? (
                <Loader2 size={15} className="animate-spin" />
              ) : (
                <RotateCw size={15} />
              )}
              Re-run
            </Button>
          ) : null}
          {onExport ? (
            <Button variant="secondary" onClick={onExport} disabled={exporting}>
              {exporting ? (
                <Loader2 size={15} className="animate-spin" />
              ) : (
                <Download size={15} />
              )}
              Export report
            </Button>
          ) : null}
        </div>
      </div>

      {result.degraded ? (
        <DegradedBanner reason={result.degraded_reason} />
      ) : null}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <ScoreCard label="Overall" value={result.score.overall_score} accent="bg-accent" />
        <ScoreCard label="Quality" value={result.score.quality_score} accent="bg-ok" />
        <ScoreCard label="Security" value={result.score.security_score} accent="bg-critical" />
        <ScoreCard
          label="Testability"
          value={result.score.testability_score}
          accent="bg-medium"
        />
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
        <MetricTile label="Requirements" value={result.requirements.length} />
        <MetricTile
          label="Quality Issues"
          value={issues.length}
          tone={issues.length ? "text-medium" : ""}
        />
        <MetricTile
          label="Security"
          value={result.security_findings.length}
          tone={result.security_findings.length ? "text-critical" : ""}
        />
        <MetricTile
          label="Contradictions"
          value={result.conflicts.length}
          tone={result.conflicts.length ? "text-high" : ""}
        />
        <MetricTile label="Test Cases" value={result.test_cases.length} />
      </div>

      <div className="grid gap-5 lg:grid-cols-2">
        <Panel className="p-5">
          <p className="mb-3 font-mono text-[11px] uppercase tracking-[0.09em] text-ink-muted">
            Security findings by severity
          </p>
          {result.security_findings.length ? (
            <DistributionBar segments={securityBySeverity} />
          ) : (
            <p className="text-[13px] text-ink-muted">No security findings.</p>
          )}
          <button
            type="button"
            onClick={() => onOpen("security")}
            className="mt-4 flex items-center gap-1 text-[12px] text-accent hover:underline"
          >
            View all findings <ChevronRight size={13} />
          </button>
        </Panel>

        <Panel className="p-5">
          <p className="mb-3 font-mono text-[11px] uppercase tracking-[0.09em] text-ink-muted">
            Quality issues by severity
          </p>
          {issues.length ? (
            <DistributionBar segments={qualityBySeverity} />
          ) : (
            <p className="text-[13px] text-ink-muted">No quality issues.</p>
          )}
          <button
            type="button"
            onClick={() => onOpen("requirements")}
            className="mt-4 flex items-center gap-1 text-[12px] text-accent hover:underline"
          >
            View requirements <ChevronRight size={13} />
          </button>
        </Panel>
      </div>

      <Panel>
        <PanelHeader
          title="Contradictions"
          icon={<GitCompareArrows size={15} />}
          count={result.conflicts.length}
        />
        <div className="divide-y divide-line-soft">
          {topConflicts.map((conflict, index) => (
            <div
              key={`${conflict.requirement_id}-${conflict.related_requirement_id}-${index}`}
              className="flex flex-col gap-2 px-4 py-3.5 sm:flex-row sm:items-start sm:gap-4"
            >
              <div className="flex shrink-0 items-center gap-1.5">
                <ReqTag id={conflict.requirement_id} />
                <span className="text-[11px] text-ink-faint">vs</span>
                <ReqTag id={conflict.related_requirement_id} />
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-[13.5px] leading-relaxed text-ink-dim">
                  {conflict.reason}
                </p>
                {conflict.evidence ? (
                  <p className="mt-1 border-l-2 border-line pl-2.5 font-mono text-[11.5px] italic text-ink-faint">
                    {conflict.evidence}
                  </p>
                ) : null}
              </div>
              <SeverityPill severity={conflict.severity} />
            </div>
          ))}
          {!result.conflicts.length ? (
            <EmptyState
              icon={<CheckCircle2 size={26} />}
              title="No contradictions detected"
              hint="No pair of requirements was found to be mutually inconsistent."
            />
          ) : null}
        </div>
      </Panel>
    </div>
  );
}

/* ---------------- Requirements + drill-down ---------------- */

export function RequirementsView({ result }: { result: AnalysisResult }) {
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState<Requirement | null>(null);

  const qualityById = useMemo(
    () => new Map(result.quality.map((q) => [q.requirement_id, q])),
    [result.quality],
  );
  const securityById = useMemo(() => {
    const map = new Map<string, number>();
    result.security_findings.forEach((f) =>
      map.set(f.requirement_id, (map.get(f.requirement_id) ?? 0) + 1),
    );
    return map;
  }, [result.security_findings]);
  const filtered = result.requirements.filter(
    (r) =>
      !query ||
      r.text.toLowerCase().includes(query.toLowerCase()) ||
      r.id.toLowerCase().includes(query.toLowerCase()) ||
      r.category.toLowerCase().includes(query.toLowerCase()),
  );

  return (
    <div className="sg-fade-in space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-[20px] font-semibold tracking-tight text-ink">
          Requirements
        </h1>
        <div className="relative">
          <Search
            size={15}
            className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-ink-faint"
          />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Filter requirements…"
            className="w-64 rounded-DEFAULT border border-line bg-base py-2 pl-9 pr-3 text-[13px] text-ink placeholder:text-ink-faint focus:border-accent focus:outline-none"
          />
        </div>
      </div>

      <Panel className="overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[860px] text-left">
            <thead className="border-b border-line bg-panel-hi/60">
              <tr className="font-mono text-[10.5px] uppercase tracking-[0.09em] text-ink-muted">
                <th className="px-4 py-2.5">ID</th>
                <th className="px-4 py-2.5">Requirement</th>
                <th className="px-4 py-2.5">Category</th>
                <th className="px-4 py-2.5 text-center">Clarity</th>
                <th className="px-4 py-2.5 text-center">Complete</th>
                <th className="px-4 py-2.5 text-center">Testable</th>
                <th className="px-4 py-2.5 text-center">Findings</th>
                <th className="px-4 py-2.5" />
              </tr>
            </thead>
            <tbody className="divide-y divide-line-soft">
              {filtered.map((req) => {
                const quality = qualityById.get(req.id);
                const findings =
                  (quality?.issues.length ?? 0) + (securityById.get(req.id) ?? 0);
                return (
                  <tr
                    key={req.id}
                    onClick={() => setSelected(req)}
                    className="cursor-pointer transition-colors hover:bg-panel-hi/60"
                  >
                    <td className="px-4 py-3">
                      <ReqTag id={req.id} />
                    </td>
                    <td className="max-w-md px-4 py-3 text-[13.5px] text-ink-dim">
                      {req.text}
                    </td>
                    <td className="px-4 py-3">
                      <Badge>{req.category}</Badge>
                    </td>
                    {[
                      quality?.clarity_score,
                      quality?.completeness_score,
                      quality?.testability_score,
                    ].map((score, i) => (
                      <td
                        key={i}
                        className={`px-4 py-3 text-center font-mono text-[12px] ${
                          score === undefined ? "text-ink-faint" : scoreTone(score)
                        }`}
                      >
                        {score ?? "—"}
                      </td>
                    ))}
                    <td className="px-4 py-3 text-center">
                      <span
                        className={`font-mono text-[12px] ${
                          findings ? "text-medium" : "text-ink-faint"
                        }`}
                      >
                        {findings}
                      </span>
                    </td>
                    <td className="px-3 py-3 text-ink-faint">
                      <ChevronRight size={15} />
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        {!filtered.length ? (
          <EmptyState title="No requirements match this filter" />
        ) : null}
      </Panel>

      {selected ? (
        <RequirementDrawer
          requirement={selected}
          result={result}
          onClose={() => setSelected(null)}
        />
      ) : null}
    </div>
  );
}

/** Everything the engine produced for one requirement, in one place — the traceability view. */
function RequirementDrawer({
  requirement,
  result,
  onClose,
}: {
  requirement: Requirement;
  result: AnalysisResult;
  onClose: () => void;
}) {
  const quality = result.quality.find(
    (q) => q.requirement_id === requirement.id,
  );
  const security = result.security_findings.filter(
    (f) => f.requirement_id === requirement.id,
  );
  const edges = result.edge_cases.filter(
    (e) => e.requirement_id === requirement.id,
  );
  const tests = result.test_cases.filter(
    (t) => t.requirement_id === requirement.id,
  );
  const conflicts = result.conflicts.filter(
    (c) =>
      c.requirement_id === requirement.id ||
      c.related_requirement_id === requirement.id,
  );
  const improved = result.improved_requirements.find(
    (i) => i.requirement_id === requirement.id,
  );

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      <button
        type="button"
        aria-label="Close"
        onClick={onClose}
        className="absolute inset-0 bg-black/60 backdrop-blur-[2px]"
      />
      <aside className="sg-fade-in relative flex h-full w-full max-w-2xl flex-col border-l border-line bg-surface shadow-2xl">
        <header className="flex items-start justify-between gap-4 border-b border-line px-5 py-4">
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <ReqTag id={requirement.id} />
              <Badge>{requirement.category}</Badge>
            </div>
            <p className="mt-2 text-[15px] leading-relaxed text-ink">
              {requirement.text}
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-DEFAULT p-1.5 text-ink-muted hover:bg-white/[0.06] hover:text-ink"
          >
            <X size={17} />
          </button>
        </header>

        <div className="flex-1 space-y-5 overflow-y-auto px-5 py-5">
          {quality ? (
            <div className="grid grid-cols-3 gap-3">
              <MetricTile label="Clarity" value={quality.clarity_score} tone={scoreTone(quality.clarity_score)} />
              <MetricTile label="Complete" value={quality.completeness_score} tone={scoreTone(quality.completeness_score)} />
              <MetricTile label="Testable" value={quality.testability_score} tone={scoreTone(quality.testability_score)} />
            </div>
          ) : null}

          <DrawerSection
            title="Quality Issues"
            icon={<AlertTriangle size={15} />}
            count={quality?.issues.length ?? 0}
          >
            {quality?.issues.map((issue, i) => (
              <FindingCard
                key={i}
                severity={issue.severity}
                title={issue.title}
                description={issue.description}
                evidence={issue.evidence}
                recommendation={issue.recommendation}
              />
            ))}
          </DrawerSection>

          <DrawerSection
            title="Security Findings"
            icon={<ShieldHalf size={15} />}
            count={security.length}
          >
            {security.map((finding, i) => (
              <FindingCard
                key={i}
                severity={finding.severity}
                title={finding.category}
                description={finding.description}
                evidence={finding.evidence}
                recommendation={finding.recommendation}
              />
            ))}
          </DrawerSection>

          <DrawerSection
            title="Contradictions"
            icon={<GitCompareArrows size={15} />}
            count={conflicts.length}
          >
            {conflicts.map((conflict, i) => (
              <div key={i} className="rounded-DEFAULT border border-line bg-panel p-3">
                <div className="mb-1.5 flex items-center gap-1.5">
                  <ReqTag id={conflict.requirement_id} />
                  <span className="text-[11px] text-ink-faint">vs</span>
                  <ReqTag id={conflict.related_requirement_id} />
                  <SeverityPill severity={conflict.severity} />
                </div>
                <p className="text-[13px] leading-relaxed text-ink-dim">
                  {conflict.reason}
                </p>
              </div>
            ))}
          </DrawerSection>

          <DrawerSection
            title="Edge Cases"
            icon={<Waypoints size={15} />}
            count={edges.length}
          >
            {edges.map((edge, i) => (
              <div key={i} className="rounded-DEFAULT border border-line bg-panel p-3">
                <div className="flex items-start justify-between gap-3">
                  <h5 className="text-[13.5px] font-medium text-ink">
                    {edge.title}
                  </h5>
                  <SeverityPill severity={edge.priority} />
                </div>
                <p className="mt-1 text-[13px] leading-relaxed text-ink-muted">
                  {edge.scenario}
                </p>
                <p className="mt-1.5 text-[12.5px] text-ink-dim">
                  <span className="text-ink-faint">Expected: </span>
                  {edge.expected_behavior}
                </p>
              </div>
            ))}
          </DrawerSection>

          <DrawerSection
            title="Test Cases"
            icon={<FlaskConical size={15} />}
            count={tests.length}
          >
            {tests.map((test) => (
              <div key={test.id} className="rounded-DEFAULT border border-line bg-panel p-3">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-[11px] text-accent-soft">
                      {test.id}
                    </span>
                    <Badge>{test.category}</Badge>
                  </div>
                  <SeverityPill severity={test.priority} />
                </div>
                <h5 className="mt-1.5 text-[13.5px] font-medium text-ink">
                  {test.title}
                </h5>
                {test.steps.length ? (
                  <ol className="mt-2 list-decimal space-y-0.5 pl-5 text-[12.5px] text-ink-muted">
                    {test.steps.map((step, i) => (
                      <li key={i}>{step}</li>
                    ))}
                  </ol>
                ) : null}
                <p className="mt-2 text-[12.5px] text-ink-dim">
                  <span className="text-ink-faint">Expected: </span>
                  {test.expected_result}
                </p>
              </div>
            ))}
          </DrawerSection>

          {improved ? (
            <DrawerSection
              title="Improved Requirement"
              icon={<Lightbulb size={15} />}
            >
              <div className="rounded-DEFAULT border border-ok/25 bg-ok/[0.06] p-3">
                <p className="text-[13.5px] leading-relaxed text-ink">
                  {improved.improved_text}
                </p>
                {improved.rationale ? (
                  <p className="mt-2 text-[12.5px] text-ink-muted">
                    {improved.rationale}
                  </p>
                ) : null}
                {improved.remaining_questions.length ? (
                  <div className="mt-2.5 border-t border-line pt-2">
                    <p className="font-mono text-[10.5px] uppercase tracking-wider text-ink-faint">
                      Open questions
                    </p>
                    <ul className="mt-1 list-disc space-y-0.5 pl-4 text-[12.5px] text-ink-muted">
                      {improved.remaining_questions.map((q, i) => (
                        <li key={i}>{q}</li>
                      ))}
                    </ul>
                  </div>
                ) : null}
              </div>
            </DrawerSection>
          ) : null}
        </div>
      </aside>
    </div>
  );
}

function DrawerSection({
  title,
  icon,
  count,
  children,
}: {
  title: string;
  icon: React.ReactNode;
  count?: number;
  children: React.ReactNode;
}) {
  const isEmpty =
    count === 0 || (Array.isArray(children) && children.length === 0);
  return (
    <div>
      <div className="mb-2 flex items-center gap-2">
        <span className="text-ink-muted">{icon}</span>
        <h4 className="text-[12px] font-semibold uppercase tracking-[0.09em] text-ink-dim">
          {title}
        </h4>
        {count !== undefined ? (
          <span className="font-mono text-[11px] text-ink-faint">{count}</span>
        ) : null}
      </div>
      {isEmpty ? (
        <p className="text-[12.5px] text-ink-faint">None detected.</p>
      ) : (
        <div className="space-y-2">{children}</div>
      )}
    </div>
  );
}

function FindingCard({
  severity,
  title,
  description,
  evidence,
  recommendation,
}: {
  severity: string;
  title: string;
  description: string;
  evidence?: string;
  recommendation?: string;
}) {
  return (
    <div className="rounded-DEFAULT border border-line bg-panel p-3">
      <div className="flex items-start justify-between gap-3">
        <h5 className="text-[13.5px] font-medium text-ink">{title}</h5>
        <SeverityPill severity={severity} />
      </div>
      {description ? (
        <p className="mt-1 text-[13px] leading-relaxed text-ink-muted">
          {description}
        </p>
      ) : null}
      {evidence ? (
        <p className="mt-2 border-l-2 border-line pl-2.5 font-mono text-[11.5px] italic text-ink-faint">
          {evidence}
        </p>
      ) : null}
      {recommendation ? (
        <p className="mt-2 text-[12.5px] text-accent-soft">
          <span className="text-ink-faint">Fix: </span>
          {recommendation}
        </p>
      ) : null}
    </div>
  );
}

/* ---------------- Security ---------------- */

export function SecurityView({ result }: { result: AnalysisResult }) {
  const [severity, setSeverity] = useState<string>("all");
  const findings = useMemo(
    () =>
      [...result.security_findings]
        .filter((f) => severity === "all" || f.severity === severity)
        .sort((a, b) => severityRank(a.severity) - severityRank(b.severity)),
    [result.security_findings, severity],
  );

  return (
    <div className="sg-fade-in space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-[20px] font-semibold tracking-tight text-ink">
          Security Findings
        </h1>
        <div className="flex gap-1.5">
          {["all", ...SEVERITY_ORDER].map((level) => (
            <button
              key={level}
              type="button"
              onClick={() => setSeverity(level)}
              className={`rounded-full border px-3 py-1 font-mono text-[11px] uppercase tracking-wider transition-colors ${
                severity === level
                  ? "border-accent/40 bg-accent/15 text-accent-soft"
                  : "border-line text-ink-muted hover:text-ink"
              }`}
            >
              {level}
            </button>
          ))}
        </div>
      </div>

      <Panel>
        <PanelHeader
          title="Findings"
          icon={<ShieldHalf size={15} />}
          count={findings.length}
        />
        <div className="divide-y divide-line-soft">
          {findings.map((finding, index) => (
            <div key={index} className="px-4 py-3.5">
              <div className="flex flex-wrap items-center gap-2">
                <ReqTag id={finding.requirement_id} />
                <Badge>{finding.category}</Badge>
                <SeverityPill severity={finding.severity} />
              </div>
              <p className="mt-2 text-[13.5px] leading-relaxed text-ink-dim">
                {finding.description}
              </p>
              {finding.evidence ? (
                <p className="mt-1.5 border-l-2 border-line pl-2.5 font-mono text-[11.5px] italic text-ink-faint">
                  {finding.evidence}
                </p>
              ) : null}
              {finding.recommendation ? (
                <p className="mt-1.5 text-[12.5px] text-accent-soft">
                  <span className="text-ink-faint">Fix: </span>
                  {finding.recommendation}
                </p>
              ) : null}
            </div>
          ))}
          {!findings.length ? (
            <EmptyState
              icon={<CheckCircle2 size={26} />}
              title="No findings at this severity"
            />
          ) : null}
        </div>
      </Panel>
    </div>
  );
}

/* ---------------- Tests ---------------- */

export function TestsView({ result }: { result: AnalysisResult }) {
  const [category, setCategory] = useState("all");
  const categories = useMemo(
    () => ["all", ...new Set(result.test_cases.map((t) => t.category))],
    [result.test_cases],
  );
  const tests = result.test_cases.filter(
    (t) => category === "all" || t.category === category,
  );

  return (
    <div className="sg-fade-in space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-[20px] font-semibold tracking-tight text-ink">
          Generated Test Cases
        </h1>
        <div className="flex flex-wrap gap-1.5">
          {categories.map((cat) => (
            <button
              key={cat}
              type="button"
              onClick={() => setCategory(cat)}
              className={`rounded-full border px-3 py-1 font-mono text-[11px] uppercase tracking-wider transition-colors ${
                category === cat
                  ? "border-accent/40 bg-accent/15 text-accent-soft"
                  : "border-line text-ink-muted hover:text-ink"
              }`}
            >
              {cat}
            </button>
          ))}
        </div>
      </div>

      <div className="grid gap-3 lg:grid-cols-2">
        {tests.map((test) => (
          <Panel key={test.id} className="p-4">
            <div className="flex flex-wrap items-center gap-2">
              <span className="font-mono text-[11px] text-accent-soft">
                {test.id}
              </span>
              <ReqTag id={test.requirement_id} />
              <Badge>{test.category}</Badge>
              <SeverityPill severity={test.priority} />
            </div>
            <h3 className="mt-2 text-[14px] font-medium text-ink">
              {test.title}
            </h3>
            {test.preconditions.length ? (
              <p className="mt-1.5 text-[12px] text-ink-faint">
                Given: {test.preconditions.join("; ")}
              </p>
            ) : null}
            {test.steps.length ? (
              <ol className="mt-2 list-decimal space-y-0.5 pl-5 text-[12.5px] text-ink-muted">
                {test.steps.map((step, i) => (
                  <li key={i}>{step}</li>
                ))}
              </ol>
            ) : null}
            <p className="mt-2 border-t border-line pt-2 text-[12.5px] text-ink-dim">
              <span className="text-ink-faint">Expected: </span>
              {test.expected_result}
            </p>
          </Panel>
        ))}
      </div>
      {!tests.length ? <EmptyState title="No test cases in this category" /> : null}
    </div>
  );
}

/* ---------------- History ---------------- */

export function HistoryView({
  analyses,
  loading,
  onOpen,
  onRefresh,
  onDelete,
  onRerun,
}: {
  analyses: AnalysisSummary[];
  loading: boolean;
  onOpen: (id: string) => void;
  onRefresh: () => void;
  onDelete: (id: string) => Promise<void>;
  onRerun: (documentId: string) => Promise<void>;
}) {
  // Two-step delete: the first click arms the row, the second confirms. Avoids a modal for
  // an action that is easy to trigger by accident in a dense table.
  const [confirmingId, setConfirmingId] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  async function remove(id: string) {
    setDeletingId(id);
    try {
      await onDelete(id);
    } finally {
      setDeletingId(null);
      setConfirmingId(null);
    }
  }

  return (
    <div className="sg-fade-in space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-[20px] font-semibold tracking-tight text-ink">
          Analyses
        </h1>
        <button
          type="button"
          onClick={onRefresh}
          className="text-[12px] text-accent hover:underline"
        >
          Refresh
        </button>
      </div>

      <Panel className="overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[720px] text-left">
            <thead className="border-b border-line bg-panel-hi/60">
              <tr className="font-mono text-[10.5px] uppercase tracking-[0.09em] text-ink-muted">
                <th className="px-4 py-2.5">Document</th>
                <th className="px-4 py-2.5">Started</th>
                <th className="px-4 py-2.5">Status</th>
                <th className="px-4 py-2.5 text-center">Score</th>
                <th className="px-4 py-2.5">Risk</th>
                <th className="px-4 py-2.5 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line-soft">
              {analyses.map((item) => {
                const done = item.status === "completed";
                return (
                  <tr
                    key={item.id}
                    onClick={() => done && onOpen(item.id)}
                    className={`transition-colors ${
                      done
                        ? "cursor-pointer hover:bg-panel-hi/60"
                        : "opacity-70"
                    }`}
                  >
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <FileText size={15} className="shrink-0 text-ink-faint" />
                        <span className="truncate text-[13.5px] text-ink-dim">
                          {item.filename}
                        </span>
                      </div>
                    </td>
                    <td className="px-4 py-3 font-mono text-[12px] text-ink-muted">
                      {new Date(item.created_at).toLocaleString("en-GB", {
                        day: "2-digit",
                        month: "short",
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </td>
                    <td className="px-4 py-3">
                      <Badge tone={done ? "ok" : "neutral"}>{item.status}</Badge>
                    </td>
                    <td className="px-4 py-3 text-center">
                      {item.overall_score !== null ? (
                        <span
                          className={`font-mono text-[13px] font-semibold ${scoreTone(
                            item.overall_score,
                          )}`}
                        >
                          {item.overall_score}
                        </span>
                      ) : (
                        <span className="text-ink-faint">—</span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      {item.risk_level ? (
                        <SeverityPill severity={item.risk_level} />
                      ) : (
                        <span className="text-ink-faint">—</span>
                      )}
                    </td>
                    <td
                      className="px-3 py-3"
                      onClick={(event) => event.stopPropagation()}
                    >
                      <div className="flex items-center justify-end gap-1">
                        {confirmingId === item.id ? (
                          <>
                            <button
                              type="button"
                              onClick={() => void remove(item.id)}
                              disabled={deletingId === item.id}
                              className="rounded-DEFAULT border border-critical/30 bg-critical/10 px-2 py-1 text-[11px] font-medium text-critical hover:bg-critical/20 disabled:opacity-50"
                            >
                              {deletingId === item.id ? (
                                <Loader2 size={12} className="animate-spin" />
                              ) : (
                                "Confirm"
                              )}
                            </button>
                            <button
                              type="button"
                              onClick={() => setConfirmingId(null)}
                              className="rounded-DEFAULT px-2 py-1 text-[11px] text-ink-muted hover:text-ink"
                            >
                              Cancel
                            </button>
                          </>
                        ) : (
                          <button
                            type="button"
                            title="Delete this analysis"
                            aria-label="Delete this analysis"
                            onClick={() => setConfirmingId(item.id)}
                            className="rounded-DEFAULT p-1.5 text-ink-faint transition-colors hover:bg-critical/10 hover:text-critical"
                          >
                            <Trash2 size={15} />
                          </button>
                        )}
                        {confirmingId !== item.id ? (
                          <button
                            type="button"
                            title="Run this document again"
                            aria-label="Run this document again"
                            onClick={() => void onRerun(item.document_id)}
                            className="rounded-DEFAULT p-1.5 text-ink-faint transition-colors hover:bg-accent/10 hover:text-accent"
                          >
                            <RotateCw size={15} />
                          </button>
                        ) : null}
                        {done && confirmingId !== item.id ? (
                          <ChevronRight size={15} className="text-ink-faint" />
                        ) : null}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        {!analyses.length && !loading ? (
          <EmptyState
            icon={<History size={26} />}
            title="No analyses yet"
            hint="Upload a requirements document to run your first analysis."
          />
        ) : null}
        {loading ? <EmptyState title="Loading history…" /> : null}
      </Panel>
    </div>
  );
}
