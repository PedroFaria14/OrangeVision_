"""Ensaio HTTP/SQL em schemas aleatórios, em transação única com rollback.

Nenhuma tabela de operação é alterada. Não mede concorrência entre conexões.
"""

import argparse
import base64
import secrets
from contextlib import contextmanager
from io import BytesIO
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

import psycopg
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw
from psycopg import sql
from psycopg.rows import dict_row

from .api.dependencies import current_session
from .application.auth_service import digest
from .config import Settings
from .infrastructure import sample_repository
from .main import create_app


def verify(settings):
    marker = 'ov_samples_' + uuid4().hex
    public, web = marker + '_p', marker + '_w'
    stages = []
    fail_commit = False
    with psycopg.connect(
        settings.database_url, autocommit=True, connect_timeout=5, row_factory=dict_row
    ) as db:

        class Proxy:
            wrote = False

            def execute(self, statement, params=None, **kwargs):
                if statement.startswith('SET TRANSACTION'):
                    return db.execute('SELECT 1')
                if statement.lstrip().startswith(('INSERT', 'UPDATE')):
                    self.wrote = True
                return db.execute(
                    statement.replace('orangevision_web', web).replace('public.', public + '.'),
                    params,
                    **kwargs,
                )

        @contextmanager
        def scoped_connection(_settings):
            with db.transaction():
                proxy = Proxy()
                yield proxy
                if fail_commit and proxy.wrote:
                    raise RuntimeError('synthetic failure before commit')

        with db.transaction(force_rollback=True):
            db.execute("SET LOCAL statement_timeout = '30s'")
            db.execute("SET LOCAL lock_timeout = '5s'")
            for name in (public, web):
                db.execute(sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(name)))
            for table in ('dispositivos', 'analises'):
                db.execute(
                    sql.SQL('CREATE TABLE {}.{} (LIKE public.{} INCLUDING ALL)').format(
                        sql.Identifier(public), sql.Identifier(table), sql.Identifier(table)
                    )
                )
            db.execute(sql.SQL('SET LOCAL search_path TO {}').format(sql.Identifier(public)))
            proxy = Proxy()
            for filename in (
                '001_web_auth.sql',
                '002_inspection_sessions.sql',
                '003_image_samples.sql',
                '004_sample_executor_detection.sql',
                '005_sample_review_authorization.sql',
            ):
                body = (Path(__file__).parent / 'migrations' / filename).read_text(encoding='utf-8')
                body = '\n'.join(
                    line for line in body.splitlines() if line.strip() not in ('BEGIN;', 'COMMIT;')
                )
                proxy.execute(body, prepare=False)
            owner, other, device, other_device = (uuid4() for _ in range(4))
            for identity in (owner, other):
                proxy.execute(
                    'INSERT INTO orangevision_web.users(id,name,email,password_hash) VALUES (%s,%s,%s,%s)',
                    (
                        identity,
                        'SQL synthetic sample user',
                        str(identity) + '@example.com',
                        'test-only-not-a-login',
                    ),
                )
            tokens = [secrets.token_urlsafe(32), secrets.token_urlsafe(32)]
            for identity, token in zip((device, other_device), tokens, strict=True):
                proxy.execute(
                    "INSERT INTO public.dispositivos(id,nome,status,criado_em) VALUES (%s,'SQL synthetic sample device','offline',now())",
                    (identity,),
                )
                proxy.execute(
                    'INSERT INTO orangevision_web.device_credentials(id,device_id,token_hash) VALUES (%s,%s,%s)',
                    (uuid4(), identity, digest(token)),
                )
            proxy.execute(
                'INSERT INTO orangevision_web.device_access(user_id,device_id) VALUES (%s,%s)',
                (owner, device),
            )
            active_owner = owner
            csrf = secrets.token_urlsafe(32)
            app = create_app(settings)
            app.dependency_overrides[current_session] = lambda: {
                'user': {'id': active_owner},
                'csrf_token': csrf,
            }
            origin = {'Origin': settings.origins[0], 'X-CSRF-Token': csrf}
            auth = {'Authorization': 'Bearer ' + tokens[0]}

            def expect(response, status):
                if response.status_code != status:
                    raise RuntimeError(
                        f'Ensaio HTTP/SQL falhou: esperado {status}, recebido {response.status_code}.'
                    )
                return (
                    response.json()
                    if response.headers.get('content-type', '').startswith('application/json')
                    else response.content
                )

            content = BytesIO()
            Image.new('RGB', (120, 80), 'orange').save(content, format='PNG')
            request_id = uuid4()
            params = {'request_id': str(request_id), 'filename': 'SQL-synthetic-sample.png'}
            with (
                patch.object(sample_repository, 'connection', scoped_connection),
                TestClient(app) as client,
            ):
                assert expect(client.get('/api/samples/config'), 200)['enabled']
                expect(
                    client.post(
                        '/api/device/samples/heartbeat',
                        json={'state': 'ready', 'model_version': 'synthetic-test-model'},
                        headers=auth,
                    ),
                    200,
                )
                executor = expect(client.get('/api/samples/executors'), 200)[0]
                assert (
                    executor['executor_recent']
                    and executor['model_version'] == 'synthetic-test-model'
                )
                stages.append('contato_do_executor_autorizado=OK')
                expect(
                    client.post(
                        '/api/device/samples/heartbeat',
                        json={'state': 'error', 'message': 'Synthetic model error'},
                        headers=auth,
                    ),
                    200,
                )
                errored = expect(client.get('/api/samples/executors'), 200)[0]
                assert errored['executor_recent'] and errored['executor_state'] == 'error'
                expect(
                    client.post(
                        '/api/device/samples/heartbeat',
                        json={'state': 'ready', 'model_version': 'synthetic-test-model'},
                        headers=auth,
                    ),
                    200,
                )
                uploaded = expect(
                    client.post(
                        '/api/samples',
                        params=params,
                        content=content.getvalue(),
                        headers={**origin, 'Content-Type': 'application/octet-stream'},
                    ),
                    201,
                )
                identity = uploaded['id']
                assert (
                    expect(
                        client.post(
                            '/api/samples',
                            params=params,
                            content=content.getvalue(),
                            headers={**origin, 'Content-Type': 'application/octet-stream'},
                        ),
                        201,
                    )['id']
                    == identity
                )
                assert expect(client.get('/api/samples'), 200)['total'] == 1
                expect(client.get(f'/api/samples/{identity}/image'), 200)
                active_owner = other
                assert expect(client.get('/api/samples'), 200)['total'] == 0
                expect(client.get(f'/api/samples/{identity}/image'), 404)
                expect(
                    client.post(
                        f'/api/samples/{identity}/queue',
                        json={'device_id': str(device)},
                        headers=origin,
                    ),
                    404,
                )
                active_owner = owner
                stages.append('upload_idempotente_e_isolamento_entre_contas=OK')
                expect(
                    client.post(
                        f'/api/samples/{identity}/queue',
                        json={'device_id': str(other_device)},
                        headers=origin,
                    ),
                    403,
                )
                expect(
                    client.post(
                        f'/api/samples/{identity}/queue',
                        json={'device_id': str(device)},
                        headers=origin,
                    ),
                    200,
                )
                attempt = {'claim_id': str(uuid4()), 'lease_token': secrets.token_urlsafe(32)}
                assert (
                    expect(
                        client.post('/api/device/samples/claim', json=attempt, headers=auth), 200
                    )['id']
                    == identity
                )
                assert (
                    expect(
                        client.post('/api/device/samples/claim', json=attempt, headers=auth), 200
                    )['id']
                    == identity
                )
                leased = {**auth, 'X-Sample-Lease': attempt['lease_token']}
                expect(client.get(f'/api/device/samples/{identity}/image', headers=leased), 200)
                expect(
                    client.post(
                        f'/api/samples/{identity}/queue',
                        json={'device_id': str(device)},
                        headers=origin,
                    ),
                    409,
                )
                mask = Image.new('L', (120, 80), 0)
                ImageDraw.Draw(mask).ellipse((20, 10, 100, 70), fill=255)
                binary = BytesIO()
                mask.save(binary, format='PNG')
                result = {
                    'claim_id': attempt['claim_id'],
                    'state': 'awaiting_review',
                    'reason': 'Synthetic SQL test; not a fruit quality measurement.',
                    'metrics': {'circularity': 0.8},
                    'mask_base64': base64.b64encode(binary.getvalue()).decode(),
                    'detection': {
                        'status': 'detected',
                        'label': 'orange',
                        'score': 0.8,
                        'box': [20, 10, 80, 60],
                        'count': 1,
                        'model': 'synthetic-test-only',
                        'inference_ms': 1,
                    },
                }
                finished = expect(
                    client.post(
                        f'/api/device/samples/{identity}/result', json=result, headers=leased
                    ),
                    200,
                )
                assert finished['classification'] is None and finished['state'] == 'awaiting_review'
                assert finished['detection']['model'] == 'synthetic-test-only'
                expect(client.get(f'/api/samples/{identity}/mask'), 200)
                expect(
                    client.post(
                        f'/api/device/samples/{identity}/result', json=result, headers=leased
                    ),
                    200,
                )
                expect(
                    client.post(
                        f'/api/device/samples/{identity}/result',
                        json={**result, 'reason': 'Different result'},
                        headers=leased,
                    ),
                    409,
                )
                stages.append('reserva_download_mascara_e_resultado_idempotente=OK')
                expect(
                    client.post(
                        f'/api/samples/{identity}/queue',
                        json={'device_id': str(device)},
                        headers=origin,
                    ),
                    200,
                )
                expect(
                    client.post(
                        f'/api/device/samples/{identity}/result', json=result, headers=leased
                    ),
                    404,
                )
                attempt2 = {'claim_id': str(uuid4()), 'lease_token': secrets.token_urlsafe(32)}
                expect(client.post('/api/device/samples/claim', json=attempt2, headers=auth), 200)
                proxy.execute(
                    "UPDATE orangevision_web.image_samples SET claim_expires_at=clock_timestamp()-interval '1 second' WHERE id=%s",
                    (identity,),
                )
                expect(
                    client.post(
                        f'/api/device/samples/{identity}/result',
                        json={**result, 'claim_id': attempt2['claim_id']},
                        headers={**auth, 'X-Sample-Lease': attempt2['lease_token']},
                    ),
                    409,
                )
                assert (
                    expect(
                        client.post(
                            '/api/device/samples/claim',
                            json={
                                'claim_id': str(uuid4()),
                                'lease_token': secrets.token_urlsafe(32),
                            },
                            headers=auth,
                        ),
                        200,
                    )['id']
                    == identity
                )
                stages.append('reserva_vencida_retomada_e_resultado_obsoleto_bloqueado=OK')
                fail_commit = True
                expect(
                    client.post(
                        '/api/samples',
                        params={**params, 'request_id': str(uuid4())},
                        content=content.getvalue(),
                        headers={**origin, 'Content-Type': 'application/octet-stream'},
                    ),
                    500,
                )
                fail_commit = False
                assert expect(client.get('/api/samples'), 200)['total'] == 1
                stages.append('rollback_antes_do_commit=OK')
                inspection_id = uuid4()
                lease = secrets.token_urlsafe(32)
                proxy.execute(
                    "INSERT INTO orangevision_web.inspection_sessions(id,user_id,device_id,request_id,state,pairing_hash,pairing_expires_at,activation_id,lease_hash,started_at,authorization_expires_at) VALUES (%s,%s,%s,%s,'active',%s,now()+interval '5 minutes',%s,%s,now()-interval '1 minute',now()+interval '1 hour')",
                    (inspection_id, owner, device, uuid4(), uuid4().hex, uuid4(), digest(lease)),
                )
                stamp = (
                    proxy.execute('SELECT clock_timestamp() AS now').fetchone()['now'].isoformat()
                )
                capture_params = {
                    'inspection_id': str(inspection_id),
                    'request_id': str(uuid4()),
                    'captured_at': stamp,
                }
                capture_headers = {
                    **auth,
                    'X-Inspection-Lease': lease,
                    'Content-Type': 'application/octet-stream',
                }
                active_owner = other
                capture = expect(
                    client.post(
                        '/api/device/samples/capture',
                        params=capture_params,
                        content=content.getvalue(),
                        headers=capture_headers,
                    ),
                    201,
                )
                assert capture['state'] == 'queued' and capture['source_inspection_id'] == str(
                    inspection_id
                )
                assert (
                    expect(
                        client.post(
                            '/api/device/samples/capture',
                            params=capture_params,
                            content=content.getvalue(),
                            headers=capture_headers,
                        ),
                        201,
                    )['id']
                    == capture['id']
                )
                assert expect(client.get('/api/samples'), 200)['total'] == 0
                expect(client.get(f'/api/samples/{capture["id"]}/image'), 404)
                active_owner = owner
                assert expect(client.get('/api/samples'), 200)['total'] == 2
                expect(
                    client.post(
                        '/api/device/samples/capture',
                        params={**capture_params, 'request_id': str(uuid4())},
                        content=content.getvalue(),
                        headers={**capture_headers, 'X-Inspection-Lease': 'x' * 40},
                    ),
                    403,
                )
                stages.append('captura_da_camera_congela_dono_e_idempotencia=OK')
                proxy.execute(
                    "UPDATE orangevision_web.inspection_sessions SET state='expired',started_at=clock_timestamp()-interval '2 hours',authorization_expires_at=clock_timestamp()-interval '1 hour' WHERE id=%s",
                    (inspection_id,),
                )
                review_id = uuid4()
                review_lease = secrets.token_urlsafe(32)
                proxy.execute(
                    "INSERT INTO orangevision_web.inspection_sessions(id,user_id,device_id,request_id,state,pairing_hash,pairing_expires_at,activation_id,lease_hash,started_at,authorization_expires_at) VALUES (%s,%s,%s,%s,'active',%s,now()+interval '5 minutes',%s,%s,clock_timestamp()-interval '1 second',clock_timestamp()+interval '1 hour')",
                    (review_id, owner, device, uuid4(), uuid4().hex, uuid4(), digest(review_lease)),
                )
                recovery_headers = {
                    **auth,
                    'X-Inspection-Lease': review_lease,
                    'X-Original-Inspection-Lease': lease,
                }
                recovery_body = {
                    'original_inspection_id': str(inspection_id),
                    'review_inspection_id': str(review_id),
                }
                expect(
                    client.post(
                        '/api/device/samples/authorize-review',
                        json=recovery_body,
                        headers=recovery_headers,
                    ),
                    200,
                )
                recovery_params = {
                    'original_inspection_id': str(inspection_id),
                    'review_inspection_id': str(review_id),
                    'request_id': str(uuid4()),
                    'captured_at': stamp,
                }
                recovered = expect(
                    client.post(
                        '/api/device/samples/review-capture',
                        params=recovery_params,
                        content=content.getvalue(),
                        headers={**recovery_headers, 'Content-Type': 'application/octet-stream'},
                    ),
                    201,
                )
                assert recovered['review_authorization_id'] == str(review_id)
                assert recovered['source_inspection_id'] == str(inspection_id)
                assert (
                    expect(
                        client.post(
                            '/api/device/samples/review-capture',
                            params=recovery_params,
                            content=content.getvalue(),
                            headers={
                                **recovery_headers,
                                'Content-Type': 'application/octet-stream',
                            },
                        ),
                        201,
                    )['id']
                    == recovered['id']
                )
                proxy.execute(
                    "UPDATE orangevision_web.inspection_sessions SET state='closed',closed_at=clock_timestamp() WHERE id=%s",
                    (review_id,),
                )
                other_review = uuid4()
                other_lease = secrets.token_urlsafe(32)
                proxy.execute(
                    'INSERT INTO orangevision_web.device_access(user_id,device_id) VALUES (%s,%s)',
                    (other, device),
                )
                proxy.execute(
                    "INSERT INTO orangevision_web.inspection_sessions(id,user_id,device_id,request_id,state,pairing_hash,pairing_expires_at,activation_id,lease_hash,started_at,authorization_expires_at) VALUES (%s,%s,%s,%s,'active',%s,now()+interval '5 minutes',%s,%s,clock_timestamp()-interval '1 second',clock_timestamp()+interval '1 hour')",
                    (
                        other_review,
                        other,
                        device,
                        uuid4(),
                        uuid4().hex,
                        uuid4(),
                        digest(other_lease),
                    ),
                )
                other_headers = {**recovery_headers, 'X-Inspection-Lease': other_lease}
                expect(
                    client.post(
                        '/api/device/samples/authorize-review',
                        json={**recovery_body, 'review_inspection_id': str(other_review)},
                        headers=other_headers,
                    ),
                    403,
                )
                expect(
                    client.post(
                        '/api/device/samples/review-capture',
                        params={
                            **recovery_params,
                            'review_inspection_id': str(other_review),
                            'request_id': str(uuid4()),
                        },
                        content=content.getvalue(),
                        headers={**other_headers, 'Content-Type': 'application/octet-stream'},
                    ),
                    403,
                )
                active_owner = other
                assert expect(client.get('/api/samples'), 200)['total'] == 0
                stages.append('recuperacao_explicita_preserva_dono_e_recusa_troca_de_conta=OK')
                unassigned_params = {
                    'review_inspection_id': str(other_review),
                    'request_id': str(uuid4()),
                    'captured_at': stamp,
                }
                unassigned = expect(
                    client.post(
                        '/api/device/samples/review-capture',
                        params=unassigned_params,
                        content=content.getvalue(),
                        headers={
                            **auth,
                            'X-Inspection-Lease': other_lease,
                            'Content-Type': 'application/octet-stream',
                        },
                    ),
                    201,
                )
                assert unassigned['source_inspection_id'] is None and unassigned[
                    'review_authorization_id'
                ] == str(other_review)
                assert expect(client.get('/api/samples'), 200)['total'] == 1
                expect(client.get(f'/api/samples/{recovered["id"]}/image'), 404)
                stages.append(
                    'foto_sem_sessao_exige_autorizacao_atual_e_fica_identificada_como_amostra=OK'
                )
        # A transação force_rollback remove todos os schemas/fixtures deste ensaio.
        assert db.execute('SELECT to_regnamespace(%s) IS NULL AS absent', (web,)).fetchone()[
            'absent'
        ]
        stages.append('schemas_transitorios_removidos_por_rollback=OK')
    return stages


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', action='store_true')
    if not parser.parse_args().run:
        print(
            'Plano: ensaio HTTP/SQL em schemas transitórios com rollback. Use --run após autorização.'
        )
        return
    for stage in verify(Settings.load()):
        print(stage)


if __name__ == '__main__':
    main()
