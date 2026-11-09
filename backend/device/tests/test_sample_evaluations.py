from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import cv2
import numpy as np
import pytest
from backend.device.api import ApiFailure, DeviceApi, Offline
from backend.device.camera_dashboard import DashboardStatus, _wrapped, render_frame
from backend.device.camera_window import maintain_camera
from backend.device.sample_evaluations import (
    ACTIVE_INTERVAL,
    MAX_BACKOFF,
    SETTLED_INTERVAL,
    evaluation_view,
    poll_sample_evaluation,
)
from backend.device.storage import Store

NOW = 1000.0
LEASE = 'lease-origem-' + 'x' * 32


def response(sample_id, inspection_id, *, state='completed', job=None, evaluations=(), **extra):
    moment = datetime.now(UTC).isoformat()
    return {
        'sample_id': sample_id, 'inspection_id': inspection_id, 'state': state,
        'captured_at': moment, 'evaluations': list(evaluations), 'gemini_job': job,
        'decision': None, 'comparison': 'pending',
        'access_expires_at': (datetime.now(UTC) + timedelta(hours=1)).isoformat(),
        'observed_at': moment, **extra,
    }


def job(state, error_code=None):
    return {
        'id': str(uuid4()), 'state': state, 'attempts': 1, 'error_code': error_code,
        'updated_at': datetime.now(UTC).isoformat(),
    }


def evaluation(origin, classification='REVISAR', state='completed', reason='Motivo informado.'):
    return {
        'id': str(uuid4()), 'origin': origin, 'state': state, 'classification': classification,
        'reason': reason, 'criteria_version': 'c1', 'model_version': None,
        'created_at': datetime.now(UTC).isoformat(),
    }


@pytest.fixture
def store(tmp_path):
    result = Store(tmp_path / 'evaluations.db')
    result.initialize()
    return result


def captured(store, *, original_known=True):
    """Cria o vínculo real: captura local -> amostra remota -> sessão de origem."""
    grant_id, photo_id, sample_id = str(uuid4()), str(uuid4()), str(uuid4())
    store.save_grant({'id': grant_id, 'lease_token': LEASE})
    store.save_camera_sample(photo_id, grant_id, datetime.now(UTC).isoformat(), b'jpeg')
    if not original_known:
        with store.db() as db:
            db.execute('UPDATE camera_sample_outbox SET original_source_known=0')
    store.record_sample_receipt(photo_id, sample_id)
    return SimpleNamespace(grant=grant_id, photo=photo_id, sample=sample_id)


class Api:
    def __init__(self, reply):
        self.reply = reply
        self.calls = []

    def sample_evaluations(self, sample_id, lease):
        self.calls.append((sample_id, lease))
        if isinstance(self.reply, Exception):
            raise self.reply
        return self.reply


def tracking(store, sample_id):
    with store.db() as db:
        return dict(db.execute(
            'SELECT * FROM sample_evaluation_tracking WHERE sample_id=?', (sample_id,)
        ).fetchone())


def poll(store, api, now=NOW):
    return poll_sample_evaluation(store, api, now=lambda: now)


def test_client_uses_published_route_with_origin_lease(monkeypatch):
    client = DeviceApi(SimpleNamespace(api_url='https://api.test', credential='secret'))
    seen = {}

    def request(method, url, **kwargs):
        seen.update(method=method, url=url, **kwargs)
        return SimpleNamespace(status_code=200, headers={}, json=lambda: {'ok': True})

    monkeypatch.setattr(client.http, 'request', request)
    sample_id = str(uuid4())
    assert client.sample_evaluations(sample_id, LEASE) == {'ok': True}
    assert seen['method'] == 'GET'
    assert seen['url'] == f'https://api.test/api/device/samples/{sample_id}/evaluations'
    assert seen['headers'] == {'X-Inspection-Lease': LEASE}
    assert seen['json'] is None
    assert client.http.headers['Authorization'] == 'Bearer secret'


def test_query_uses_lease_of_origin_session_even_after_new_session(store):
    item = captured(store)
    store.save_grant({'id': str(uuid4()), 'lease_token': 'lease-de-outra-sessao-' + 'y' * 32})
    api = Api(response(item.sample, item.grant))
    assert poll(store, api) == item.sample
    assert api.calls == [(item.sample, LEASE)]


def test_sample_without_known_origin_session_is_never_queried(store):
    item = captured(store, original_known=False)
    api = Api(response(item.sample, item.grant))
    assert poll(store, api) is None
    assert api.calls == []
    view = evaluation_view(store.sample_evaluation(item.sample))
    assert 'Sem sessao de origem' in view['notice']


def test_site_sample_without_local_capture_is_never_queried(store):
    sample_id = str(uuid4())
    store.start_sample_work(sample_id, {'claim_id': str(uuid4()), 'lease_token': 'z' * 43})
    api = Api(None)
    assert poll(store, api) is None
    assert api.calls == []


