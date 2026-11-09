from uuid import NAMESPACE_URL, uuid4, uuid5

from psycopg.types.json import Jsonb

from ..application.errors import ApplicationError
from ..application.inspection_service import capture_within_authorization, payload_digest
from ..database import connection

CRITERIA_VERSION = 'orange-surface-v1'


def evaluations_ready(db):
    return db.execute('''SELECT to_regclass('orangevision_web.sample_evaluations') IS NOT NULL
        AND to_regclass('orangevision_web.gemini_jobs') IS NOT NULL
        AND to_regclass('orangevision_web.gemini_attempts') IS NOT NULL
        AND to_regclass('orangevision_web.sample_decisions') IS NOT NULL
        AND to_regclass('orangevision_web.effective_analyses') IS NOT NULL AS ready''').fetchone()['ready']


def record_local(db, row):
    if not row.get('result_hash') or row['state'] not in ('completed', 'awaiting_review', 'not_evaluable', 'failed') or not evaluations_ready(db):
        return
    db.execute('''INSERT INTO orangevision_web.sample_evaluations
        (id,sample_id,origin,run_key,state,classification,reason,criteria_version,model_version,metrics)
        VALUES (%s,%s,'local',%s,%s,%s,%s,%s,%s,%s)
        ON CONFLICT(sample_id,origin,run_key) DO NOTHING''',
        (uuid4(), row['id'], row['claim_id'] or row['id'], row['state'], row['classification'],
         row['reason'] or 'Resultado local sem justificativa.', row['calibration_version'] or 'local-unconfigured',
         row['algorithm_version'], Jsonb(row['metrics']) if row['metrics'] else None))


def describe_evaluations(db, identities):
    if not identities or not evaluations_ready(db):
        return {}
    result = {identity: {'evaluations': [], 'gemini_job': None, 'decision': None} for identity in identities}
    for row in db.execute('''SELECT DISTINCT ON(sample_id,origin)
        sample_id,id,origin,state,classification,reason,criteria_version,model_version,created_at
        FROM orangevision_web.sample_evaluations WHERE sample_id=ANY(%s)
        ORDER BY sample_id,origin,created_at DESC,id DESC''', (identities,)).fetchall():
        result[row.pop('sample_id')]['evaluations'].append(row)
    for row in db.execute('''SELECT DISTINCT ON(sample_id) sample_id,id,state,attempts,error_code,updated_at
        FROM orangevision_web.gemini_jobs WHERE sample_id=ANY(%s)
        ORDER BY sample_id,created_at DESC,id DESC''', (identities,)).fetchall():
        result[row.pop('sample_id')]['gemini_job'] = row
    for row in db.execute('''SELECT DISTINCT ON(sample_id) sample_id,revision,origin,classification,reason,created_at
        FROM orangevision_web.sample_decisions WHERE sample_id=ANY(%s)
        ORDER BY sample_id,revision DESC''', (identities,)).fetchall():
        result[row.pop('sample_id')]['decision'] = row
    for value in result.values():
        categories = [evaluation['classification'] for evaluation in value['evaluations']]
        value['comparison'] = ('agreement' if categories[0] == categories[1] else 'divergence') if len(categories) == 2 and all(categories) else 'inconclusive' if len(categories) == 2 else 'pending'
    return result


