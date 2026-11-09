-- ADITIVA. Depende de 001, 002 e public.dispositivos. Aplicação manual.
-- Não atribui propriedade automaticamente a equipamentos cadastrados anteriormente.
BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '30s';

CREATE TABLE IF NOT EXISTS orangevision_web.managed_devices (
    device_id uuid PRIMARY KEY REFERENCES public.dispositivos(id),
    owner_id uuid NOT NULL REFERENCES orangevision_web.users(id),
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS managed_devices_owner_idx
    ON orangevision_web.managed_devices(owner_id);

CREATE TABLE IF NOT EXISTS orangevision_web.device_commands (
    user_id uuid NOT NULL REFERENCES orangevision_web.users(id),
    request_id uuid NOT NULL,
    operation text NOT NULL CHECK (operation IN ('create', 'rotate')),
    device_id uuid NOT NULL REFERENCES public.dispositivos(id),
    fingerprint text NOT NULL CHECK (length(fingerprint) = 64),
    credential_id uuid NOT NULL REFERENCES orangevision_web.device_credentials(id),
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (user_id, request_id)
);
COMMIT;
