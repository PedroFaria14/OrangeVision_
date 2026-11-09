-- ADITIVA. Depende de 001–005 e public.analises. Não publica resultados antigos.
BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '30s';
ALTER TABLE orangevision_web.image_samples
    ADD COLUMN IF NOT EXISTS analysis_id uuid REFERENCES public.analises(id);
CREATE UNIQUE INDEX IF NOT EXISTS image_samples_analysis_unique
    ON orangevision_web.image_samples(analysis_id) WHERE analysis_id IS NOT NULL;
COMMIT;
