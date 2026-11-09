import os
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import timedelta
from uuid import uuid4

import psycopg
import pytest
from fastapi.testclient import TestClient

from web_api.api.dependencies import current_session
from web_api.application.auth_service import digest
from web_api.application.errors import ApplicationError
from web_api.contracts import Filters
from web_api.evaluation_contracts import DecisionRequest, VisualAssessment
from web_api.infrastructure.analysis_repository import AnalysisRepository
from web_api.infrastructure.dashboard_readiness import inspect_dashboard
from web_api.infrastructure.evaluation_repository import EvaluationRepository
from web_api.infrastructure.gemini_jobs import GeminiJobs, process_once
from web_api.infrastructure.gemini_provider import ProviderFailure
from web_api.infrastructure.sample_repository import SampleRepository
from web_api.main import create_app

from . import test_devices_postgres, test_sample_publication_postgres
from .test_devices_postgres import LEGACY, MIGRATIONS, A, B
from .test_sample_publication_postgres import finish, result, sample

device_db = test_devices_postgres.db
publication_db = test_sample_publication_postgres.prepared
pytestmark = pytest.mark.skipif(not os.getenv('OV_DEVICE_TEST_DATABASE_URL'), reason='PostgreSQL descartável não configurado.')


@pytest.fixture
def dual(publication_db):
    db, settings = publication_db
    db.execute((MIGRATIONS / '008_dual_evaluations.sql').read_text(), prepare=False)
    return db, replace(settings, gemini_enabled=True, gemini_api_key='synthetic-provider-key', gemini_daily_limit=5, gemini_user_daily_limit=3)


class Provider:
    calls = 0

    def assess(self, image, model):
        self.calls += 1
        assert image == b'fixture'
        return VisualAssessment(evaluable=True, classification='ATENCAO', reason='Alterações visuais sintéticas; confirmar com operador.'), {'total_tokens': 200}


def request(settings, identity, owner=A):
    EvaluationRepository(settings).request(owner, identity, uuid4())


def decision(evaluation_id=None, category='REVISAR', revision=0):
    return DecisionRequest(request_id=uuid4(), expected_revision=revision, evaluation_id=evaluation_id,
                           classification=category, reason='Decisão sintética conferida pelo operador.')


def test_local_and_gemini_are_independent_and_decision_counts_once(dual):
    db, settings = dual
    identity, claim = sample(db)
    local = finish(settings, identity, result(claim))
    assert len(local['evaluations']) == 1 and local['analysis_id']
    request(settings, identity)
    provider = Provider()
    assert process_once(GeminiJobs(settings), provider) == 'completed'
    listed = SampleRepository(settings).listing(A, 20, 0)['items'][0]
    assert listed['comparison'] == 'divergence' and listed['classification'] == 'APROVADA'
    gemini = next(item for item in listed['evaluations'] if item['origin'] == 'gemini')
    assert 'metrics' not in gemini
    queries = AnalysisRepository(settings)
    assert queries.summarize(A, Filters())['approved'] == 1  # Gemini não adota sozinho.
    command = decision(gemini['id'], 'ATENCAO')
    EvaluationRepository(settings).decide(A, identity, command)
    EvaluationRepository(settings).decide(A, identity, command)
    assert queries.summarize(A, Filters())['total'] == 1
    assert queries.summarize(A, Filters())['attention'] == 1
    assert queries.summarize(A, Filters(classification='ATENCAO'))['total'] == 1
    assert queries.summarize(B, Filters())['total'] == 0
    assert queries.find_analysis(A, local['analysis_id'])['evaluation_source'] == 'gemini'
    EvaluationRepository(settings).decide(A, identity, decision(category='REVISAR', revision=1))
    assert queries.summarize(A, Filters())['review'] == 1
    assert db.execute('SELECT classificacao FROM public.analises WHERE id=%s', (local['analysis_id'],)).fetchone()['classificacao'] == 'APROVADA'
    assert db.execute('SELECT count(*) AS n FROM orangevision_web.sample_decisions').fetchone()['n'] == 2


