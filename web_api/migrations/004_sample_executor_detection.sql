-- Aditiva: observabilidade da fila e evidência de detecção em amostras.
BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '30s';
CREATE TABLE IF NOT EXISTS orangevision_web.sample_executors (
    device_id uuid PRIMARY KEY REFERENCES public.dispositivos(id),
    last_seen_at timestamptz NOT NULL,
    state text NOT NULL CHECK (state IN ('starting','ready','error','stopped')),
    model_version varchar(100),
    message varchar(300)
);
ALTER TABLE orangevision_web.image_samples ADD COLUMN IF NOT EXISTS detection jsonb;
ALTER TABLE orangevision_web.image_samples ADD COLUMN IF NOT EXISTS source_inspection_id uuid REFERENCES orangevision_web.inspection_sessions(id);
ALTER TABLE orangevision_web.image_samples ADD COLUMN IF NOT EXISTS captured_at timestamptz;
COMMIT;
