-- Tracks which generator batches have been applied, so the loader is safe to re-run.
CREATE TABLE IF NOT EXISTS etl_batch_control (
    batch_name  TEXT PRIMARY KEY,
    batch_type  TEXT NOT NULL CHECK (batch_type IN ('initial', 'delta')),
    row_counts  JSONB NOT NULL,
    loaded_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