def test_gemini_can_finish_before_local_and_operator_publishes_null_metrics(dual):
    db, settings = dual
    db.execute('ALTER TABLE public.analises ALTER COLUMN cor_media SET DEFAULT 0, ALTER COLUMN score_visual SET DEFAULT 0')
    identity, claim = sample(db)
    request(settings, identity)
    process_once(GeminiJobs(settings), Provider())
    evaluation = SampleRepository(settings).listing(A, 20, 0)['items'][0]['evaluations'][0]
    EvaluationRepository(settings).decide(A, identity, decision(evaluation['id'], 'ATENCAO'))
    items, count = AnalysisRepository(settings).list_analyses(A, Filters(), 20, 0)
    assert count == 1 and all(value is None for value in items[0]['metrics'].values())
    # Resultado local tardio não sobrescreve a decisão nem cria outra fruta.
    saved = finish(settings, identity, result(claim))
    assert saved['decision']['origin'] == 'gemini' and len(saved['evaluations']) == 2
    assert AnalysisRepository(settings).summarize(A, Filters())['attention'] == 1
    refreshed = AnalysisRepository(settings).find_analysis(A, saved['analysis_id'])
    assert refreshed['metrics']['orange_color_ratio'] == .8
    assert refreshed['calibration_version'] is None


def test_idempotent_enqueue_and_stale_worker_fencing(dual):
    db, settings = dual
    identity, _ = sample(db)
    command = uuid4()
    store = EvaluationRepository(settings)
    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(lambda _: store.request(A, identity, command), range(2)))
    assert db.execute('SELECT count(*) AS n FROM orangevision_web.gemini_jobs').fetchone()['n'] == 1
    jobs = GeminiJobs(settings)
    first = jobs.claim()
    db.execute("UPDATE orangevision_web.gemini_jobs SET lease_expires_at=now()-interval '1 second'")
    second = jobs.claim()
    assessment, usage = Provider().assess(b'fixture', second['model_version'])
    assert jobs.finish(first, assessment=assessment, usage=usage) is False
    assert jobs.finish(second, assessment=assessment, usage=usage) is True
    assert db.execute('SELECT count(*) AS n FROM orangevision_web.sample_evaluations').fetchone()['n'] == 1
    assert db.execute('SELECT count(*) AS n FROM orangevision_web.gemini_attempts').fetchone()['n'] == 2


def test_daily_budget_counts_attempts_and_defers_jobs(dual):
    db, settings = dual
    settings = replace(settings, gemini_daily_limit=2, gemini_user_daily_limit=2)
    for _ in range(3):
        identity, _ = sample(db)
        request(settings, identity)
    jobs, provider = GeminiJobs(settings), Provider()
    assert process_once(jobs, provider) == 'completed'
    assert process_once(jobs, provider) == 'completed'
    assert process_once(jobs, provider) == 'idle'
    assert provider.calls == 2
    assert db.execute("SELECT count(*) AS n FROM orangevision_web.gemini_jobs WHERE error_code='daily_limit' AND state='retry_wait'").fetchone()['n'] == 1


def test_failure_retries_are_bounded_and_do_not_touch_local(dual):
    db, settings = dual
    identity, claim = sample(db)
    finish(settings, identity, result(claim))
    request(settings, identity)

    class BrokenProvider:
        def assess(self, image, model):
            raise ProviderFailure('network_uncertain', True)

    for _ in range(3):
        assert process_once(GeminiJobs(settings), BrokenProvider()) == 'network_uncertain'
        db.execute("UPDATE orangevision_web.gemini_jobs SET next_attempt_at=now()-interval '1 second'")
    assert process_once(GeminiJobs(settings), BrokenProvider()) == 'idle'
    row = SampleRepository(settings).listing(A, 20, 0)['items'][0]
    assert row['gemini_job']['state'] == 'failed' and row['classification'] == 'APROVADA'
    assert AnalysisRepository(settings).summarize(A, Filters())['approved'] == 1


def test_requeue_preserves_previous_local_assessment(dual):
    db, settings = dual
    identity, claim = sample(db)
    finish(settings, identity, result(claim, 'awaiting_review'))
    queued = SampleRepository(settings).queue(A, identity, LEGACY)
    assert queued['state'] == 'queued' and queued['classification'] is None
    assert queued['evaluations'][0]['state'] == 'awaiting_review'


