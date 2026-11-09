-- ADITIVA. Requer 001–005 e 007. Não agenda chamadas nem adota resultados antigos.
BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '30s';
CREATE TABLE IF NOT EXISTS orangevision_web.sample_evaluations (
    id uuid PRIMARY KEY,
    sample_id uuid NOT NULL REFERENCES orangevision_web.image_samples(id),
    origin text NOT NULL CHECK (origin IN ('local','gemini')),
    run_key uuid NOT NULL,
    state text NOT NULL CHECK (state IN ('completed','awaiting_review','not_evaluable','failed')),
    classification text CHECK (classification IN ('APROVADA','ATENCAO','REVISAR')),
    reason varchar(1000) NOT NULL,
    criteria_version varchar(100) NOT NULL,
    model_version varchar(100),
    metrics jsonb,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    UNIQUE(sample_id,origin,run_key),
    CHECK ((state='completed') = (classification IS NOT NULL)),
    CHECK (origin='local' OR metrics IS NULL)
);
CREATE INDEX IF NOT EXISTS evaluations_sample_latest ON orangevision_web.sample_evaluations(sample_id,origin,created_at DESC,id);
CREATE TABLE IF NOT EXISTS orangevision_web.gemini_jobs (
    id uuid PRIMARY KEY,
    sample_id uuid NOT NULL REFERENCES orangevision_web.image_samples(id),
    user_id uuid NOT NULL REFERENCES orangevision_web.users(id),
    request_id uuid NOT NULL,
    state text NOT NULL DEFAULT 'queued' CHECK (state IN ('queued','running','retry_wait','completed','failed')),
    criteria_version varchar(100) NOT NULL,
    model_version varchar(100) NOT NULL,
    attempts integer NOT NULL DEFAULT 0 CHECK (attempts BETWEEN 0 AND 3),
    execution_token uuid,
    lease_expires_at timestamptz,
    next_attempt_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    error_code varchar(50),
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    UNIQUE(sample_id,request_id)
);
CREATE UNIQUE INDEX IF NOT EXISTS gemini_one_active_sample ON orangevision_web.gemini_jobs(sample_id)
    WHERE state IN ('queued','running','retry_wait');
CREATE INDEX IF NOT EXISTS gemini_pending ON orangevision_web.gemini_jobs(next_attempt_at,created_at)
    WHERE state IN ('queued','running','retry_wait');
CREATE TABLE IF NOT EXISTS orangevision_web.gemini_attempts (
    job_id uuid NOT NULL REFERENCES orangevision_web.gemini_jobs(id),
    attempt integer NOT NULL,
    user_id uuid NOT NULL REFERENCES orangevision_web.users(id),
    started_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    usage jsonb,
    outcome varchar(50),
    PRIMARY KEY(job_id,attempt)
);
CREATE INDEX IF NOT EXISTS gemini_attempt_budget ON orangevision_web.gemini_attempts(started_at,user_id);
CREATE TABLE IF NOT EXISTS orangevision_web.sample_decisions (
    id uuid PRIMARY KEY,
    sample_id uuid NOT NULL REFERENCES orangevision_web.image_samples(id),
    revision integer NOT NULL CHECK (revision>0),
    request_id uuid NOT NULL,
    user_id uuid NOT NULL REFERENCES orangevision_web.users(id),
    evaluation_id uuid REFERENCES orangevision_web.sample_evaluations(id),
    origin text NOT NULL CHECK (origin IN ('local','gemini','human')),
    classification text NOT NULL CHECK (classification IN ('APROVADA','ATENCAO','REVISAR')),
    reason varchar(1000) NOT NULL,
    fingerprint text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    UNIQUE(sample_id,revision), UNIQUE(sample_id,request_id)
);
-- Avaliação qualitativa confirmada não inventa medições locais.
ALTER TABLE public.analises ALTER COLUMN cor_media DROP NOT NULL,
    ALTER COLUMN regioes_anormais DROP NOT NULL, ALTER COLUMN circularidade DROP NOT NULL,
    ALTER COLUMN assimetria DROP NOT NULL, ALTER COLUMN score_visual DROP NOT NULL;
-- Decisões são append-only; a projeção muda a leitura, nunca reescreve o original.
CREATE OR REPLACE VIEW orangevision_web.effective_analyses AS
SELECT a.id,a.dispositivo_id,a.data_hora,
    COALESCE(d.classification,a.classificacao::text) AS classificacao,
    COALESCE(a.cor_media,(local.metrics->>'orange_color_ratio')::numeric*100) AS cor_media,
    COALESCE(a.regioes_anormais,(local.metrics->>'abnormal_region_ratio')::numeric*100) AS regioes_anormais,
    COALESCE(a.circularidade,(local.metrics->>'circularity')::numeric) AS circularidade,
    COALESCE(a.assimetria,(local.metrics->>'asymmetry')::numeric*100) AS assimetria,
    COALESCE(a.score_visual,(local.metrics->>'visual_score')::numeric) AS score_visual,
    a.versao_algoritmo,a.criado_em,a.inspection_session_id,a.calibration_version,
    COALESCE(d.reason,a.classification_reason) AS classification_reason,
    COALESCE(d.origin,CASE WHEN s.id IS NOT NULL THEN 'local' END) AS evaluation_source,
    COALESCE(d.revision,0) AS decision_revision
FROM public.analises a
LEFT JOIN orangevision_web.image_samples s ON s.analysis_id=a.id
LEFT JOIN LATERAL (
    SELECT metrics FROM orangevision_web.sample_evaluations
    WHERE sample_id=s.id AND origin='local' AND state='completed'
    ORDER BY created_at DESC,id DESC LIMIT 1
) local ON true
LEFT JOIN LATERAL (
    SELECT classification,reason,origin,revision FROM orangevision_web.sample_decisions
    WHERE sample_id=s.id ORDER BY revision DESC LIMIT 1
) d ON true;
COMMIT;
