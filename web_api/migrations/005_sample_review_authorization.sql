-- Recuperação explícita de amostras locais, sem alterar o dono original.
BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '30s';
ALTER TABLE orangevision_web.image_samples ADD COLUMN IF NOT EXISTS review_authorization_id uuid
    REFERENCES orangevision_web.inspection_sessions(id);
COMMIT;
