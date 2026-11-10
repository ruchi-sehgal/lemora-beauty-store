CREATE TABLE IF NOT EXISTS ingest_runs (
  run_id bigserial PRIMARY KEY,
  started_at timestamptz NOT NULL DEFAULT now(),
  embedded integer NOT NULL,
  already_fresh integer NOT NULL,
  seconds numeric(8,1) NOT NULL
);