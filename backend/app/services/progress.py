"""Live pipeline progress and execution log for an in-flight analysis.

The analysis runs in a background thread while the browser polls for status, so stage
transitions are held in memory for instant reads and flushed to the database at stage
boundaries. That keeps the live view responsive without adding a database round trip to
every log line.
"""

import logging
import threading
from collections.abc import Callable
from contextvars import ContextVar

from backend.app.models import (
    AnalysisStatus,
    LogEvent,
    LogLevel,
    StageInfo,
    StageStatus,
    utc_now,
)

logger = logging.getLogger(__name__)

MAX_EVENTS = 400

# The pipeline as the user sees it. Each entry maps to real work in workflow.py - nothing
# here is decorative, and the weights are used to derive overall percentage.
PIPELINE: list[tuple[str, str, str, int]] = [
    ("initialization", "Initialization", "Loading document and extracting text.", 8),
    (
        "analysis",
        "Requirement Analysis",
        "Extracting requirements and assessing clarity, completeness and contradictions.",
        34,
    ),
    (
        "rag",
        "Embedding & Retrieval",
        "Generating vectors and retrieving related requirements from pgvector.",
        16,
    ),
    (
        "security_tests",
        "Security & Test Generation",
        "Identifying security gaps and generating test cases and rewrites.",
        30,
    ),
    ("scoring", "Scoring", "Computing deterministic quality and risk scores.", 6),
    ("persistence", "Report Generation", "Persisting results and building the report.", 6),
]


class AnalysisCancelled(RuntimeError):
    """Raised inside the workflow when the user aborts a running analysis."""


class ProgressTracker:
    def __init__(self, analysis_id: str, on_flush: Callable[["ProgressTracker"], None] | None = None) -> None:
        self.analysis_id = analysis_id
        self._lock = threading.Lock()
        self._on_flush = on_flush
        self._cancelled = threading.Event()
        self.stages: list[StageInfo] = [
            StageInfo(key=key, label=label, description=description)
            for key, label, description, _ in PIPELINE
        ]
        self._weights = {key: weight for key, _, _, weight in PIPELINE}
        self.events: list[LogEvent] = []

    # ---- cancellation ----

    def cancel(self) -> None:
        self._cancelled.set()

    @property
    def cancelled(self) -> bool:
        return self._cancelled.is_set()

    def raise_if_cancelled(self) -> None:
        if self._cancelled.is_set():
            raise AnalysisCancelled("Analysis was cancelled.")

    # ---- logging ----

    def log(self, message: str, level: LogLevel = LogLevel.info, stage: str | None = None) -> None:
        with self._lock:
            self.events.append(LogEvent(level=level, stage=stage, message=message))
            # Bounded so a pathological document cannot grow the log without limit.
            if len(self.events) > MAX_EVENTS:
                del self.events[: len(self.events) - MAX_EVENTS]

    # ---- stage transitions ----

    def _stage(self, key: str) -> StageInfo | None:
        return next((stage for stage in self.stages if stage.key == key), None)

    def start(self, key: str, message: str | None = None) -> None:
        self.raise_if_cancelled()
        stage = self._stage(key)
        if stage:
            stage.status = StageStatus.running
            stage.started_at = utc_now()
            stage.progress = 0
            self.log(message or f"{stage.label} started.", LogLevel.info, key)
        self.flush()

    def update(self, key: str, progress: int, message: str | None = None) -> None:
        stage = self._stage(key)
        if stage:
            stage.progress = max(0, min(100, progress))
            if message:
                self.log(message, LogLevel.info, key)

    def complete(self, key: str, message: str | None = None) -> None:
        stage = self._stage(key)
        if stage:
            stage.status = StageStatus.completed
            stage.progress = 100
            stage.finished_at = utc_now()
            self.log(message or f"{stage.label} completed.", LogLevel.success, key)
        self.flush()

    def fail(self, key: str, message: str) -> None:
        stage = self._stage(key)
        if stage:
            stage.status = StageStatus.failed
            stage.finished_at = utc_now()
        self.log(message, LogLevel.error, key)
        self.flush()

    def warn(self, message: str, stage: str | None = None) -> None:
        self.log(message, LogLevel.warning, stage)

    def skip_remaining(self, reason: str) -> None:
        for stage in self.stages:
            if stage.status in (StageStatus.pending, StageStatus.running):
                stage.status = StageStatus.skipped
        self.log(reason, LogLevel.warning)
        self.flush()

    # ---- derived values ----

    @property
    def overall_progress(self) -> int:
        total = sum(self._weights.values()) or 1
        earned = sum(
            self._weights.get(stage.key, 0) * (stage.progress / 100) for stage in self.stages
        )
        return int(round(earned / total * 100))

    @property
    def current_stage(self) -> str:
        running = next((s for s in self.stages if s.status == StageStatus.running), None)
        if running:
            return running.key
        if all(s.status == StageStatus.completed for s in self.stages):
            return "completed"
        pending = next((s for s in self.stages if s.status == StageStatus.pending), None)
        return pending.key if pending else "completed"

    def flush(self) -> None:
        if self._on_flush is None:
            return
        try:
            self._on_flush(self)
        except Exception as exc:  # noqa: BLE001
            # Progress reporting must never be able to fail an otherwise healthy analysis.
            logger.warning("Failed to persist analysis progress: %s", exc)


# The tracker for the analysis running on this thread. Exposed as a context variable so deep
# call sites - notably the LLM client waiting out a rate-limit window - can report progress
# without threading a tracker argument through every function between here and there.
current_tracker: ContextVar["ProgressTracker | None"] = ContextVar(
    "current_tracker", default=None
)


def report(message: str, level: LogLevel = LogLevel.info, stage: str | None = None) -> None:
    """Log to whichever analysis is running on this thread, if any."""
    tracker = current_tracker.get()
    if tracker is not None:
        tracker.log(message, level, stage)


def report_stage_progress(stage: str, progress: int, message: str | None = None) -> None:
    tracker = current_tracker.get()
    if tracker is not None:
        tracker.update(stage, progress, message)
        tracker.flush()


# Live trackers for analyses currently running in this process, so status polls read fresh
# in-memory state instead of the last database flush.
_active: dict[str, ProgressTracker] = {}
_active_lock = threading.Lock()


def register(tracker: ProgressTracker) -> None:
    with _active_lock:
        _active[tracker.analysis_id] = tracker


def unregister(analysis_id: str) -> None:
    with _active_lock:
        _active.pop(analysis_id, None)


def get_tracker(analysis_id: str) -> ProgressTracker | None:
    with _active_lock:
        return _active.get(analysis_id)


def cancel_analysis(analysis_id: str) -> bool:
    tracker = get_tracker(analysis_id)
    if tracker is None:
        return False
    tracker.cancel()
    return True


def status_for(analysis_id: str, fallback_status: AnalysisStatus) -> dict | None:
    """Live status straight from memory, used while an analysis is still running."""
    tracker = get_tracker(analysis_id)
    if tracker is None:
        return None
    return {
        "status": fallback_status.value,
        "progress": tracker.overall_progress,
        "current_stage": tracker.current_stage,
        "stages": [stage.model_dump(mode="json") for stage in tracker.stages],
        "events": [event.model_dump(mode="json") for event in tracker.events],
    }