def test_requesting_gemini_archives_existing_local_result_without_reprocessing(dual):
    db, settings = dual
    identity, claim = sample(db)
    finish(settings, identity, result(claim, 'awaiting_review'))
    # Simula resultado recebido antes da migration 008, ainda sem snapshot.
    db.execute('DELETE FROM orangevision_web.sample_evaluations WHERE sample_id=%s', (identity,))
    request(settings, identity)
    process_once(GeminiJobs(settings), Provider())
    row = SampleRepository(settings).listing(A, 20, 0)['items'][0]
    assert len(row['evaluations']) == 2 and row['comparison'] == 'inconclusive'
    assert row['state'] == 'awaiting_review' and row['classification'] is None


def test_readiness_requires_complete_migration_007_not_just_column(dual):
    db, _ = dual
    db.execute('DROP INDEX orangevision_web.image_samples_analysis_unique')
    report = inspect_dashboard(db, True)
    assert report['checks']['column_exists'] and not report['checks']['link_unique']
    assert report['status'] == 'schema_unavailable'


def test_concurrent_decisions_conflict_instead_of_double_counting(dual):
    db, settings = dual
    identity, _ = sample(db)

    def adopt(category):
        try:
            EvaluationRepository(settings).decide(A, identity, decision(category=category))
            return 200
        except ApplicationError as error:
            return error.status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        codes = sorted(pool.map(adopt, ['APROVADA', 'REVISAR']))
    assert codes == [200, 409]
    assert AnalysisRepository(settings).summarize(A, Filters())['total'] == 1


def test_readiness_distinguishes_runtime_flag_column_and_permissions(dual):
    db, _ = dual
    assert inspect_dashboard(db, True)['status'] == 'enabled'
    assert inspect_dashboard(db, False)['status'] == 'inspections_disabled'
    db.execute('CREATE ROLE orangevision_limited NOLOGIN')
    try:
        db.execute('GRANT USAGE ON SCHEMA orangevision_web,public TO orangevision_limited')
        db.execute('GRANT SELECT(id,state) ON orangevision_web.image_samples TO orangevision_limited')
        db.execute('SET ROLE orangevision_limited')
        report = inspect_dashboard(db, True)
        assert report['checks']['column_exists'] and not report['checks']['column_visible']
        assert report['status'] == 'permissions_missing'
    finally:
        db.execute('RESET ROLE')
        db.execute('DROP OWNED BY orangevision_limited')
        db.execute('DROP ROLE orangevision_limited')


def origin_session(db, *, owner=A, device=LEGACY, lease='origin-lease', started="now()-interval '10 minutes'",
                   expires="now()+interval '1 hour'", closed='NULL', state='active'):
    identity = uuid4()
    db.execute(f'''INSERT INTO orangevision_web.inspection_sessions
        (id,user_id,device_id,request_id,state,pairing_hash,pairing_expires_at,lease_hash,started_at,authorization_expires_at,closed_at)
        VALUES (%s,%s,%s,%s,%s,%s,now(),%s,{started},{expires},{closed})''',
        (identity, owner, device, uuid4(), state, digest(str(identity)), digest(lease)))
    return identity


def captured(db, session, *, column='source_inspection_id', owner=A):
    identity = uuid4()
    db.execute(f'''INSERT INTO orangevision_web.image_samples
        (id,user_id,request_id,source_hash,filename,image_data,width,height,state,device_id,{column},captured_at)
        VALUES (%s,%s,%s,'fixture','capture.jpg',%s,80,60,'queued',%s,%s,now()-interval '1 minute')''',
        (identity, owner, uuid4(), b'fixture', LEGACY, session))
    return identity


def consult(settings, identity, lease='origin-lease', device=LEGACY):
    return SampleRepository(settings).device_evaluations(device, identity, digest(lease))


def denied(settings, identity, **kwargs):
    with pytest.raises(ApplicationError) as error:
        consult(settings, identity, **kwargs)
    return error.value.status_code


