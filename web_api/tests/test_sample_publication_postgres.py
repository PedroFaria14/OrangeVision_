import os
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import psycopg
import pytest
from fastapi.testclient import TestClient

from web_api.api.dependencies import current_session
from web_api.application.auth_service import digest
from web_api.application.errors import ApplicationError
from web_api.config import Settings
from web_api.contracts import Filters
from web_api.infrastructure.analysis_repository import AnalysisRepository
from web_api.infrastructure.sample_repository import SampleRepository
from web_api.main import create_app
from web_api.sample_contracts import SampleResult

from . import test_devices_postgres
from .test_devices_postgres import LEGACY, MIGRATIONS, A, B

device_db = test_devices_postgres.db

pytestmark = pytest.mark.skipif(not os.getenv('OV_DEVICE_TEST_DATABASE_URL'), reason='PostgreSQL descartável não configurado.')


@pytest.fixture
def prepared(device_db):
    db = device_db
    db.execute('''ALTER TABLE public.analises
        ADD COLUMN dispositivo_id uuid REFERENCES public.dispositivos(id),
        ADD COLUMN classificacao text, ADD COLUMN cor_media numeric,
        ADD COLUMN regioes_anormais numeric, ADD COLUMN circularidade numeric,
        ADD COLUMN assimetria numeric, ADD COLUMN score_visual numeric,
        ADD COLUMN versao_algoritmo varchar(50), ADD COLUMN criado_em timestamptz''')
    for name in ('003_image_samples.sql', '004_sample_executor_detection.sql', '005_sample_review_authorization.sql', '007_sample_analyses.sql'):
        db.execute((MIGRATIONS / name).read_text(), prepare=False)
    settings = Settings(os.environ['OV_DEVICE_TEST_DATABASE_URL'], ('https://example.test',), True, 3600, True)
    return db, settings


def sample(db, *, state='processing', owner=A, source_owner=A, with_session=True):
    identity, claim, session = uuid4(), uuid4(), uuid4()
    captured = datetime.now(UTC) - timedelta(minutes=1)
    if with_session:
        db.execute('''INSERT INTO orangevision_web.inspection_sessions
            (id,user_id,device_id,request_id,state,pairing_hash,pairing_expires_at,started_at,authorization_expires_at,closed_at)
            VALUES (%s,%s,%s,%s,'closed',%s,now(),now()-interval '10 minutes',now()+interval '1 hour',now())''',
            (session, source_owner, LEGACY, uuid4(), digest(str(session))))
    db.execute('''INSERT INTO orangevision_web.image_samples
        (id,user_id,request_id,source_hash,filename,image_data,width,height,state,device_id,
         claim_id,lease_hash,claim_expires_at,source_inspection_id,captured_at)
        VALUES (%s,%s,%s,'fixture','capture.jpg',%s,80,60,%s,%s,%s,%s,now()+interval '5 minutes',%s,%s)''',
        (identity, owner, uuid4(), b'fixture', state, LEGACY, claim, digest('lease'), session if with_session else None, captured if with_session else None))
    return identity, claim


def result(claim, state='completed'):
    return SampleResult(claim_id=claim, state=state, reason='Resultado sintético validado.',
        metrics={'orange_color_ratio': .8, 'abnormal_region_ratio': .1, 'circularity': .9, 'asymmetry': .05, 'visual_score': 85} if state == 'completed' else None,
        classification='APROVADA' if state == 'completed' else None,
        calibration_version='fixture-v1', algorithm_version='opencv-hsv-contour-v2', calibration_validated=state == 'completed').model_dump(mode='json')


def finish(settings, identity, payload):
    return SampleRepository(settings).finish(LEGACY, identity, digest('lease'), payload, digest(str(payload)), None)


def test_auto_publication_counts_once_and_preserves_owner_and_units(prepared):
    db, settings = prepared
    identity, claim = sample(db)
    payload = result(claim)
    with ThreadPoolExecutor(max_workers=2) as pool:
        answers = list(pool.map(lambda _: finish(settings, identity, payload), range(2)))
    assert answers[0]['analysis_id'] == answers[1]['analysis_id']
    db.execute('INSERT INTO orangevision_web.device_access VALUES (%s,%s)', (B, LEGACY))
    queries = AnalysisRepository(settings)
    assert queries.summarize(A, Filters())['approved'] == 1
    assert queries.summarize(B, Filters())['total'] == 0
    items, count = queries.list_analyses(A, Filters(), 20, 0)
    assert count == 1 and items[0]['metrics']['orange_color_ratio'] == .8
    assert items[0]['metrics']['asymmetry'] == .05
    assert items[0]['inspection_session_id'] is not None
    assert len(queries.aggregate_daily(A, Filters())) == 1
    assert SampleRepository(settings).publish(A, identity)['analysis_id'] == answers[0]['analysis_id']
    assert db.execute('SELECT count(*) AS n FROM public.analises').fetchone()['n'] == 1
    with pytest.raises(ApplicationError) as error:
        SampleRepository(settings).queue(A, identity, LEGACY)
    assert error.value.status_code == 409