@pytest.mark.parametrize(
    ('sample_state', 'gemini_job', 'expected', 'interval'),
    [
        ('processing', None, 'active', ACTIVE_INTERVAL),
        ('completed', 'running', 'active', ACTIVE_INTERVAL),
        ('completed', 'retry_wait', 'active', ACTIVE_INTERVAL),
        ('completed', None, 'active', SETTLED_INTERVAL),
        ('awaiting_review', 'completed', 'active', SETTLED_INTERVAL),
        ('completed', 'completed', 'done', 0),
        ('failed', 'failed', 'done', 0),
    ],
)
def test_poll_interval_and_terminal_state(store, sample_state, gemini_job, expected, interval):
    item = captured(store)
    reply = response(
        item.sample, item.grant, state=sample_state, job=job(gemini_job) if gemini_job else None
    )
    poll(store, Api(reply))
    row = tracking(store, item.sample)
    assert row['tracking'] == expected
    assert row['next_poll_at'] == NOW + interval
    api = Api(reply)
    poll(store, api, NOW + interval - 1)
    assert api.calls == []
    poll(store, api, NOW + interval)
    assert len(api.calls) == (1 if expected == 'active' else 0)


@pytest.mark.parametrize('status', [403, 404, 410, 422])
def test_lost_authorization_stops_and_keeps_last_data(store, status):
    item = captured(store)
    poll(store, Api(response(
        item.sample, item.grant, evaluations=[evaluation('gemini')], job=job('running'),
    )))
    api = Api(ApiFailure(status))
    poll(store, api, NOW + ACTIVE_INTERVAL)
    assert tracking(store, item.sample)['tracking'] == 'stopped'
    poll(store, api, NOW + 10 ** 6)
    assert len(api.calls) == 1
    record = store.sample_evaluation(item.sample)
    assert record['response']['evaluations'][0]['classification'] == 'REVISAR'
    assert 'site' in evaluation_view(record)['notice']


def test_offline_preserves_data_and_backs_off(store):
    item = captured(store)
    poll(store, Api(response(item.sample, item.grant, job=job('queued'))))
    api = Api(Offline('sem rede'))
    moments = []
    now = NOW + ACTIVE_INTERVAL
    for _ in range(7):
        poll(store, api, now)
        now = tracking(store, item.sample)['next_poll_at']
        moments.append(now)
    gaps = [after - before for before, after in zip(moments, moments[1:], strict=False)]
    assert gaps == sorted(gaps)
    assert gaps[-1] == MAX_BACKOFF
    record = store.sample_evaluation(item.sample)
    assert record['response'] is not None
    view = evaluation_view(record)
    assert 'atualizacao pendente' in view['notice']
    assert view['gemini'] == 'Gemini: na fila da API.'


def test_retry_after_and_credential_refusal_keep_tracking(store):
    item = captured(store)
    poll(store, Api(ApiFailure(429, retry_after=900)))
    assert tracking(store, item.sample)['next_poll_at'] == NOW + 900
    poll(store, Api(ApiFailure(401)), NOW + 900)
    row = tracking(store, item.sample)
    assert (row['tracking'], row['next_poll_at']) == ('active', NOW + 900 + MAX_BACKOFF)


@pytest.mark.parametrize(
    'tamper',
    [
        {'sample_id': str(uuid4())}, {'inspection_id': str(uuid4())}, {'state': 'desconhecido'},
        {'comparison': 'talvez'}, {'evaluations': [{'origin': 'gemini'}]}, {'observed_at': None},
        {'gemini_job': {'state': 'pausado'}}, {'decision': {'origin': 'site'}},
    ],
)
def test_response_outside_contract_or_of_other_capture_is_not_persisted(store, tamper):
    item = captured(store)
    good = response(item.sample, item.grant, job=job('queued'))
    poll(store, Api(good))
    poll(store, Api({**good, **tamper}), NOW + ACTIVE_INTERVAL)
    record = store.sample_evaluation(item.sample)
    assert record['response'] == good
    assert record['last_error'] == 'incompatible'
    assert record['tracking'] == 'active'


def test_local_and_gemini_stay_separate_and_divergence_is_reported(store):
    item = captured(store)
    reply = response(
        item.sample, item.grant, job=job('completed'),
        evaluations=[
            evaluation('local', 'APROVADA', reason='Criterio local.'),
            evaluation('gemini', 'REVISAR', reason='Mancha observada.'),
        ],
        comparison='divergence',
        decision={
            'revision': 2, 'origin': 'human', 'classification': 'ATENCAO',
            'reason': 'Decisao do operador.', 'created_at': datetime.now(UTC).isoformat(),
        },
    )
    poll(store, Api(reply))
    view = evaluation_view(Store(store.path).sample_evaluation(item.sample))
    assert view['gemini'] == 'Gemini: REVISAR'
    assert view['tone'] == 'red'
    assert view['detail'] == 'Mancha observada.'
    assert view['local'] == 'APROVADA: Criterio local.'
    assert view['adopted'] == 'Adotado (human, rev. 2): ATENCAO'
    assert view['comparison'] == 'Local e Gemini divergem.'
    assert view['notice'] == 'Acompanhamento concluido.'
    assert (view['photo_id'], view['inspection_id']) == (item.photo, item.grant)


