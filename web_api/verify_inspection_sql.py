"""Verificação explícita em namespaces transitórios: nenhuma migration nos schemas reais.

Usa LIKE apenas para copiar a estrutura (não dados) das duas tabelas legadas. Todas as
escritas/DDL e contas de teste ficam numa transação com rollback obrigatório. As rotas
usam o SQL real, redirecionado aos namespaces de teste. Não mede concorrência/carga.
"""

import argparse
import secrets
from contextlib import contextmanager
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

import psycopg
from fastapi.testclient import TestClient
from psycopg import sql
from psycopg.rows import dict_row

from .application.auth_service import digest
from .application.query_service import QueryService
from .config import Settings
from .contracts import Filters
from .infrastructure.analysis_repository import AnalysisRepository
from .infrastructure.passwords import hasher
from .main import create_app


def verify(settings):
    marker = uuid4().hex
    public_name = f'ov_verify_{marker}_p'
    web_name = f'ov_verify_{marker}_w'
    stages = []
    with psycopg.connect(
        settings.database_url, connect_timeout=5, autocommit=True, row_factory=dict_row
    ) as db:

        class Isolated:
            def execute(self, statement, params=None, **kwargs):
                # O snapshot do teste engloba DDL/fixtures. Só aqui não é possível
                # torná-lo read only a cada consulta; o modo real já tem teste separado.
                if statement.strip().startswith('SET TRANSACTION ISOLATION LEVEL'):
                    return db.execute('SELECT 1')
                rewritten = statement.replace('orangevision_web', web_name).replace(
                    'public.', public_name + '.'
                )
                return db.execute(rewritten, params, **kwargs)

            def transaction(self):
                return db.transaction()

        proxy = Isolated()

        @contextmanager
        def scoped_connection(_settings):
            with db.transaction():
                yield proxy

        with db.transaction(force_rollback=True):
            db.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ')
            db.execute('SET LOCAL statement_timeout = 30000')
            db.execute('SET LOCAL lock_timeout = 5000')
            db.execute(sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(public_name)))
            db.execute(sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(web_name)))
            for table in ('dispositivos', 'analises'):
                db.execute(
                    sql.SQL('CREATE TABLE {}.{} (LIKE public.{} INCLUDING ALL)').format(
                        sql.Identifier(public_name), sql.Identifier(table), sql.Identifier(table)
                    )
                )
            db.execute(sql.SQL('SET LOCAL search_path TO {}').format(sql.Identifier(public_name)))
            for name in ('001_web_auth.sql', '002_inspection_sessions.sql'):
                script = (Path(__file__).parent / 'migrations' / name).read_text(encoding='utf-8')
                body = '\n'.join(
                    line
                    for line in script.splitlines()
                    if line.strip() not in ('BEGIN;', 'COMMIT;')
                )
                proxy.execute(body, prepare=False)
            stages.append('ddl_001_002_isoladas=OK')
            device_id, other_device = uuid4(), uuid4()
            user_a, user_b = uuid4(), uuid4()
            password = secrets.token_urlsafe(32)
            for user_id, label in ((user_a, 'A'), (user_b, 'B')):
                proxy.execute(
                    'INSERT INTO orangevision_web.users(id,name,email,password_hash) VALUES (%s,%s,%s,%s)',
                    (
                        user_id,
                        f'SQL synthetic {label}',
                        f'{marker}-{label.lower()}@example.com',
                        hasher.hash(password),
                    ),
                )
            for identity in (device_id, other_device):
                proxy.execute(
                    "INSERT INTO public.dispositivos(id,nome,status,criado_em) VALUES (%s,'SQL synthetic device','offline',now())",
                    (identity,),
                )
            for owner in (user_a, user_b):
                proxy.execute(
                    'INSERT INTO orangevision_web.device_access(user_id,device_id) VALUES (%s,%s)',
                    (owner, device_id),
                )
            credential, other_credential = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
            for identity, token in ((device_id, credential), (other_device, other_credential)):
                proxy.execute(
                    'INSERT INTO orangevision_web.device_credentials(id,device_id,token_hash) VALUES (%s,%s,%s)',
                    (uuid4(), identity, digest(token)),
                )
            enabled = replace(settings, inspections_enabled=True)
            origin = settings.origins[0]

            def expect(response, status):
                if response.status_code != status:
                    raise RuntimeError(
                        f'Unexpected HTTP status {response.status_code}, expected {status}'
                    )
                return response.json() if status != 204 else None

            with (
                patch('web_api.infrastructure.auth_repository.connection', scoped_connection),
                patch('web_api.infrastructure.inspection_repository.connection', scoped_connection),
                patch('web_api.infrastructure.analysis_repository.connection', scoped_connection),
            ):
                with (
                    TestClient(
                        create_app(enabled), base_url=origin, client=(marker + 'a', 50001)
                    ) as a,
                    TestClient(
                        create_app(enabled), base_url=origin, client=(marker + 'b', 50002)
                    ) as b,
                    TestClient(create_app(enabled), base_url=origin) as device,
                ):
                    csrf_a = expect(
                        a.post(
                            '/api/auth/login',
                            json={'email': marker + '-a@example.com', 'password': password},
                            headers={'Origin': origin},
                        ),
                        200,
                    )['csrf_token']
                    csrf_b = expect(
                        b.post(
                            '/api/auth/login',
                            json={'email': marker + '-b@example.com', 'password': password},
                            headers={'Origin': origin},
                        ),
                        200,
                    )['csrf_token']
                    ha, hb = (
                        {'Origin': origin, 'X-CSRF-Token': csrf_a},
                        {'Origin': origin, 'X-CSRF-Token': csrf_b},
                    )
                    code_a, code_b = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
                    start_a = {
                        'device_id': str(device_id),
                        'request_id': str(uuid4()),
                        'pairing_code': code_a,
                    }
                    first = expect(a.post('/api/inspections', json=start_a, headers=ha), 201)
                    assert (
                        expect(a.post('/api/inspections', json=start_a, headers=ha), 201)['id']
                        == first['id']
                    )
                    start_b = {
                        'device_id': str(device_id),
                        'request_id': str(uuid4()),
                        'pairing_code': code_b,
                    }
                    expect(b.post('/api/inspections', json=start_b, headers=hb), 409)
                    stages.append('sessao_unica_e_inicio_idempotente=OK')
                    lease_a, lease_b = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
                    pair_a = {
                        'pairing_code': code_a,
                        'activation_id': str(uuid4()),
                        'lease_token': lease_a,
                    }
                    dh = {'Authorization': 'Bearer ' + credential}
                    paired = expect(
                        device.post('/api/device/inspections/pair', json=pair_a, headers=dh), 200
                    )
                    assert 'user_id' not in paired and 'lease_hash' not in paired
                    assert (
                        expect(
                            device.post('/api/device/inspections/pair', json=pair_a, headers=dh),
                            200,
                        )['id']
                        == first['id']
                    )
                    expect(
                        device.post(
                            '/api/device/inspections/pair',
                            json=pair_a,
                            headers={'Authorization': 'Bearer ' + other_credential},
                        ),
                        404,
                    )
                    stages.append('pareamento_idempotente_e_dispositivo_isolado=OK')
                    captured = db.execute('SELECT clock_timestamp() AS time').fetchone()['time']
                    item = {
                        'id': str(uuid4()),
                        'inspection_session_id': first['id'],
                        'timestamp': captured.isoformat(),
                        'classification': 'APROVADA',
                        'metrics': {
                            'orange_color_ratio': 0.8,
                            'abnormal_region_ratio': 0.02,
                            'circularity': 0.9,
                            'asymmetry': 0.03,
                            'visual_score': 85.0,
                        },
                        'calibration_version': 'sql-synthetic-only',
                        'algorithm_version': 'sql-verification',
                        'reason': 'Synthetic SQL integration only.',
                    }
                    lease_headers = {**dh, 'X-Inspection-Lease': lease_a}
                    assert (
                        expect(
                            device.post(
                                '/api/ingest/analyses',
                                json={'items': [item]},
                                headers=lease_headers,
                            ),
                            200,
                        )['items'][0]['status']
                        == 'accepted'
                    )
                    assert (
                        expect(
                            device.post(
                                '/api/ingest/analyses',
                                json={'items': [item]},
                                headers=lease_headers,
                            ),
                            200,
                        )['items'][0]['status']
                        == 'duplicate'
                    )
                    changed = {**item, 'reason': 'Different content, must not overwrite.'}
                    assert (
                        expect(
                            device.post(
                                '/api/ingest/analyses',
                                json={'items': [changed]},
                                headers=lease_headers,
                            ),
                            200,
                        )['items'][0]['status']
                        == 'conflict'
                    )
                    expect(b.get('/api/analyses/' + item['id']), 404)
                    assert expect(b.get('/api/metrics/summary'), 200)['total'] == 0
                    expect(a.post('/api/inspections/' + first['id'] + '/close', headers=ha), 200)
                    assert (
                        expect(
                            device.post(
                                '/api/device/inspections/' + first['id'] + '/closed',
                                headers=lease_headers,
                            ),
                            200,
                        )['state']
                        == 'closed'
                    )
                    second = expect(b.post('/api/inspections', json=start_b, headers=hb), 201)
                    expect(
                        device.post(
                            '/api/device/inspections/pair',
                            json={
                                'pairing_code': code_b,
                                'activation_id': str(uuid4()),
                                'lease_token': lease_b,
                            },
                            headers=dh,
                        ),
                        200,
                    )
                    captured_b = db.execute('SELECT clock_timestamp() AS time').fetchone()['time']
                    item_b = {
                        **item,
                        'id': str(uuid4()),
                        'inspection_session_id': second['id'],
                        'timestamp': captured_b.isoformat(),
                        'classification': 'REVISAR',
                    }
                    assert (
                        expect(
                            device.post(
                                '/api/ingest/analyses',
                                json={'items': [item_b]},
                                headers={**dh, 'X-Inspection-Lease': lease_b},
                            ),
                            200,
                        )['items'][0]['status']
                        == 'accepted'
                    )
                    expect(
                        device.post(
                            '/api/ingest/analyses',
                            json={'items': [item]},
                            headers={**dh, 'X-Inspection-Lease': lease_b},
                        ),
                        403,
                    )
                    assert (
                        expect(
                            device.post(
                                '/api/ingest/analyses',
                                json={'items': [item]},
                                headers=lease_headers,
                            ),
                            200,
                        )['items'][0]['status']
                        == 'duplicate'
                    )
                    assert expect(a.get('/api/metrics/summary'), 200)['approved'] == 1
                    assert expect(b.get('/api/metrics/summary'), 200)['review'] == 1
                    assert expect(a.get('/api/analyses'), 200)['total'] == 1
                    assert expect(b.get('/api/analyses'), 200)['total'] == 1
                    expect(a.get('/api/analyses/' + item_b['id']), 404)
                    stages.append('ingestao_deduplicacao_conflito_e_dono_original=OK')
                    now = datetime.now(UTC)
                    filters = Filters(start=now - timedelta(days=1), end=now + timedelta(days=1))
                    assert (
                        QueryService(AnalysisRepository(enabled)).comparison(user_a, filters)[
                            'current'
                        ]['approved']
                        == 1
                    )
                    assert (
                        QueryService(AnalysisRepository(enabled)).comparison(user_b, filters)[
                            'current'
                        ]['review']
                        == 1
                    )
                    assert (
                        QueryService(
                            AnalysisRepository(replace(settings, inspections_enabled=False))
                        ).summary(user_a, Filters())['total']
                        == 0
                    )
                    stages.append('historico_comparacao_e_desativacao_sem_vazamento=OK')
        assert db.execute(
            'SELECT to_regnamespace(%s) IS NULL AND to_regnamespace(%s) IS NULL AS removed',
            (public_name, web_name),
        ).fetchone()['removed']
    return stages + ['rollback_namespaces_e_dados_temporarios=OK']


def main():
    parser = argparse.ArgumentParser(
        description='Verificar SQL em namespaces temporários com rollback obrigatório, sem aplicar 002 nos schemas reais.'
    )
    parser.add_argument('--run', action='store_true')
    args = parser.parse_args()
    if not args.run:
        print(
            'Nenhuma execução. --run usa estruturas transitórias e rollback; requer ambiente/autoridade revisados.'
        )
        return
    try:
        for stage in verify(Settings.load()):
            print(stage)
    except Exception as exc:
        print(
            f'verificacao_sql_falhou; tipo={type(exc).__name__}; estruturas temporárias revertidas sem commit'
        )
        raise SystemExit(1) from None


if __name__ == '__main__':
    main()
