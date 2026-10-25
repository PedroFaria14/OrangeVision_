-- ADITIVA. Aplicar explicitamente após revisão. Não atribui histórico a pessoas.
BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '30s';
CREATE TABLE IF NOT EXISTS orangevision_web.device_credentials (
    id uuid PRIMARY KEY,
    device_id uuid NOT NULL REFERENCES public.dispositivos(id),
    token_hash text NOT NULL UNIQUE,
    created_at timestamptz NOT NULL DEFAULT now(),
    revoked_at timestamptz
);
CREATE TABLE IF NOT EXISTS orangevision_web.inspection_sessions (
    id uuid PRIMARY KEY,
    user_id uuid NOT NULL REFERENCES orangevision_web.users(id),
    device_id uuid NOT NULL REFERENCES public.dispositivos(id),
    request_id uuid NOT NULL,
    state text NOT NULL CHECK (state IN ('pending','active','closing','closed','expired')),
    pairing_hash text NOT NULL UNIQUE,
    pairing_expires_at timestamptz NOT NULL,
    activation_id uuid,
    lease_hash text UNIQUE,
    started_at timestamptz,
    authorization_expires_at timestamptz,
    closed_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (user_id,request_id)
);
CREATE UNIQUE INDEX IF NOT EXISTS inspection_one_open_per_device
    ON orangevision_web.inspection_sessions(device_id)
    WHERE state IN ('pending','active','closing');
CREATE INDEX IF NOT EXISTS inspection_owner_created
    ON orangevision_web.inspection_sessions(user_id,created_at DESC);
ALTER TABLE public.analises ADD COLUMN IF NOT EXISTS inspection_session_id uuid
    REFERENCES orangevision_web.inspection_sessions(id);
ALTER TABLE public.analises ADD COLUMN IF NOT EXISTS calibration_version varchar(100);
ALTER TABLE public.analises ADD COLUMN IF NOT EXISTS classification_reason text;
CREATE INDEX IF NOT EXISTS analyses_inspection_timestamp
    ON public.analises(inspection_session_id,data_hora DESC);
CREATE TABLE IF NOT EXISTS orangevision_web.ingestion_receipts (
    analysis_id uuid PRIMARY KEY REFERENCES public.analises(id),
    inspection_session_id uuid NOT NULL REFERENCES orangevision_web.inspection_sessions(id),
    payload_hash text NOT NULL,
    received_at timestamptz NOT NULL DEFAULT now()
);
COMMIT;
