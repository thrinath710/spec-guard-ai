"use client";

import {
  AlertCircle,
  FileText,
  Loader2,
  Sparkles,
  UploadCloud,
} from "lucide-react";
import { ChangeEvent, DragEvent, useRef, useState } from "react";
import { Button, Panel } from "./ui";

const ACCEPTED = ".pdf,.docx,.txt,.md,.markdown";

const PIPELINE_BLURB = [
  "Requirements are extracted and scored for clarity, completeness and testability",
  "Vectors are stored in Supabase pgvector and related requirements retrieved",
  "Security gaps, contradictions, edge cases and test cases are generated",
];

export function UploadView({
  onStart,
  busy,
  error,
}: {
  onStart: (file: File) => void;
  busy: boolean;
  error: string | null;
}) {
  const [file, setFile] = useState<File | null>(null);
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  function pick(next: File | null) {
    if (next) setFile(next);
  }

  function onDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setDragging(false);
    pick(event.dataTransfer.files?.[0] ?? null);
  }

  return (
    <div className="sg-fade-in mx-auto max-w-3xl space-y-6 py-4">
      <div className="text-center">
        <h1 className="text-[26px] font-semibold tracking-tight text-ink">
          Analyze a requirements document
        </h1>
        <p className="mx-auto mt-2 max-w-xl text-[14px] leading-relaxed text-ink-muted">
          SpecGuard extracts individual requirements, then detects ambiguity,
          security gaps and contradictions before development begins.
        </p>
      </div>

      <Panel className="p-6">
        <div
          onDragOver={(e) => {
            e.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={onDrop}
          onClick={() => inputRef.current?.click()}
          className={`flex cursor-pointer flex-col items-center justify-center rounded-md border border-dashed px-6 py-12 text-center transition-colors ${
            dragging
              ? "border-accent bg-accent/[0.06]"
              : "border-line bg-base hover:border-accent/50 hover:bg-white/[0.02]"
          }`}
        >
          <div className="flex h-12 w-12 items-center justify-center rounded-full border border-line bg-panel">
            {file ? (
              <FileText size={22} className="text-accent" />
            ) : (
              <UploadCloud size={22} className="text-ink-muted" />
            )}
          </div>
          <p className="mt-3 max-w-full truncate text-[14px] font-medium text-ink">
            {file ? file.name : "Drop a document or click to browse"}
          </p>
          <p className="mt-1 font-mono text-[11px] uppercase tracking-wider text-ink-faint">
            PDF · DOCX · TXT · Markdown
          </p>
          <input
            ref={inputRef}
            type="file"
            accept={ACCEPTED}
            className="hidden"
            onChange={(e: ChangeEvent<HTMLInputElement>) =>
              pick(e.target.files?.[0] ?? null)
            }
          />
        </div>

        {error ? (
          <div className="mt-4 flex items-start gap-2.5 rounded-DEFAULT border border-critical/25 bg-critical/[0.08] px-3.5 py-2.5">
            <AlertCircle size={16} className="mt-0.5 shrink-0 text-critical" />
            <p className="text-[13px] leading-relaxed text-critical">{error}</p>
          </div>
        ) : null}

        <Button
          onClick={() => file && onStart(file)}
          disabled={!file || busy}
          className="mt-5 h-11 w-full"
        >
          {busy ? (
            <Loader2 size={16} className="animate-spin" />
          ) : (
            <Sparkles size={16} />
          )}
          {busy ? "Starting analysis" : "Start Analysis"}
        </Button>
      </Panel>

      <div className="grid gap-3 sm:grid-cols-3">
        {PIPELINE_BLURB.map((text, index) => (
          <div
            key={index}
            className="rounded-md border border-line bg-panel/60 p-4"
          >
            <span className="font-mono text-[11px] text-accent">
              0{index + 1}
            </span>
            <p className="mt-1.5 text-[12.5px] leading-relaxed text-ink-muted">
              {text}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}
