ALTER TABLE errors ADD COLUMN IF NOT EXISTS event_id UUID;
CREATE UNIQUE INDEX IF NOT EXISTS uq_errors_event_id ON errors (event_id);
