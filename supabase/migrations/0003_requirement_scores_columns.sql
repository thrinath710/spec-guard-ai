alter table requirements
  add column if not exists clarity_score integer,
  add column if not exists completeness_score integer,
  add column if not exists testability_score integer;
