"use client";

import { useCallback, useRef, useState } from "react";
import {
  AnalysisResult,
  AnalysisSummary,
  ApiError,
  api,
  StatusData,
} from "@/lib/api";
import { LiveAnalysis } from "@/components/LiveAnalysis";
import { MobileNav, Shell, ViewKey } from "@/components/Shell";
import { Splash } from "@/components/Splash";
import { UploadView } from "@/components/UploadView";
import {
  DashboardView,
  HistoryView,
  RequirementsView,
  SecurityView,
  TestsView,
} from "@/components/Views";

const POLL_INTERVAL_MS = 1000;
const POLL_TIMEOUT_MS = 6 * 60 * 1000;

export default function Home() {
  const [booted, setBooted] = useState(false);
  const [view, setView] = useState<ViewKey>("new");

  const [filename, setFilename] = useState("");
  const [analysisId, setAnalysisId] = useState<string | null>(null);
  const [status, setStatus] = useState<StatusData | null>(null);
  const [result, setResult] = useState<AnalysisResult | null>(null);

  const [busy, setBusy] = useState(false);
  const [cancelling, setCancelling] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [history, setHistory] = useState<AnalysisSummary[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);

  // Guards the poll loop so a cancelled or superseded run stops updating state.
  const activeRun = useRef<string | null>(null);

  const running =
    status?.status === "processing" || status?.status === "queued";

  const loadHistory = useCallback(async () => {
    setHistoryLoading(true);
    try {
      setHistory(await api.listAnalyses());
    } catch {
      // History is supplementary; a failure here should not disrupt the main flow.
    } finally {
      setHistoryLoading(false);
    }
  }, []);

  const navigate = useCallback(
    (next: ViewKey) => {
      setView(next);
      // Fetched when the tab is opened so it always reflects the latest runs.
      if (next === "history") void loadHistory();
    },
    [loadHistory],
  );

  const poll = useCallback(
    async (id: string) => {
      const deadline = Date.now() + POLL_TIMEOUT_MS;
      while (Date.now() < deadline) {
        if (activeRun.current !== id) return;
        const next = await api.status(id);
        if (activeRun.current !== id) return;
        setStatus(next);

        if (next.status === "completed") {
          setResult(await api.results(id));
          setView("dashboard");
          void loadHistory();
          return;
        }
        if (next.status === "failed") {
          throw new ApiError(next.error_message ?? "Analysis failed.");
        }
        await new Promise((resolve) => setTimeout(resolve, POLL_INTERVAL_MS));
      }
      throw new ApiError(
        "Analysis timed out. The backend may still be working — check the Analyses tab.",
      );
    },
    [loadHistory],
  );

  async function startAnalysis(file: File) {
    setBusy(true);
    setError(null);
    setResult(null);
    setStatus(null);
    try {
      const upload = await api.uploadDocument(file);
      setFilename(upload.filename);
      const started = await api.startAnalysis(upload.document_id);
      setAnalysisId(started.analysis_id);
      activeRun.current = started.analysis_id;
      setView("new");
      await poll(started.analysis_id);
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : "Something went wrong.",
      );
      activeRun.current = null;
      setStatus(null);
    } finally {
      setBusy(false);
      setCancelling(false);
    }
  }

  async function cancelAnalysis() {
    if (!analysisId) return;
    setCancelling(true);
    try {
      await api.cancel(analysisId);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not cancel.");
      setCancelling(false);
    }
  }

  const deleteAnalysis = useCallback(
    async (id: string) => {
      await api.deleteAnalysis(id);
      setHistory((prev) => prev.filter((item) => item.id !== id));
      // Clear the open result if the analysis being viewed was the one deleted.
      setResult((prev) => (analysisId === id ? null : prev));
      if (analysisId === id) {
        setAnalysisId(null);
        setFilename("");
      }
    },
    [analysisId],
  );

  async function openAnalysis(id: string) {
    setBusy(true);
    setError(null);
    try {
      activeRun.current = null;
      const [loaded, summary] = await Promise.all([
        api.results(id),
        api.listAnalyses(),
      ]);
      setResult(loaded);
      setAnalysisId(id);
      setStatus(null);
      setFilename(
        summary.find((a) => a.id === id)?.filename ?? "Previous analysis",
      );
      setView("dashboard");
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : "Could not load analysis.",
      );
    } finally {
      setBusy(false);
    }
  }

  if (!booted) return <Splash onDone={() => setBooted(true)} />;

  const breadcrumb = running
    ? `Analysis / ${filename || "Running"}`
    : result
      ? `Analysis / ${filename}`
      : view === "history"
        ? "Analyses"
        : "New Analysis";

  return (
    <Shell
      view={view}
      onNavigate={navigate}
      breadcrumb={breadcrumb}
      hasResults={!!result}
      running={running}
    >
      <MobileNav view={view} onNavigate={navigate} hasResults={!!result} />

      {view === "new" ? (
        running && status ? (
          <LiveAnalysis
            filename={filename}
            status={status}
            onCancel={cancelAnalysis}
            cancelling={cancelling}
          />
        ) : (
          <UploadView onStart={startAnalysis} busy={busy} error={error} />
        )
      ) : null}

      {view === "dashboard" ? (
        result ? (
          <DashboardView
            result={result}
            filename={filename}
            onOpen={(next) => navigate(next)}
          />
        ) : (
          <UploadView onStart={startAnalysis} busy={busy} error={error} />
        )
      ) : null}

      {view === "requirements" && result ? (
        <RequirementsView result={result} />
      ) : null}
      {view === "security" && result ? <SecurityView result={result} /> : null}
      {view === "tests" && result ? <TestsView result={result} /> : null}

      {view === "history" ? (
        <HistoryView
          analyses={history}
          loading={historyLoading}
          onOpen={openAnalysis}
          onRefresh={loadHistory}
          onDelete={deleteAnalysis}
        />
      ) : null}
    </Shell>
  );
}
