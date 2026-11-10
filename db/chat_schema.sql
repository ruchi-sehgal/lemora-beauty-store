CREATE TABLE IF NOT EXISTS conversations (
    conversation_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    visitor_id      text NOT NULL,
    created_at      timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS messages (
    message_id       bigserial PRIMARY KEY,
    conversation_id  uuid NOT NULL REFERENCES conversations ON DELETE CASCADE,
    role             text NOT NULL CHECK (role IN ('user', 'assistant')),
    content          text NOT NULL,
    recommended_skus text[] NOT NULL DEFAULT '{}',
    relaxed_filters  text[] NOT NULL DEFAULT '{}',
    prompt_version   text,
    model            text,
    latency_ms       integer,
    created_at       timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS messages_conversation_idx
    ON messages (conversation_id, created_at);

CREATE TABLE IF NOT EXISTS feedback (
    feedback_id     bigserial PRIMARY KEY,
    message_id      bigint NOT NULL REFERENCES messages ON DELETE CASCADE,
    verdict         text NOT NULL CHECK (verdict IN ('accepted', 'corrected', 'rejected')),
    correction_text text,
    csat_score      integer CHECK (csat_score BETWEEN 1 AND 5),
    created_at      timestamptz NOT NULL DEFAULT now()
);