class EvaluationRepository:
    def __init__(self, settings):
        self.settings = settings

    def ready(self):
        with connection(self.settings) as db:
            return evaluations_ready(db)

    def enqueue(self, db, row, request_id=None, *, required=False):
        if not self.settings.gemini_enabled or not evaluations_ready(db):
            if required:
                raise ApplicationError(503, 'Avaliação Gemini requer ativação e migration 008.')
            return
        request_id = request_id or uuid5(NAMESPACE_URL, f'orangevision:gemini:{row["id"]}:{CRITERIA_VERSION}')
        db.execute("SELECT pg_advisory_xact_lock(hashtextextended('orangevision:gemini-enqueue',0))")
        previous = db.execute('SELECT id FROM orangevision_web.gemini_jobs WHERE sample_id=%s AND request_id=%s', (row['id'], request_id)).fetchone()
        if previous:
            return
        if db.execute("SELECT 1 FROM orangevision_web.gemini_jobs WHERE sample_id=%s AND state IN ('queued','running','retry_wait')", (row['id'],)).fetchone():
            if required:
                raise ApplicationError(409, 'Já existe uma avaliação Gemini em andamento para esta captura.')
            return
        capacity = db.execute("SELECT count(*) AS total,count(*) FILTER(WHERE user_id=%s) AS own FROM orangevision_web.gemini_jobs WHERE state IN ('queued','running','retry_wait')", (row['user_id'],)).fetchone()
        if capacity['total'] >= 500 or capacity['own'] >= 20:
            if required:
                raise ApplicationError(429, 'Fila Gemini no limite. Aguarde os trabalhos existentes.', {'Retry-After': '60'})
            return
        db.execute('''INSERT INTO orangevision_web.gemini_jobs
            (id,sample_id,user_id,request_id,criteria_version,model_version)
            VALUES (%s,%s,%s,%s,%s,%s)''',
            (uuid4(), row['id'], row['user_id'], request_id, CRITERIA_VERSION, self.settings.gemini_model))

    def request(self, owner, identity, request_id):
        with connection(self.settings) as db:
            row = db.execute('''SELECT id,user_id,claim_id,result_hash,state,classification,reason,
                calibration_version,algorithm_version,metrics FROM orangevision_web.image_samples
                WHERE id=%s AND user_id=%s FOR UPDATE''', (identity, owner)).fetchone()
            if not row:
                raise ApplicationError(404, 'Amostra não encontrada ou sem acesso.')
            self.enqueue(db, row, request_id, required=True)
            record_local(db, row)

    def decide(self, owner, identity, command):
        fingerprint = payload_digest(command.model_dump(mode='json'))
        with connection(self.settings) as db:
            row = db.execute('SELECT * FROM orangevision_web.image_samples WHERE id=%s AND user_id=%s FOR UPDATE', (identity, owner)).fetchone()
            if not row:
                raise ApplicationError(404, 'Amostra não encontrada ou sem acesso.')
            if not evaluations_ready(db) or not self.settings.inspections_enabled:
                raise ApplicationError(503, 'Decisão requer migration 008 e inspeções ativas.')
            self._apply(db, row, owner, identity, command, fingerprint)

    def _apply(self, db, row, owner, identity, command, fingerprint, algorithm='operator-decision-v1'):
        """Registra a decisão (append-only) e publica a análise única da captura."""
        previous = db.execute('SELECT fingerprint FROM orangevision_web.sample_decisions WHERE sample_id=%s AND request_id=%s', (identity, command.request_id)).fetchone()
        if previous:
            if previous['fingerprint'] != fingerprint:
                raise ApplicationError(409, 'Comando já utilizado com outra decisão.')
            return
        revision = db.execute('SELECT COALESCE(max(revision),0) AS revision FROM orangevision_web.sample_decisions WHERE sample_id=%s', (identity,)).fetchone()['revision']
        if revision != command.expected_revision:
            raise ApplicationError(409, 'A decisão foi atualizada. Consulte novamente antes de confirmar.')
        origin = 'human'
        if command.evaluation_id:
            evaluation = db.execute('SELECT origin,state,classification FROM orangevision_web.sample_evaluations WHERE id=%s AND sample_id=%s', (command.evaluation_id, identity)).fetchone()
            if not evaluation or evaluation['state'] != 'completed' or evaluation['classification'] != command.classification:
                raise ApplicationError(409, 'Avaliação incompatível. Para corrigir a categoria, registre uma decisão humana.')
            origin = evaluation['origin']
        session = db.execute('SELECT s.*,clock_timestamp() AS observed_at FROM orangevision_web.inspection_sessions s WHERE id=%s FOR SHARE', (row['source_inspection_id'],)).fetchone()
        if (not session or not row['captured_at'] or session['user_id'] != owner
                or session['device_id'] != row['device_id']
                or not capture_within_authorization(row['captured_at'], session, session['observed_at'])):
            raise ApplicationError(409, 'A captura precisa de sessão e horário de origem autorizados.')
        if not row['analysis_id']:
            analysis = uuid4()
            # A base é imutável. Métricas ausentes permanecem NULL.
            db.execute('''INSERT INTO public.analises
                (id,dispositivo_id,data_hora,classificacao,versao_algoritmo,criado_em,
                 inspection_session_id,classification_reason,cor_media,regioes_anormais,
                 circularidade,assimetria,score_visual,calibration_version)
                VALUES (%s,%s,%s,%s,%s,now(),%s,%s,NULL,NULL,NULL,NULL,NULL,NULL)''',
                (analysis, row['device_id'], row['captured_at'], command.classification, algorithm,
                 session['id'], command.reason))
            db.execute('INSERT INTO orangevision_web.ingestion_receipts(analysis_id,inspection_session_id,payload_hash) VALUES (%s,%s,%s)', (analysis, session['id'], fingerprint))
            db.execute('UPDATE orangevision_web.image_samples SET analysis_id=%s WHERE id=%s', (analysis, identity))
        db.execute('''INSERT INTO orangevision_web.sample_decisions
            (id,sample_id,revision,request_id,user_id,evaluation_id,origin,classification,reason,fingerprint)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)''',
            (uuid4(), identity, revision + 1, command.request_id, owner, command.evaluation_id,
             origin, command.classification, command.reason, fingerprint))


