-- Per-stage pipeline progress and the execution log shown in the live analysis view.
-- Stored on the analyses row (rather than as separate tables) because both are always read
-- and written together with the analysis itself, and neither is queried independently.
alter table analyses
  add column if not exists stages jsonb not null default '[]'::jsonb,
  add column if not exists events jsonb not null default '[]'::jsonb,
  add column if not exists completed_at timestamptz;

create index if not exists idx_analyses_created_at on analyses(created_at desc);