def test_device_reads_both_evaluations_without_side_effects(dual):
    db, settings = dual
    session = origin_session(db)
    identity = captured(db, session)
    EvaluationRepository(settings).enqueue(db, {'id': identity, 'user_id': A})
    db.execute("UPDATE orangevision_web.image_samples SET claim_id=%s,lease_hash=%s,state='processing',claim_expires_at=now()+interval '5 minutes' WHERE id=%s",
               (claim := uuid4(), digest('lease'), identity))
    pending = consult(settings, identity)
    assert pending['gemini_job']['state'] == 'queued' and pending['evaluations'] == []
    assert pending['comparison'] == 'pending' and pending['inspection_id'] == session

    tables = ('image_samples', 'sample_evaluations', 'gemini_jobs', 'gemini_attempts', 'sample_decisions')

    def snapshot():
        return [db.execute(f'SELECT * FROM orangevision_web.{table} ORDER BY 1,2').fetchall() for table in tables]

    before = snapshot()
    consult(settings, identity)
    assert snapshot() == before

    finish(settings, identity, result(claim))
    process_once(GeminiJobs(settings), Provider())
    answer = consult(settings, identity)
    assert {item['origin'] for item in answer['evaluations']} == {'local', 'gemini'}
    assert answer['comparison'] == 'divergence' and answer['gemini_job']['state'] == 'completed'
    assert answer['state'] == 'completed' and answer['decision'] is None


def test_device_read_transaction_rejects_writes(dual, monkeypatch):
    db, settings = dual
    identity = captured(db, origin_session(db))
    from web_api.infrastructure import sample_repository

    def write_during_read(database, identities):
        database.execute("UPDATE orangevision_web.image_samples SET state='failed'")

    monkeypatch.setattr(sample_repository, 'describe_evaluations', write_during_read)
    with pytest.raises(psycopg.errors.ReadOnlySqlTransaction):
        consult(settings, identity)
    state = db.execute('SELECT state FROM orangevision_web.image_samples WHERE id=%s', (identity,)).fetchone()['state']
    assert state == 'queued'


def test_device_read_hides_sample_from_wrong_device_lease_or_owner(dual):
    db, settings = dual
    other_device = uuid4()
    db.execute("INSERT INTO public.dispositivos VALUES (%s,'Outro','offline',now())", (other_device,))
    identity = captured(db, origin_session(db))
    assert denied(settings, uuid4()) == 404
    assert denied(settings, identity, lease='wrong-lease') == 404
    assert denied(settings, identity, device=other_device) == 404
    # Lease válida de outra sessão do mesmo equipamento não abre esta captura.
    origin_session(db, lease='other-lease', state='closed', closed='now()')
    assert denied(settings, identity, lease='other-lease') == 404
    # Sessão de outra conta não comprova a origem, mesmo com a lease correta.
    foreign = captured(db, origin_session(db, owner=B, lease='foreign-lease', state='closed', closed='now()'))
    assert denied(settings, foreign, lease='foreign-lease') == 404
    # Foto enviada pelo formulário não tem sessão de origem.
    upload = sample(db, with_session=False)[0]
    assert denied(settings, upload) == 404
    # Sessão sem ativação nunca autoriza leitura.
    inactive = captured(db, origin_session(db, lease='inactive-lease', started='NULL', state='closed', closed='now()'))
    assert denied(settings, inactive, lease='inactive-lease') == 404


def test_device_read_window_after_close_and_expiration(dual):
    db, settings = dual
    window = {
        'closed_recently': ("now()+interval '1 hour'", "now()-interval '59 minutes'", 'closed'),
        'closed_long_ago': ("now()+interval '1 hour'", "now()-interval '61 minutes'", 'closed'),
        'expired_recently': ("now()-interval '59 minutes'", 'NULL', 'expired'),
        'expired_long_ago': ("now()-interval '61 minutes'", 'NULL', 'expired'),
    }
    samples = {
        name: captured(db, origin_session(db, lease=name, started="now()-interval '3 hours'", expires=expires, closed=closed, state=state))
        for name, (expires, closed, state) in window.items()
    }
    recent = consult(settings, samples['closed_recently'], lease='closed_recently')
    assert timedelta(0) < recent['access_expires_at'] - recent['observed_at'] <= timedelta(minutes=1)
    assert consult(settings, samples['expired_recently'], lease='expired_recently')
    assert denied(settings, samples['closed_long_ago'], lease='closed_long_ago') == 410
    assert denied(settings, samples['expired_long_ago'], lease='expired_long_ago') == 410


