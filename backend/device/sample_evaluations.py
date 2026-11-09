"""Acompanhamento somente leitura das avaliações de uma captura pela Web API.

Consome GET /api/device/samples/{id}/evaluations com a lease da sessão de origem.
Não agenda Gemini, não consome a fila e não substitui a avaliação local.
"""

import time
from datetime import datetime
from uuid import UUID

from .api import ApiFailure, Offline

ACTIVE_INTERVAL = 15
SETTLED_INTERVAL = 120
BASE_BACKOFF = 30
MAX_BACKOFF = 600
# Perda de autorização ou de prazo: não adianta repetir esta consulta.
STOP_STATUSES = (403, 404, 410, 422)

SAMPLE_STATES = {
    'received', 'queued', 'processing', 'awaiting_review', 'completed', 'not_evaluable', 'failed',
}
EVALUATION_STATES = {'completed', 'awaiting_review', 'not_evaluable', 'failed'}
JOB_STATES = {'queued', 'running', 'retry_wait', 'completed', 'failed'}
CATEGORIES = {'APROVADA', 'ATENCAO', 'REVISAR'}
COMPARISONS = {
    'pending': 'Comparacao local x Gemini pendente.',
    'agreement': 'Local e Gemini concordam.',
    'divergence': 'Local e Gemini divergem.',
    'inconclusive': 'Comparacao local x Gemini inconclusiva.',
}
CATEGORY_TONES = {'APROVADA': 'green', 'ATENCAO': 'orange', 'REVISAR': 'red'}


def _require(condition):
    if not condition:
        raise ValueError


def validate_response(response, sample_id, inspection_id):
    """Rejeita resposta fora do contrato ou de outra amostra/sessão, sem persisti-la."""
    try:
        _require(UUID(response['sample_id']) == UUID(sample_id))
        _require(UUID(response['inspection_id']) == UUID(inspection_id))
        _require(response['state'] in SAMPLE_STATES)
        _require(response['comparison'] in COMPARISONS)
        datetime.fromisoformat(response['observed_at'])
        datetime.fromisoformat(response['access_expires_at'])
        for item in response['evaluations']:
            _require(item['origin'] in ('local', 'gemini'))
            _require(item['state'] in EVALUATION_STATES)
            _require(item['classification'] in CATEGORIES or item['classification'] is None)
            _require(isinstance(item['reason'], str))
            datetime.fromisoformat(item['created_at'])
        job = response['gemini_job']
        if job is not None:
            _require(job['state'] in JOB_STATES)
        decision = response['decision']
        if decision is not None:
            _require(decision['origin'] in ('local', 'gemini', 'human'))
            _require(decision['classification'] in CATEGORIES)
            _require(isinstance(decision['reason'], str))
    except (KeyError, TypeError, ValueError, AttributeError) as exc:
        raise RuntimeError('Resposta de avaliações incompatível com o contrato.') from exc


def next_step(response):
    """Encerra só com Gemini e amostra terminais; sem job, o site ainda pode agendar um."""
    job = response['gemini_job']
    job_state = job['state'] if job else None
    settled = response['state'] in ('completed', 'not_evaluable', 'failed')
    if job_state in ('completed', 'failed') and settled:
        return 'done', 0
    if job_state in ('queued', 'running', 'retry_wait') or response['state'] in (
        'received', 'queued', 'processing',
    ):
        return 'active', ACTIVE_INTERVAL
    return 'active', SETTLED_INTERVAL


def _backoff(failures, retry_after=None):
    return max(min(MAX_BACKOFF, BASE_BACKOFF * 2**failures), retry_after or 0)


def poll_sample_evaluation(store, api, *, now=time.time):
    """Faz no máximo uma consulta; deve rodar fora da thread da câmera e da interface."""
    due = store.due_sample_evaluation(now())
    if due is None:
        return None
    sample_id = due['sample_id']
    try:
        response = api.sample_evaluations(sample_id, due['lease_token'])
        validate_response(response, sample_id, due['inspection_id'])
    except Offline:
        store.sample_evaluation_failure(
            sample_id, 'offline', 'active', now() + _backoff(due['failures'])
        )
    except ApiFailure as exc:
        error = f'HTTP{exc.status}'
        if exc.status in STOP_STATUSES:
            store.sample_evaluation_failure(sample_id, error, 'stopped', 0)
        else:
            # 401 é da credencial do equipamento: pode voltar após update-credential.
            delay = MAX_BACKOFF if exc.status == 401 else _backoff(due['failures'], exc.retry_after)
            store.sample_evaluation_failure(sample_id, error, 'active', now() + delay)
    except RuntimeError:
        store.sample_evaluation_failure(
            sample_id, 'incompatible', 'active', now() + _backoff(due['failures'])
        )
    else:
        tracking, interval = next_step(response)
        store.save_sample_evaluation(sample_id, response, tracking, now() + interval)
    return sample_id


