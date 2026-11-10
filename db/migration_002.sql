ALTER TABLE messages
  ADD COLUMN IF NOT EXISTS input_tokens integer,
  ADD COLUMN IF NOT EXISTS output_tokens integer,
  ADD COLUMN IF NOT EXISTS model_requests integer;

CREATE TABLE IF NOT EXISTS search_log (
  search_id bigserial PRIMARY KEY,
  conversation_id uuid NOT NULL REFERENCES conversations(conversation_id) ON DELETE CASCADE,
  filters jsonb NOT NULL,
  relaxed text[] NOT NULL DEFAULT '{}',
  result_count integer NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS search_log_conv_idx ON search_log (conversation_id);

-- lets a shopper give a star rating without also giving a thumbs verdict (used in Block D)
ALTER TABLE feedback ALTER COLUMN verdict DROP NOT NULL;