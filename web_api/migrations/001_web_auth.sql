-- Migração ADITIVA. Revisar contra o schema existente e aplicar explicitamente.
-- Não executada no startup nem nas requests. Não modifica as tabelas do Pi.
BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '30s';
CREATE SCHEMA IF NOT EXISTS orangevision_web;
CREATE TABLE IF NOT EXISTS orangevision_web.users (
    id uuid PRIMARY KEY,
    name varchar(100) NOT NULL,
    email varchar(254) NOT NULL UNIQUE,
    password_hash text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS orangevision_web.sessions (
    token_hash text PRIMARY KEY,
    user_id uuid NOT NULL REFERENCES orangevision_web.users(id) ON DELETE CASCADE,
    csrf_token text NOT NULL,
    expires_at timestamptz NOT NULL
);
CREATE INDEX IF NOT EXISTS sessions_expiry ON orangevision_web.sessions(expires_at);
-- Sem FK para dispositivos: tipo/schema precisam ser confirmados no banco existente.
CREATE TABLE IF NOT EXISTS orangevision_web.device_access (
    user_id uuid NOT NULL REFERENCES orangevision_web.users(id) ON DELETE CASCADE,
    device_id uuid NOT NULL,
    PRIMARY KEY (user_id, device_id)
);
CREATE TABLE IF NOT EXISTS orangevision_web.auth_attempts (
    bucket text PRIMARY KEY,
    attempts integer NOT NULL,
    expires_at timestamptz NOT NULL
);
CREATE INDEX IF NOT EXISTS auth_attempts_expiry ON orangevision_web.auth_attempts(expires_at);
COMMIT;