@pytest.mark.parametrize('state', ['awaiting_review', 'not_evaluable', 'failed'])
def test_unclassified_results_never_enter_graphs(prepared, state):
    db, settings = prepared
    identity, claim = sample(db)
    assert finish(settings, identity, result(claim, state))['analysis_id'] is None
    assert AnalysisRepository(settings).summarize(A, Filters())['total'] == 0
    with pytest.raises(ApplicationError) as error:
        SampleRepository(settings).publish(A, identity)
    assert error.value.status_code == 409


@pytest.mark.parametrize('classification,key', [('APROVADA', 'approved'), ('ATENCAO', 'attention'), ('REVISAR', 'review')])
def test_each_quality_class_enters_its_own_counter(prepared, classification, key):
    db, settings = prepared
    identity, claim = sample(db)
    payload = result(claim)
    payload['classification'] = classification
    assert finish(settings, identity, payload)['analysis_id']
    counters = AnalysisRepository(settings).summarize(A, Filters())
    assert counters['total'] == 1 and counters[key] == 1


def test_changed_result_cannot_overwrite_published_analysis(prepared):
    db, settings = prepared
    identity, claim = sample(db)
    payload = result(claim)
    finish(settings, identity, payload)
    with pytest.raises(ApplicationError) as error:
        finish(settings, identity, {**payload, 'classification': 'REVISAR'})
    assert error.value.status_code == 409
    assert AnalysisRepository(settings).summarize(A, Filters())['approved'] == 1


def test_missing_migration_preserves_result_and_can_publish_after_activation(prepared):
    db, settings = prepared
    db.execute('ALTER TABLE orangevision_web.image_samples DROP COLUMN analysis_id')
    identity, claim = sample(db)
    saved = finish(settings, identity, result(claim))
    assert saved['state'] == 'completed' and saved['analysis_id'] is None
    with pytest.raises(ApplicationError) as error:
        SampleRepository(settings).publish(A, identity)
    assert error.value.status_code == 503
    db.execute((MIGRATIONS / '007_sample_analyses.sql').read_text(), prepare=False)
    assert SampleRepository(settings).publish(A, identity)['analysis_id']


@pytest.mark.parametrize('with_session,source_owner', [(False, A), (True, B)])
def test_upload_without_session_or_foreign_session_never_publishes(prepared, with_session, source_owner):
    db, settings = prepared
    identity, claim = sample(db, with_session=with_session, source_owner=source_owner)
    assert finish(settings, identity, result(claim))['analysis_id'] is None
    with pytest.raises(ApplicationError) as error:
        SampleRepository(settings).publish(A, identity)
    assert error.value.status_code == 409


def test_disabled_inspections_and_other_owner_cannot_publish(prepared):
    db, settings = prepared
    disabled = replace(settings, inspections_enabled=False)
    identity, claim = sample(db)
    assert finish(disabled, identity, result(claim))['analysis_id'] is None
    with pytest.raises(ApplicationError) as error:
        SampleRepository(settings).publish(B, identity)
    assert error.value.status_code == 404
    assert SampleRepository(settings).publish(A, identity)['analysis_id']


def test_capture_outside_authorized_window_does_not_publish(prepared):
    db, settings = prepared
    identity, claim = sample(db)
    db.execute("UPDATE orangevision_web.image_samples SET captured_at=now()-interval '1 day' WHERE id=%s", (identity,))
    assert finish(settings, identity, result(claim))['analysis_id'] is None
    assert AnalysisRepository(settings).summarize(A, Filters())['total'] == 0


def test_publication_failure_rolls_back_result_and_analysis(prepared):
    db, settings = prepared
    identity, claim = sample(db)
    db.execute("CREATE FUNCTION public.reject_analysis() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'fixture'; END $$")
    db.execute('CREATE TRIGGER reject_analysis BEFORE INSERT ON public.analises FOR EACH ROW EXECUTE FUNCTION public.reject_analysis()')
    try:
        with pytest.raises(psycopg.Error):
            finish(settings, identity, result(claim))
        row = db.execute('SELECT state,result_hash,analysis_id FROM orangevision_web.image_samples WHERE id=%s', (identity,)).fetchone()
        assert row == {'state': 'processing', 'result_hash': None, 'analysis_id': None}
        assert db.execute('SELECT count(*) AS n FROM public.analises').fetchone()['n'] == 0
    finally:
        db.execute('DROP FUNCTION public.reject_analysis() CASCADE')


def test_http_publish_requires_csrf_and_origin_and_is_idempotent(prepared):
    db, settings = prepared
    identity, claim = sample(db)
    finish(replace(settings, inspections_enabled=False), identity, result(claim))
    app = create_app(settings)
    app.dependency_overrides[current_session] = lambda: {'user': {'id': A}, 'csrf_token': 'fixture-csrf'}
    url = f'/api/samples/{identity}/analysis'
    with TestClient(app) as client:
        assert client.post(url).status_code == 403
        assert client.post(url, headers={'Origin': 'https://evil.example', 'X-CSRF-Token': 'fixture-csrf'}).status_code == 403
        headers = {'Origin': settings.origins[0], 'X-CSRF-Token': 'fixture-csrf'}
        first = client.post(url, headers=headers)
        assert first.status_code == 200, first.text
        assert first.json()['analysis_id']
        assert client.post(url, headers=headers).json()['analysis_id'] == first.json()['analysis_id']
        app.dependency_overrides[current_session] = lambda: {'user': {'id': B}, 'csrf_token': 'fixture-csrf'}
        assert client.post(url, headers=headers).status_code == 404
