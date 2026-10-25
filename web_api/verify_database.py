"""Verificação HTTP/banco real com registros temporários revertidos por ROLLBACK."""

import argparse
import secrets
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from unittest.mock import patch
from uuid import UUID, uuid4

import psycopg
from fastapi.testclient import TestClient
from psycopg.rows import dict_row

from .application.auth_service import digest
from .config import Settings
from .main import create_app


def verify(settings):
    run_id = uuid4().hex
    email = f'integration-{run_id}@example.com'
    identity = f'integration-{run_id}'
    payload = {
        'name': 'Integration verification',
        'email': email,
        'password': secrets.token_urlsafe(32),
    }
    results = {}
    user_id = None

    def expect(response, status, stage):
        if response.status_code != status:
            raise RuntimeError(f'{stage}: status inesperado {response.status_code}')
        results[stage] = status
        return response

    with psycopg.connect(
        settings.database_url, connect_timeout=5, autocommit=True, row_factory=dict_row
    ) as db:
        # Todas as escritas de autenticação ficam neste bloco e NUNCA são confirmadas.
        with db.transaction(force_rollback=True):
            db.execute('SET LOCAL statement_timeout = 10000')

            @contextmanager
            def sandbox_connection(_settings):
                # Savepoints preservam o fluxo após a tentativa de cadastro duplicado.
                with db.transaction():
                    yield db

            origin = settings.origins[0]
            with patch('web_api.infrastructure.auth_repository.connection', sandbox_connection):
                with TestClient(
                    create_app(settings), base_url=origin, client=(identity, 50000)
                ) as client:
                    headers = {'Origin': origin}
                    expect(
                        client.post('/api/auth/register', json=payload, headers=headers),
                        201,
                        'cadastro',
                    )
                    expect(
                        client.post('/api/auth/register', json=payload, headers=headers),
                        409,
                        'duplicidade',
                    )
                    expect(
                        client.post(
                            '/api/auth/login',
                            json={'email': email, 'password': 'wrong-password-for-test'},
                            headers=headers,
                        ),
                        401,
                        'senha_invalida',
                    )
                    credentials = {key: payload[key] for key in ('email', 'password')}
                    login = expect(
                        client.post('/api/auth/login', json=credentials, headers=headers),
                        200,
                        'login',
                    )
                    session = login.json()
                    user_id = UUID(session['user']['id'])
                    assert 'password_hash' not in session['user']
                    stored = db.execute(
                        'SELECT password_hash FROM orangevision_web.users WHERE id=%s', (user_id,)
                    ).fetchone()
                    assert stored['password_hash'].startswith('$argon2id$')
                    assert stored['password_hash'] != payload['password']
                    assert 'HttpOnly' in login.headers['set-cookie']
                    expect(client.get('/api/auth/session'), 200, 'sessao')
                    history = expect(
                        client.get('/api/analyses?limit=20&offset=0'), 200, 'historico_sem_vinculo'
                    )
                    assert history.json()['items'] == [] and history.json()['total'] == 0
                    summary = expect(client.get('/api/metrics/summary'), 200, 'resumo_sem_vinculo')
                    assert summary.json()['total'] == 0 and summary.json()['approval_rate'] is None
                    now = datetime.now(UTC)
                    series = expect(
                        client.get(
                            '/api/metrics/timeseries',
                            params={
                                'start': (now - timedelta(days=1)).isoformat(),
                                'end': now.isoformat(),
                            },
                        ),
                        200,
                        'serie_sem_vinculo',
                    )
                    assert series.json()['items'] == []
                    existing = db.execute('SELECT id FROM public.analises LIMIT 1').fetchone()
                    analysis_id = existing['id'] if existing else uuid4()
                    expect(client.get(f'/api/analyses/{analysis_id}'), 404, 'detalhe_sem_acesso')
                    expect(
                        client.post('/api/auth/logout', headers=headers), 403, 'csrf_obrigatorio'
                    )
                    expect(
                        client.post(
                            '/api/auth/logout',
                            headers={**headers, 'X-CSRF-Token': session['csrf_token']},
                        ),
                        204,
                        'logout',
                    )
                    expect(client.get('/api/auth/session'), 401, 'sessao_revogada')
                    expect(
                        client.post('/api/auth/login', json=credentials, headers=headers),
                        200,
                        'novo_login',
                    )
                    db.execute(
                        "UPDATE orangevision_web.sessions SET expires_at=now()-interval '1 second' WHERE user_id=%s",
                        (user_id,),
                    )
                    expect(client.get('/api/auth/session'), 401, 'sessao_expirada')

        # Uma transação independente confirma que nenhum registro de teste ficou salvo.
        assert (
            db.execute(
                'SELECT count(*) AS count FROM orangevision_web.users WHERE email=%s', (email,)
            ).fetchone()['count']
            == 0
        )
        assert (
            db.execute(
                'SELECT count(*) AS count FROM orangevision_web.sessions WHERE user_id=%s',
                (user_id,),
            ).fetchone()['count']
            == 0
        )
        buckets = [digest(f'ip:{identity}'), digest(f'email:{email}')]
        assert (
            db.execute(
                'SELECT count(*) AS count FROM orangevision_web.auth_attempts WHERE bucket=ANY(%s)',
                (buckets,),
            ).fetchone()['count']
            == 0
        )
    return results


def main():
    parser = argparse.ArgumentParser(
        description='Verificação explícita de autenticação no banco real, com rollback.'
    )
    parser.add_argument('--run', action='store_true')
    args = parser.parse_args()
    if not args.run:
        print(
            'Nenhuma execução. Após configurar banco e migration: python -m web_api.verify_database --run'
        )
        return
    try:
        results = verify(Settings.load())
        for stage, status in results.items():
            print(f'{stage}={status}')
        print(
            'OK: registros temporários revertidos; nenhuma conta, sessão ou contador de teste persistiu.'
        )
    except Exception as exc:
        print(
            f'Verificação falhou; tipo={type(exc).__name__}. A transação temporária foi encerrada sem commit.'
        )
        raise SystemExit(1) from None


if __name__ == '__main__':
    main()
