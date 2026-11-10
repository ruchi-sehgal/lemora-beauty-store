CREATE TABLE IF NOT EXISTS error_log (
  error_id bigserial PRIMARY KEY,
  created_at timestamptz NOT NULL DEFAULT now(),
  kind text NOT NULL,
  detail text NOT NULL DEFAULT ''
);