def _latest(response, origin):
    items = [item for item in response['evaluations'] if item['origin'] == origin]
    return max(items, key=lambda item: item['created_at']) if items else None


def _gemini(response):
    job = response['gemini_job']
    job_state = job['state'] if job else None
    if job_state == 'queued':
        return 'Gemini: na fila da API.', 'orange'
    if job_state == 'running':
        return 'Gemini: em processamento.', 'orange'
    if job_state == 'retry_wait':
        return 'Gemini: aguardando nova tentativa.', 'orange'
    item = _latest(response, 'gemini')
    if item:
        if item['state'] == 'completed' and item['classification']:
            return 'Gemini: ' + item['classification'], CATEGORY_TONES[item['classification']]
        return {
            'not_evaluable': ('Gemini: imagem nao avaliavel.', 'muted'),
            'failed': ('Gemini: avaliacao falhou.', 'red'),
        }.get(item['state'], ('Gemini: aguardando revisao.', 'orange'))
    if job_state == 'failed':
        code = job.get('error_code')
        return 'Gemini: falhou' + (f' ({code}).' if code else '.'), 'red'
    if job_state == 'completed':
        return 'Gemini: concluido sem avaliacao registrada.', 'muted'
    return 'Gemini: nao agendado.', 'muted'


def _notice(record):
    error = record['last_error']
    if error == 'offline':
        return 'Sem internet: atualizacao pendente. Dados preservados.'
    if error == 'incompatible':
        return 'Resposta incompativel da API: atualizacao pendente.'
    if error == 'HTTP410':
        return 'Prazo de consulta encerrado; o resultado continua no site.'
    if error == 'HTTP403':
        return 'Vinculo do equipamento removido: consulta encerrada. Veja o site.'
    if error == 'HTTP404':
        return 'API nao liberou a consulta para esta sessao: encerrada. Veja o site.'
    if error == 'HTTP401':
        return 'Credencial recusada: atualize-a; consulta pendente.'
    if error and record['tracking'] == 'stopped':
        return f'Consulta encerrada ({error}). Veja o site.'
    if error:
        return f'API indisponivel ({error}): atualizacao pendente.'
    if record['tracking'] == 'done':
        return 'Acompanhamento concluido.'
    return 'Atualizacao em segundo plano.'


def evaluation_view(record):
    """Textos do painel; a avaliação local e a da API nunca se substituem."""
    view = {
        'gemini': 'Gemini: sem dados.', 'tone': 'muted', 'detail': 'Sem justificativa recebida.',
        'local': 'Sem avaliacao local registrada na API.', 'adopted': 'Adotado: sem decisao.',
        'comparison': 'Comparacao local x Gemini indisponivel.',
        'notice': 'Sem amostra para acompanhar.', 'observed': 'Sem consulta concluida.',
        'photo_id': 'nenhuma', 'inspection_id': 'nenhuma',
    }
    if record is None:
        return view
    view['photo_id'] = record['photo_id'] or 'nenhuma'
    view['inspection_id'] = record['inspection_id'] or 'desconhecida'
    if not record['photo_id'] or not record['inspection_id']:
        view['notice'] = 'Sem sessao de origem neste equipamento. Acompanhe no site.'
        return view
    view['notice'] = _notice(record)
    response = record['response']
    if response is None:
        view['gemini'] = 'Gemini: aguardando consulta a Web API.'
        return view
    view['gemini'], view['tone'] = _gemini(response)
    gemini = _latest(response, 'gemini')
    if gemini:
        view['detail'] = gemini['reason'] or view['detail']
    job = response['gemini_job']
    if job and job.get('error_code') and not gemini:
        view['detail'] = 'Codigo informado pela API: ' + str(job['error_code'])
    local = _latest(response, 'local')
    if local:
        view['local'] = f'{local["classification"] or local["state"]}: {local["reason"]}'
    decision = response['decision']
    if decision:
        view['adopted'] = (
            f'Adotado ({decision["origin"]}, rev. {decision.get("revision")}): '
            f'{decision["classification"]}'
        )
    view['comparison'] = COMPARISONS[response['comparison']]
    observed = datetime.fromisoformat(response['observed_at']).astimezone()
    view['observed'] = f'Ultimo dado da API: {observed:%d/%m %H:%M:%S}.'
    return view