@pytest.mark.parametrize(
    ('reply_job', 'expected'),
    [
        (None, 'Gemini: nao agendado.'),
        ('queued', 'Gemini: na fila da API.'),
        ('running', 'Gemini: em processamento.'),
        ('retry_wait', 'Gemini: aguardando nova tentativa.'),
    ],
)
def test_job_states_do_not_invent_a_result(store, reply_job, expected):
    item = captured(store)
    poll(store, Api(response(item.sample, item.grant, job=job(reply_job) if reply_job else None)))
    view = evaluation_view(store.sample_evaluation(item.sample))
    assert view['gemini'] == expected
    assert view['adopted'] == 'Adotado: sem decisao.'


def test_failed_job_shows_code_without_inventing_evaluation(store):
    item = captured(store)
    poll(store, Api(response(item.sample, item.grant, job=job('failed', 'quota'))))
    view = evaluation_view(store.sample_evaluation(item.sample))
    assert view['gemini'] == 'Gemini: falhou (quota).'
    assert view['tone'] == 'red'


def test_late_reply_of_other_capture_never_reaches_displayed_sample(store):
    old = captured(store)
    new = captured(store)
    status = DashboardStatus()
    status.handle({'kind': 'synced', 'sample_id': new.sample})
    store.save_sample_evaluation(
        old.sample,
        response(old.sample, old.grant, evaluations=[evaluation('gemini', 'APROVADA')]),
        'done', 0,
    )
    status.refresh(store, None)
    assert status.evaluation['gemini'] == 'Gemini: aguardando consulta a Web API.'
    assert status.evaluation['photo_id'] == new.photo
    local_card = status.sample
    status.handle({'kind': 'synced', 'sample_id': old.sample})
    status.refresh(store, None)
    assert status.evaluation['gemini'] == 'Gemini: APROVADA'
    assert status.sample == local_card


def test_evaluation_is_restored_after_restart(store):
    item = captured(store)
    poll(store, Api(response(item.sample, item.grant, evaluations=[evaluation('gemini')])))
    status = DashboardStatus()
    status.restore(Store(store.path))
    status.refresh(Store(store.path), None)
    assert status.evaluation['gemini'] == 'Gemini: REVISAR'


def test_maintenance_polls_read_only_and_failure_does_not_stop_it(store):
    item = captured(store)
    calls = []
    forbidden = SimpleNamespace(
        heartbeat_samples=lambda *a: None,
        claim_sample=lambda attempt: calls.append('claim'),
        sample_evaluations=lambda sample_id, lease: (_ for _ in ()).throw(Offline('rede')),
    )
    events = []
    maintain_camera(store, forbidden, None, None, events.append)
    assert calls == ['claim']  # A fila existente segue igual; a consulta não usa /claim.
    assert 'connection_error' not in [event['kind'] for event in events]
    assert tracking(store, item.sample)['last_error'] == 'offline'


def render(status, **kwargs):
    return render_frame(
        np.zeros((480, 640, 3), np.uint8), {'status': 'not_detected'},
        False, False, False, False, False, '', '', dashboard=status, **kwargs,
    )


def test_details_page_shows_full_chain_and_does_not_hang(store, monkeypatch):
    item = captured(store)
    poll(store, Api(response(item.sample, item.grant, evaluations=[evaluation('gemini')])))
    status = DashboardStatus()
    status.handle({'kind': 'synced', 'sample_id': item.sample})
    status.refresh(store, None)
    texts = []
    original = cv2.putText

    def record(image, text, *args, **kwargs):
        texts.append(text)
        return original(image, text, *args, **kwargs)

    monkeypatch.setattr(cv2, 'putText', record)
    pages = max(1, (len(_wrapped(status.analysis_detail, 602, 0.42)) + 6) // 7)
    render(status, details=True, details_page=pages)
    assert any(item.photo in text for text in texts)
    assert any(item.sample in text for text in texts)
    assert any(item.grant in text for text in texts)
    assert 'Motivo informado.' in texts
    assert 'Amostra: nenhuma' not in texts  # A pagina de motivo nao fica desenhada por baixo.


def test_main_panel_text_stays_inside_its_cards(store, monkeypatch):
    status = DashboardStatus()
    status.evaluation = {**status.evaluation, 'gemini': 'Gemini: REVISAR'}
    points = []
    original = cv2.putText

    def record(image, text, point, *args, **kwargs):
        points.append((text, point))
        return original(image, text, point, *args, **kwargs)

    monkeypatch.setattr(cv2, 'putText', record)
    render(status)
    gemini = next(point for text, point in points if text == 'Gemini: REVISAR')
    assert 418 < gemini[1] < 534
    side_panel = [
        point for _, point in points if point[0] == 678 and not 84 <= point[1] <= 534
    ]
    assert side_panel == []  # Nada do painel lateral invade a faixa dos botões (555-605).