def test_device_read_requires_current_access_and_activation(dual):
    db, settings = dual
    identity = captured(db, origin_session(db))
    assert denied(replace(settings, inspections_enabled=False), identity) == 503
    db.execute('DELETE FROM orangevision_web.device_access WHERE user_id=%s AND device_id=%s', (A, LEGACY))
    assert denied(settings, identity) == 403


def test_device_read_accepts_review_session_authorization(dual):
    db, settings = dual
    review = origin_session(db, lease='review-lease')
    identity = captured(db, review, column='review_authorization_id')
    assert consult(settings, identity, lease='review-lease')['inspection_id'] == review
    assert denied(settings, identity) == 404


def test_device_read_over_http(dual):
    db, settings = dual
    identity = captured(db, origin_session(db))
    db.execute('''INSERT INTO orangevision_web.device_credentials(id,device_id,token_hash)
        VALUES (%s,%s,%s)''', (uuid4(), LEGACY, digest('c' * 40)))
    url = f'/api/device/samples/{identity}/evaluations'
    headers = {'Authorization': 'Bearer ' + 'c' * 40, 'X-Inspection-Lease': 'origin-lease'.ljust(32, 'x')}
    db.execute('UPDATE orangevision_web.inspection_sessions SET lease_hash=%s', (digest(headers['X-Inspection-Lease']),))
    with TestClient(create_app(settings)) as client:
        answer = client.get(url, headers=headers)
        assert answer.status_code == 200, answer.text
        assert answer.json()['sample_id'] == str(identity) and 'user_id' not in answer.json()
        assert client.get(url, headers={**headers, 'X-Inspection-Lease': 'y' * 32}).status_code == 404
        db.execute('UPDATE orangevision_web.device_credentials SET revoked_at=now()')
        assert client.get(url, headers=headers).status_code == 401
    assert db.execute('SELECT count(*) AS n FROM orangevision_web.gemini_jobs').fetchone()['n'] == 0


def test_http_authorization_csrf_and_decision_replay(dual):
    db, settings = dual
    identity, _ = sample(db)
    app = create_app(settings)
    session = {'user': {'id': A}, 'csrf_token': 'synthetic-csrf'}
    app.dependency_overrides[current_session] = lambda: session
    headers = {'Origin': settings.origins[0], 'X-CSRF-Token': 'synthetic-csrf'}
    url = f'/api/samples/{identity}'
    with TestClient(app) as client:
        body = {'request_id': str(uuid4())}
        assert client.post(url + '/evaluations/gemini', json=body).status_code == 403
        assert client.post(url + '/evaluations/gemini', json=body, headers=headers).status_code == 202
        command = decision().model_dump(mode='json')
        first = client.post(url + '/decisions', json=command, headers=headers)
        assert first.status_code == 200, first.text
        assert first.json()['decision']['revision'] == 1 and first.json()['analysis_id']
        assert client.post(url + '/decisions', json=command, headers=headers).json()['decision']['revision'] == 1
        session['user']['id'] = B
        assert client.post(url + '/evaluations/gemini', json=body, headers=headers).status_code == 404
        assert client.post(url + '/decisions', json=command, headers=headers).status_code == 404


# --- Publicação automática (WEB_GEMINI_AUTO_ADOPT=true): fluxo completo com banco real ---

class Fixed:
    def __init__(self, category='APROVADA', failure=None):
        self.category, self.failure = category, failure

    def assess(self, image, model):
        if self.failure:
            raise self.failure
        return VisualAssessment(evaluable=True, classification=self.category, reason='Casca sintética.'), {'total_tokens': 10}


def auto(settings):
    return replace(settings, gemini_auto_adopt=True)


def latest_decision(db, identity):
    return db.execute('SELECT origin,classification,revision FROM orangevision_web.sample_decisions '
                      'WHERE sample_id=%s ORDER BY revision DESC LIMIT 1', (identity,)).fetchone()


