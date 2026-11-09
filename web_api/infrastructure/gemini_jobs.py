import logging
from uuid import uuid4

from psycopg.types.json import Jsonb

from ..database import connection
from .evaluation_repository import CRITERIA_VERSION, evaluations_ready

log = logging.getLogger('orangevision.web')


class GeminiJobs:
    def __init__(self, settings):
        self.settings = settings

    def claim(self):
        with connection(self.settings) as db:
            if not evaluations_ready(db):
                raise RuntimeError('Worker requer migration 008.')
            # Reserva do orçamento é confirmada ANTES da chamada externa. Tentativas
            # incertas também consomem o limite; não prometer cobrança exactly-once.
            db.execute("SELECT pg_advisory_xact_lock(hashtextextended('orangevision:gemini-budget',0))")
            db.execute("UPDATE orangevision_web.gemini_attempts a SET outcome='lease_uncertain' FROM orangevision_web.gemini_jobs j WHERE a.job_id=j.id AND a.attempt=j.attempts AND j.state='running' AND j.lease_expires_at<=clock_timestamp()")
            db.execute("UPDATE orangevision_web.gemini_jobs SET state='failed',execution_token=NULL,error_code='lease_exhausted',updated_at=clock_timestamp() WHERE state='running' AND lease_expires_at<=clock_timestamp() AND attempts>=3")
            job = db.execute('''SELECT * FROM orangevision_web.gemini_jobs
                WHERE attempts<3 AND (
                    (state IN ('queued','retry_wait') AND next_attempt_at<=clock_timestamp())
                    OR (state='running' AND lease_expires_at<=clock_timestamp()))
                ORDER BY next_attempt_at,created_at FOR UPDATE SKIP LOCKED LIMIT 1''').fetchone()
            if not job:
                return None
            if job['state'] == 'running':
                db.execute("UPDATE orangevision_web.gemini_attempts SET outcome='lease_uncertain' WHERE job_id=%s AND attempt=%s", (job['id'], job['attempts']))
            counts = db.execute('''SELECT count(*) AS total,count(*) FILTER(WHERE user_id=%s) AS own
                FROM orangevision_web.gemini_attempts WHERE started_at>=date_trunc('day',clock_timestamp(),'UTC')''', (job['user_id'],)).fetchone()
            if counts['total'] >= self.settings.gemini_daily_limit or counts['own'] >= self.settings.gemini_user_daily_limit:
                db.execute("UPDATE orangevision_web.gemini_jobs SET state='retry_wait',execution_token=NULL,error_code='daily_limit',next_attempt_at=date_trunc('day',clock_timestamp(),'UTC')+interval '1 day',updated_at=clock_timestamp() WHERE id=%s", (job['id'],))
                return None
            token, attempt = uuid4(), job['attempts'] + 1
            db.execute("UPDATE orangevision_web.gemini_jobs SET state='running',execution_token=%s,attempts=%s,lease_expires_at=clock_timestamp()+interval '2 minutes',error_code=NULL,updated_at=clock_timestamp() WHERE id=%s", (token, attempt, job['id']))
            db.execute('INSERT INTO orangevision_web.gemini_attempts(job_id,attempt,user_id) VALUES (%s,%s,%s)', (job['id'], attempt, job['user_id']))
            image = bytes(db.execute('SELECT image_data FROM orangevision_web.image_samples WHERE id=%s AND user_id=%s', (job['sample_id'], job['user_id'])).fetchone()['image_data'])
            job.update(execution_token=token, attempts=attempt, image=image)
        return job

    def finish(self, job, assessment=None, usage=None, failure=None):
        with connection(self.settings) as db:
            current = db.execute("SELECT id FROM orangevision_web.gemini_jobs WHERE id=%s AND state='running' AND execution_token=%s AND lease_expires_at>clock_timestamp() FOR UPDATE", (job['id'], job['execution_token'])).fetchone()
            if not current:
                return False
            if assessment is not None:
                db.execute('''INSERT INTO orangevision_web.sample_evaluations
                    (id,sample_id,origin,run_key,state,classification,reason,criteria_version,model_version)
                    VALUES (%s,%s,'gemini',%s,%s,%s,%s,%s,%s)
                    ON CONFLICT(sample_id,origin,run_key) DO NOTHING''',
                    (uuid4(), job['sample_id'], job['id'], 'completed' if assessment.evaluable else 'not_evaluable',
                     assessment.classification, assessment.reason, job['criteria_version'], job['model_version']))
                state, code, delay = 'completed', None, 0
            else:
                state = 'retry_wait' if failure.retryable and job['attempts'] < 3 else 'failed'
                code, delay = failure.code, max(failure.delay, min(300, 5 * 2 ** job['attempts']))
            db.execute('''UPDATE orangevision_web.gemini_jobs SET state=%s,error_code=%s,
                execution_token=NULL,next_attempt_at=clock_timestamp()+make_interval(secs=>%s),updated_at=clock_timestamp()
                WHERE id=%s''', (state, code, delay, job['id']))
            db.execute('UPDATE orangevision_web.gemini_attempts SET outcome=%s,usage=%s WHERE job_id=%s AND attempt=%s',
                       (code or 'completed', Jsonb(usage or {}), job['id'], job['attempts']))
        return True


def audit_attempt(job, outcome, detail, classification=None):
    """Uma linha de log por tentativa: o que foi chamado, quanto demorou e o resultado.

    Sem imagem, chave, texto livre do provedor ou dados pessoais. O mesmo detalhe
    fica gravado em gemini_attempts.usage para consulta posterior.
    """
    log.info('gemini_attempt', extra={
        'job_id': str(job['id']), 'sample_id': str(job['sample_id']),
        'attempt': job.get('attempts'), 'model': job.get('model_version'),
        'outcome': outcome, 'classification': classification,
        'http_status': detail.get('http_status'), 'provider_status': detail.get('provider_status'),
        'duration_ms': detail.get('duration_ms'), 'reason': detail.get('reason'),
    })


def adopt_automatically(jobs, job, adopter=None):
    """Após uma avaliação salva: publica sozinha quando a regra permite; nunca derruba o worker."""
    from .evaluation_repository import AutoAdoption

    settings = getattr(jobs, 'settings', None)
    adopter = adopter or (AutoAdoption(settings) if settings is not None else None)
    if adopter is None:
        return None
    try:
        outcome = adopter.run(job['sample_id'], job['user_id'])
    except Exception as error:
        outcome = 'failed'
        log.error('gemini_auto_adoption_failed', extra={
            'sample_id': str(job['sample_id']), 'error_type': type(error).__name__,
        })
    log.info('gemini_auto_adoption', extra={'sample_id': str(job['sample_id']), 'outcome': outcome})
    return outcome


def process_once(jobs, provider, adopter=None):
    from .gemini_provider import ProviderFailure

    job = jobs.claim()
    if not job:
        return 'idle'
    try:
        if job['criteria_version'] != CRITERIA_VERSION:
            raise ProviderFailure('criteria_unavailable')
        result, usage = provider.assess(job['image'], job['model_version'])
    except ProviderFailure as failure:
        jobs.finish(job, failure=failure, usage=failure.detail)
        audit_attempt(job, failure.code, failure.detail)
        # Falha definitiva do Gemini: a avaliação local pode valer sozinha.
        adopt_automatically(jobs, job, adopter)
        return failure.code
    saved = jobs.finish(job, assessment=result, usage=usage)
    audit_attempt(job, 'completed' if saved else 'stale_result', usage, result.classification)
    if saved:
        adopt_automatically(jobs, job, adopter)
    return 'completed' if saved else 'stale_result'
