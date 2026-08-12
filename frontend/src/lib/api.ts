const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

// True when the app was built without NEXT_PUBLIC_API_BASE_URL. On a deployed site that
// default points at the visitor's own machine, so the failure needs naming explicitly
// rather than reading as "the backend is down".
const USING_FALLBACK_BASE = !process.env.NEXT_PUBLIC_API_BASE_URL;

export type ApiEnvelope<T> = {
  success: boolean;
  data?: T;
  error?: { code: string; message: string };
};

export type Severity = "low" | "medium" | "high" | "critical";
export type StageStatus =
  | "pending"
  | "running"
  | "completed"
  | "failed"
  | "skipped";
export type AnalysisState = "queued" | "processing" | "completed" | "failed";

export type UploadData = {
  document_id: string;
  filename: string;
  file_type: string;
  file_size: number;
  status: string;
};

export type StartData = {
  analysis_id: string;
  document_id: string;
  filename: string;
  status: string;
};

export type StageInfo = {
  key: string;
  label: string;
  description: string;
  status: StageStatus;
  progress: number;
  started_at?: string | null;
  finished_at?: string | null;
};

export type LogEvent = {
  timestamp: string;
  level: "info" | "success" | "warning" | "error";
  stage?: string | null;
  message: string;
};

export type StatusData = {
  analysis_id: string;
  status: AnalysisState;
  progress: number;
  current_stage: string;
  error_message?: string | null;
  stages: StageInfo[];
  events: LogEvent[];
  created_at?: string;
  completed_at?: string | null;
};

export type Requirement = {
  id: string;
  text: string;
  category: string;
  source_text?: string | null;
  source_location?: string | null;
};

export type RequirementIssue = {
  severity: Severity;
  type: string;
  title: string;
  description: string;
  evidence: string;
  recommendation: string;
};

export type QualityAnalysis = {
  requirement_id: string;
  clarity_score: number;
  completeness_score: number;
  testability_score: number;
  issues: RequirementIssue[];
};

export type SecurityFinding = {
  requirement_id: string;
  severity: Severity;
  category: string;
  description: string;
  evidence: string;
  recommendation: string;
};

export type RequirementConflict = {
  requirement_id: string;
  related_requirement_id: string;
  reason: string;
  evidence: string;
  severity: Severity;
};

export type EdgeCase = {
  requirement_id: string;
  title: string;
  scenario: string;
  expected_behavior: string;
  priority: string;
};

export type TestCase = {
  id: string;
  requirement_id: string;
  title: string;
  preconditions: string[];
  steps: string[];
  expected_result: string;
  priority: string;
  category: string;
};

export type ImprovedRequirement = {
  requirement_id: string;
  original_text: string;
  improved_text: string;
  rationale: string;
  remaining_questions: string[];
};

export type AnalysisScore = {
  quality_score: number;
  security_score: number;
  testability_score: number;
  overall_score: number;
  risk_level: string;
};

export type AnalysisResult = {
  requirements: Requirement[];
  quality: QualityAnalysis[];
  security_findings: SecurityFinding[];
  conflicts: RequirementConflict[];
  edge_cases: EdgeCase[];
  test_cases: TestCase[];
  improved_requirements: ImprovedRequirement[];
  score: AnalysisScore;
  degraded?: boolean;
  degraded_reason?: string | null;
};

export type AnalysisSummary = {
  id: string;
  document_id: string;
  status: AnalysisState;
  progress: number;
  current_stage: string;
  created_at: string;
  completed_at?: string | null;
  error_message?: string | null;
  filename: string;
  file_type: string;
  overall_score: number | null;
  risk_level: string | null;
};