def test_auto_local_waits_for_gemini_and_agreement_publishes_with_local_metrics(dual):
    db, settings = dual
    settings = auto(settings)
    identity, claim = sample(db)
    saved = finish(settings, identity, result(claim))
    assert saved['analysis_id'] is None  # local sozinho não publica mais
    assert AnalysisRepository(settings).summarize(A, Filters())['total'] == 0
    request(settings, identity)
    assert process_once(GeminiJobs(settings), Fixed('APROVADA')) == 'completed'
    queries = AnalysisRepository(settings)
    assert queries.summarize(A, Filters())['approved'] == 1
    assert latest_decision(db, identity)['origin'] == 'local'
    analysis = SampleRepository(settings).listing(A, 20, 0)['items'][0]['analysis_id']
    assert queries.find_analysis(A, analysis)['metrics']['orange_color_ratio'] == .8
    # Repetir o ciclo não duplica.
    from web_api.infrastructure.evaluation_repository import AutoAdoption
    assert AutoAdoption(settings).run(identity, A) == 'existing_decision'
    assert queries.summarize(A, Filters())['total'] == 1


def test_auto_divergence_waits_for_person(dual):
    db, settings = dual
    settings = auto(settings)
    identity, claim = sample(db)
    finish(settings, identity, result(claim))
    request(settings, identity)
    process_once(GeminiJobs(settings), Fixed('ATENCAO'))
    listed = SampleRepository(settings).listing(A, 20, 0)['items'][0]
    assert listed['comparison'] == 'divergence' and listed['analysis_id'] is None
    assert latest_decision(db, identity) is None
    assert AnalysisRepository(settings).summarize(A, Filters())['total'] == 0


def test_auto_local_failed_uses_gemini(dual):
    db, settings = dual
    settings = auto(settings)
    identity, claim = sample(db)
    finish(settings, identity, result(claim, 'not_evaluable'))
    request(settings, identity)
    process_once(GeminiJobs(settings), Fixed('ATENCAO'))
    assert AnalysisRepository(settings).summarize(A, Filters())['attention'] == 1
    assert latest_decision(db, identity)['origin'] == 'gemini'


def test_auto_gemini_first_then_local_agrees_publishes_on_local_result(dual):
    db, settings = dual
    settings = auto(settings)
    identity, claim = sample(db)
    request(settings, identity)
    process_once(GeminiJobs(settings), Fixed('APROVADA'))
    assert AnalysisRepository(settings).summarize(A, Filters())['total'] == 0  # espera o Pi
    saved = finish(settings, identity, result(claim))
    assert saved['analysis_id'] is not None
    assert AnalysisRepository(settings).summarize(A, Filters())['approved'] == 1


def test_auto_gemini_permanent_failure_lets_local_stand_alone(dual):
    db, settings = dual
    settings = auto(settings)
    identity, claim = sample(db)
    finish(settings, identity, result(claim))
    request(settings, identity)
    assert process_once(GeminiJobs(settings), Fixed(failure=ProviderFailure('response_invalid'))) == 'response_invalid'
    assert AnalysisRepository(settings).summarize(A, Filters())['approved'] == 1
    assert latest_decision(db, identity)['origin'] == 'local'


def test_auto_human_correction_after_auto_publication_counts_once(dual):
    db, settings = dual
    settings = auto(settings)
    identity, claim = sample(db)
    finish(settings, identity, result(claim))
    request(settings, identity)
    process_once(GeminiJobs(settings), Fixed('APROVADA'))
    EvaluationRepository(settings).decide(A, identity, decision(category='REVISAR', revision=1))
    summary = AnalysisRepository(settings).summarize(A, Filters())
    assert summary['total'] == 1 and summary['review'] == 1


def test_site_close_takes_effect_immediately_and_device_sees_closed(dual):
    from web_api.infrastructure.inspection_repository import InspectionRepository

    db, settings = dual
    session = origin_session(db)
    before = captured(db, session)
    closed = InspectionRepository(settings).request_close(A, session)
    assert closed['state'] == 'closed'
    device = InspectionRepository(settings).device_session(LEGACY, session, digest('origin-lease'))
    assert device['state'] == 'closed'
    # Foto tirada antes do encerramento continua consultável pelo equipamento.
    assert consult(settings, before)['sample_id'] == before
    # Sessão antiga presa em 'closing' também é liberada.
    stuck = origin_session(db, state='closing')
    assert InspectionRepository(settings).request_close(A, stuck)['state'] == 'closed'
