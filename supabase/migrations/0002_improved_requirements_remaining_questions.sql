alter table improved_requirements
  add column if not exists remaining_questions jsonb not null default '[]'::jsonb;