export type Statistics = {
  totals: {
    requirements: number;
    quality_issues: number;
    security_findings: number;
    conflicts: number;
    edge_cases: number;
    test_cases: number;
    improved_requirements: number;
  };
  score: AnalysisScore | null;
  quality_by_severity: Record<string, number>;
  security_by_severity: Record<string, number>;
  security_by_category: Record<string, number>;
  tests_by_category: Record<string, number>;
  requirements_by_category: Record<string, number>;
  degraded: boolean;
  degraded_reason: string | null;
};

export class ApiError extends Error {
  code: string;
  constructor(message: string, code = "REQUEST_FAILED") {
    super(message);
    this.code = code;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, init);
  } catch {
    const isDeployed =
      typeof window !== "undefined" &&
      !["localhost", "127.0.0.1"].includes(window.location.hostname);
    if (isDeployed && USING_FALLBACK_BASE) {
      throw new ApiError(
        `This site was built without NEXT_PUBLIC_API_BASE_URL, so it is trying to reach ` +
          `${API_BASE} — your own machine rather than the server. Set that variable on the ` +
          `web service to the API's URL (ending in /api/v1) and redeploy.`,
        "CONFIG",
      );
    }
    throw new ApiError(
      `Cannot reach the SpecGuard API at ${API_BASE}. ` +
        (isDeployed
          ? "The API may be asleep or restarting — wait ~30s and retry."
          : "Start the backend with: uvicorn backend.app.main:app --port 8000"),
      "NETWORK",
    );
  }
  let payload: ApiEnvelope<T>;
  try {
    payload = (await response.json()) as ApiEnvelope<T>;
  } catch {
    throw new ApiError(`Unexpected response (HTTP ${response.status}).`);
  }
  if (!response.ok || !payload.success) {
    throw new ApiError(
      payload.error?.message ?? `Request failed with status ${response.status}`,
      payload.error?.code,
    );
  }
  return payload.data as T;
}

export const api = {
  health: () => request<{ status: string }>("/health"),

  uploadDocument: (file: File) => {
    const body = new FormData();
    body.append("file", file);
    return request<UploadData>("/documents/upload", { method: "POST", body });
  },

  startAnalysis: (documentId: string) =>
    request<StartData>("/analyses", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ document_id: documentId }),
    }),

  status: (id: string) => request<StatusData>(`/analyses/${id}/status`),

  results: (id: string) => request<AnalysisResult>(`/analyses/${id}/results`),

  statistics: (id: string) => request<Statistics>(`/analyses/${id}/statistics`),

  listAnalyses: () =>
    request<{ analyses: AnalysisSummary[] }>("/analyses").then((d) => d.analyses),

  // Server sets Content-Disposition; the blob is turned into a download by the caller.
  exportUrl: (id: string) => `${API_BASE}/analyses/${id}/export`,

  downloadReport: async (id: string, filename: string) => {
    const response = await fetch(`${API_BASE}/analyses/${id}/export`);
    if (!response.ok) throw new ApiError("Could not generate the report.");
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `specguard_${filename.replace(/\.[^.]+$/, "")}.md`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  },

  deleteAnalysis: (id: string) =>
    request<{ analysis_id: string; deleted: boolean }>(`/analyses/${id}`, {
      method: "DELETE",
    }),

  cancel: (id: string) =>
    request<{ analysis_id: string; cancelling: boolean }>(
      `/analyses/${id}/cancel`,
      { method: "POST" },
    ),
};

export const SEVERITY_ORDER: Severity[] = ["critical", "high", "medium", "low"];

export function severityClasses(severity: string) {
  switch (severity?.toLowerCase()) {
    case "critical":
      return "text-critical border-critical/30 bg-critical/10";
    case "high":
      return "text-high border-high/30 bg-high/10";
    case "medium":
      return "text-medium border-medium/30 bg-medium/10";
    default:
      return "text-low border-low/30 bg-low/10";
  }
}

export function scoreTone(score: number) {
  if (score >= 75) return "text-ok";
  if (score >= 55) return "text-medium";
  if (score >= 40) return "text-high";
  return "text-critical";
}
