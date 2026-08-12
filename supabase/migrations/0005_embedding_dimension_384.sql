-- OPTIONAL — only run this if you switch to a 384-dimensional embedding model
-- (BAAI/bge-small-en-v1.5), which needs roughly half the memory of the 768-dim default and
-- therefore fits smaller hosting plans.
--
-- Existing vectors cannot be reinterpreted at a different dimension, so the column is
-- recreated empty and previously analyzed documents lose only their stored vectors; their
-- requirements, findings and scores are untouched. Re-run an analysis to repopulate.

drop index if exists idx_document_chunks_embedding;

alter table document_chunks drop column if exists embedding;
alter table document_chunks add column embedding vector(384);

create index if not exists idx_document_chunks_embedding
  on document_chunks
  using ivfflat (embedding vector_cosine_ops)
  with (lists = 100);

drop function if exists match_document_chunks(vector, int, uuid);

create or replace function match_document_chunks(
  query_embedding vector(384),
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
