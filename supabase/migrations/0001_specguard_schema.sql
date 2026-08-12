create extension if not exists vector;

create table if not exists documents (
  id uuid primary key default gen_random_uuid(),
  filename text not null,
  file_type text not null check (file_type in ('pdf', 'docx', 'txt', 'md')),
  file_size integer not null check (file_size > 0),
  storage_path text not null,
  status text not null default 'uploaded' check (status in ('uploaded', 'processing', 'processed', 'failed')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists requirements (
  id uuid primary key default gen_random_uuid(),
  document_id uuid not null references documents(id) on delete cascade,
  requirement_code text not null,
  text text not null,
  category text not null default 'Other',
  source_text text,
  source_location text,
  created_at timestamptz not null default now()
);

create table if not exists document_chunks (
  id uuid primary key default gen_random_uuid(),
  document_id uuid not null references documents(id) on delete cascade,
  requirement_id uuid references requirements(id) on delete set null,
  chunk_index integer not null,
  content text not null,
  metadata jsonb not null default '{}'::jsonb,
  embedding vector(768),
  created_at timestamptz not null default now()
);

create table if not exists analyses (
  id uuid primary key default gen_random_uuid(),
  document_id uuid not null references documents(id) on delete cascade,
  status text not null default 'queued' check (status in ('queued', 'processing', 'completed', 'failed')),
  progress integer not null default 0 check (progress between 0 and 100),
  current_stage text not null default 'queued',
  error_message text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists quality_findings (
  id uuid primary key default gen_random_uuid(),
  analysis_id uuid not null references analyses(id) on delete cascade,
  requirement_id uuid not null references requirements(id) on delete cascade,
  severity text not null check (severity in ('low', 'medium', 'high', 'critical')),
  finding_type text not null,
  title text not null,
  description text not null,
  evidence text not null,
  recommendation text not null,
  created_at timestamptz not null default now()
);

create table if not exists security_findings (
  id uuid primary key default gen_random_uuid(),
  analysis_id uuid not null references analyses(id) on delete cascade,
  requirement_id uuid not null references requirements(id) on delete cascade,
  severity text not null check (severity in ('low', 'medium', 'high', 'critical')),
  category text not null,
  description text not null,
  evidence text not null,
  recommendation text not null,
  created_at timestamptz not null default now()
);

create table if not exists requirement_conflicts (
  id uuid primary key default gen_random_uuid(),
  analysis_id uuid not null references analyses(id) on delete cascade,
  requirement_id uuid not null references requirements(id) on delete cascade,
  related_requirement_id uuid not null references requirements(id) on delete cascade,
  severity text not null default 'medium' check (severity in ('low', 'medium', 'high', 'critical')),
  reason text not null,
  evidence text not null,
  created_at timestamptz not null default now()
);

create table if not exists edge_cases (
  id uuid primary key default gen_random_uuid(),
  analysis_id uuid not null references analyses(id) on delete cascade,
  requirement_id uuid not null references requirements(id) on delete cascade,
  title text not null,
  scenario text not null,
  expected_behavior text not null,
  priority text not null default 'medium',
  created_at timestamptz not null default now()
);

create table if not exists test_cases (
  id uuid primary key default gen_random_uuid(),
  analysis_id uuid not null references analyses(id) on delete cascade,
  requirement_id uuid not null references requirements(id) on delete cascade,
  test_code text not null,
  title text not null,
  preconditions jsonb not null default '[]'::jsonb,
  steps jsonb not null default '[]'::jsonb,
  expected_result text not null,
  priority text not null default 'medium',
  category text not null,
  created_at timestamptz not null default now()
);

create table if not exists improved_requirements (
  id uuid primary key default gen_random_uuid(),
  analysis_id uuid not null references analyses(id) on delete cascade,
  requirement_id uuid not null references requirements(id) on delete cascade,
  original_text text not null,
  improved_text text not null,
  rationale text not null,
  created_at timestamptz not null default now()
);

create table if not exists analysis_scores (
  id uuid primary key default gen_random_uuid(),
  analysis_id uuid not null references analyses(id) on delete cascade,
  quality_score integer not null check (quality_score between 0 and 100),
  security_score integer not null check (security_score between 0 and 100),
  testability_score integer not null check (testability_score between 0 and 100),
  overall_score integer not null check (overall_score between 0 and 100),
  risk_level text not null check (risk_level in ('low', 'medium', 'high', 'critical')),
  created_at timestamptz not null default now()
);

create index if not exists idx_requirements_document_id on requirements(document_id);
create index if not exists idx_analyses_document_id on analyses(document_id);
create index if not exists idx_chunks_document_id on document_chunks(document_id);
create index if not exists idx_quality_analysis_id on quality_findings(analysis_id);
create index if not exists idx_security_analysis_id on security_findings(analysis_id);

create index if not exists idx_document_chunks_embedding
  on document_chunks
  using ivfflat (embedding vector_cosine_ops)
  with (lists = 100);

create or replace function match_document_chunks(
  query_embedding vector(768),
  match_count int default 5,
  filter_document_id uuid default null
)
returns table (
  id uuid,
  document_id uuid,
  requirement_id uuid,
  content text,
  metadata jsonb,
  similarity float
)
language sql stable
as $$
  select
    document_chunks.id,
    document_chunks.document_id,
    document_chunks.requirement_id,
    document_chunks.content,
    document_chunks.metadata,
    1 - (document_chunks.embedding <=> query_embedding) as similarity
  from document_chunks
  where document_chunks.embedding is not null
    and (filter_document_id is null or document_chunks.document_id = filter_document_id)
  order by document_chunks.embedding <=> query_embedding
  limit match_count;
$$;
