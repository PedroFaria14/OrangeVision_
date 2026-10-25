-- Amostras privadas de teste/calibração. Não altera análises ou seus donos.
BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '30s';
CREATE TABLE IF NOT EXISTS orangevision_web.image_samples (
    id uuid PRIMARY KEY,
    user_id uuid NOT NULL REFERENCES orangevision_web.users(id),
    request_id uuid NOT NULL,
    source_hash text NOT NULL,
    filename varchar(120) NOT NULL,
    image_data bytea NOT NULL CHECK (octet_length(image_data) <= 5242880),
    width integer NOT NULL CHECK (width BETWEEN 1 AND 1600),
    height integer NOT NULL CHECK (height BETWEEN 1 AND 1600),
    state text NOT NULL CHECK (state IN ('received','queued','processing','awaiting_review','completed','not_evaluable','failed')),
    device_id uuid REFERENCES public.dispositivos(id),
    claim_id uuid UNIQUE,
    lease_hash text,
    claim_expires_at timestamptz,
    metrics jsonb,
    classification text CHECK (classification IN ('APROVADA','ATENCAO','REVISAR')),
    reason varchar(1000),
    calibration_version varchar(100),
    algorithm_version varchar(100),
    mask_data bytea CHECK (octet_length(mask_data) <= 1500000),
    result_hash text,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    started_at timestamptz,
    finished_at timestamptz,
    UNIQUE (user_id, request_id)
);
CREATE INDEX IF NOT EXISTS image_samples_owner_created ON orangevision_web.image_samples(user_id,created_at DESC,id);
CREATE INDEX IF NOT EXISTS image_samples_device_queue ON orangevision_web.image_samples(device_id,state,created_at);
COMMIT;