LOCAL_FAILED = ('awaiting_review', 'not_evaluable', 'failed')


def auto_adoption(gemini, local, decision, gemini_job_state=None):
    """Decide se a captura entra sozinha no histórico/gráficos.

    Retorna (adotar, origem, motivo). origem é 'local' ou 'gemini' (de quem vem a categoria).
    - As duas com categoria: entra se concordarem; divergência fica para a pessoa.
    - Uma sem categoria (falhou): vale a categoria da outra.
    - As duas sem categoria: fica para a pessoa. Enquanto uma ainda roda, espera.
    """
    if decision is not None:
        return False, None, 'existing_decision'
    local_class = local['classification'] if local and local['state'] == 'completed' else None
    gemini_class = gemini['classification'] if gemini and gemini['state'] == 'completed' else None
    local_failed = bool(local) and local['state'] in LOCAL_FAILED
    gemini_failed = (bool(gemini) and not gemini_class) or (not gemini and gemini_job_state == 'failed')
    if local_class and gemini_class:
        if local_class != gemini_class:
            return False, None, 'divergence'
        return True, 'local', 'agreement'
    if local_class and gemini_failed:
        return True, 'local', 'gemini_failed'
    if gemini_class and local_failed:
        return True, 'gemini', 'local_failed'
    if local_failed and gemini_failed:
        return False, None, 'both_failed'
    return False, None, 'awaiting_gemini' if local_class or local_failed else 'awaiting_local'


AUTO_REASONS = {
    'agreement': 'Aprovado automaticamente: avaliação local e Gemini concordaram ({category}). {reason}',
    'gemini_failed': 'Aprovado automaticamente pela avaliação local ({category}); Gemini sem categoria. {reason}',
    'local_failed': 'Aprovado automaticamente pelo Gemini ({category}); avaliação local sem categoria. {reason}',
}


class AutoAdoption:
    """Publica a captura pela regra automática; chamado quando chega o local ou o Gemini."""

    def __init__(self, settings):
        self.settings = settings

    def run(self, sample_id, user_id):
        from ..evaluation_contracts import DecisionRequest

        if (not self.settings.gemini_auto_adopt or not self.settings.gemini_auto_request
                or not self.settings.inspections_enabled):
            return 'disabled'
        with connection(self.settings) as db:
            row = db.execute(
                'SELECT * FROM orangevision_web.image_samples WHERE id=%s AND user_id=%s FOR UPDATE',
                (sample_id, user_id),
            ).fetchone()
            if not row or not evaluations_ready(db):
                return 'unavailable'
            latest = {
                item['origin']: item for item in db.execute('''SELECT DISTINCT ON(origin)
                    id,origin,state,classification,reason FROM orangevision_web.sample_evaluations
                    WHERE sample_id=%s ORDER BY origin,created_at DESC,id DESC''', (sample_id,)).fetchall()
            }
            decision = db.execute(
                'SELECT revision FROM orangevision_web.sample_decisions WHERE sample_id=%s ORDER BY revision DESC LIMIT 1',
                (sample_id,),
            ).fetchone()
            job = db.execute(
                'SELECT state FROM orangevision_web.gemini_jobs WHERE sample_id=%s ORDER BY created_at DESC LIMIT 1',
                (sample_id,),
            ).fetchone()
            adopt, origin, reason = auto_adoption(
                # Sem Gemini ativo não há segunda opinião: equivale a falha dela.
                latest.get('gemini'), latest.get('local'), decision,
                job['state'] if job else (None if self.settings.gemini_enabled else 'failed'),
            )
            if not adopt:
                return reason
            chosen = latest[origin]
            # Ligada à avaliação escolhida; com a local, a view usa as métricas dela.
            command = DecisionRequest(
                request_id=uuid5(NAMESPACE_URL, f'orangevision:auto:{reason}:{chosen["id"]}'),
                expected_revision=0, evaluation_id=chosen['id'],
                classification=chosen['classification'],
                reason=AUTO_REASONS[reason].format(category=chosen['classification'], reason=chosen['reason'])[:1000],
            )
            try:
                self._repository()._apply(
                    db, row, user_id, sample_id, command,
                    payload_digest(command.model_dump(mode='json')), algorithm=f'auto-{reason}-v1'.replace('_', '-'),
                )
            except ApplicationError as error:
                # Sem sessão de origem válida etc.: fica para revisão humana, sem erro no worker.
                return f'skipped_{error.status_code}'
        return reason

    def _repository(self):
        return EvaluationRepository(self.settings)
