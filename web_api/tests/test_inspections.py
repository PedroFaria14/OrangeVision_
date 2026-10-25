import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from web_api.api.dependencies import current_session
from web_api.api.inspection_routes import inspection_service
from web_api.application.auth_service import digest
from web_api.application.errors import ApplicationError
from web_api.application.inspection_service import (
    InspectionService,
    capture_within_authorization,
    pairing_action,
    payload_digest,
    receipt_status,
)
from web_api.contracts import Filters
from web_api.infrastructure.analysis_repository import scope
from web_api.infrastructure.inspection_repository import public_inspection
from web_api.inspection_contracts import IngestAnalysis
from web_api.main import create_app

from .test_web_api import SETTINGS


def inspection_row(state='pending'):
    return {
        'id': UUID(int=10),
        'user_id': UUID(int=1),
        'device_id': UUID(int=2),
        'operator_name': 'Pessoa A',
        'state': state,
        'created_at': datetime.now(UTC),
        'pairing_expires_at': datetime.now(UTC) + timedelta(minutes=5),
        'started_at': None,
        'authorization_expires_at': None,
        'closed_at': None,
        'pairing_hash': 'must-not-leak',
        'lease_hash': 'must-not-leak',
    }


class InspectionStore:
    def __init__(self):
        self.calls = []

    def authenticate_device(self, token_hash):
        return (
            {'device_id': UUID(int=2)}
            if token_hash == digest('test-only-device-credential-000000000000')
            else None
        )

    def start(self, user, device, request, code_hash):
        self.calls.append((user, device, request, code_hash))
        return public_inspection(inspection_row())

    def pair(self, device, code_hash, activation, lease_hash, seconds):
        self.calls.append((device, code_hash, activation, lease_hash))
        return {
            **public_inspection(inspection_row()),
            'state': 'active',
            'started_at': datetime.now(UTC),
            'authorization_expires_at': datetime.now(UTC) + timedelta(seconds=seconds),
        }

    def ingest(self, device, lease_hash, items):
        self.calls.append((device, lease_hash, items))
        return [{'id': item[0]['id'], 'status': 'accepted'} for item in items]


@pytest.fixture
def context():
    store = InspectionStore()
    service = InspectionService(store)
    app = create_app(replace(SETTINGS, inspections_enabled=True))
    app.dependency_overrides[inspection_service] = lambda: service
    app.dependency_overrides[current_session] = lambda: {
        'user': {'id': UUID(int=1)},
        'csrf_token': 'test-only-csrf',
    }
    with TestClient(app) as client:
        yield client, store


def test_start_requires_origin_and_csrf_and_uses_server_user(context):
    client, store = context
    body = {'device_id': str(UUID(int=2)), 'request_id': str(UUID(int=3)), 'pairing_code': 'c' * 32}
    assert client.post('/api/inspections', json=body).status_code == 403
    response = client.post(
        '/api/inspections',
        json=body,
        headers={'Origin': SETTINGS.origins[0], 'X-CSRF-Token': 'test-only-csrf'},
    )
    assert response.status_code == 201
    assert store.calls[0][0] == UUID(int=1)
    assert store.calls[0][-1] == digest('c' * 32)
    assert 'pairing_hash' not in response.text and 'lease_hash' not in response.text
    assert (
        client.post('/api/inspections', json={**body, 'user_id': str(UUID(int=99))}).status_code
        == 422
    )


def test_device_credentials_and_user_sessions_are_separate(context):
    client, store = context
    body = {'pairing_code': 'c' * 32, 'activation_id': str(UUID(int=4)), 'lease_token': 's' * 32}
    assert client.post('/api/device/inspections/pair', json=body).status_code == 401
    response = client.post(
        '/api/device/inspections/pair',
        json=body,
        headers={'Authorization': 'Bearer test-only-device-credential-000000000000'},
    )
    assert response.status_code == 200
    assert 'user_id' not in response.json() and 'lease_token' not in response.json()
    assert store.calls[-1][-1] == digest('s' * 32)


def test_device_token_does_not_authenticate_browser_routes():
    with TestClient(create_app(SETTINGS)) as client:
        assert (
            client.get(
                '/api/auth/session',
                headers={'Authorization': 'Bearer test-only-device-credential-000000000000'},
            ).status_code
            == 401
        )


def test_ingest_rejects_arbitrary_user_device_and_nonfinite_metrics(context):
    client, _ = context
    headers = {
        'Authorization': 'Bearer test-only-device-credential-000000000000',
        'X-Inspection-Lease': 's' * 32,
    }
    item = {
        'id': str(UUID(int=20)),
        'inspection_session_id': str(UUID(int=10)),
        'timestamp': '2026-10-20T12:00:00Z',
        'classification': 'APROVADA',
        'metrics': {
            'orange_color_ratio': 0.8,
            'abnormal_region_ratio': 0.02,
            'circularity': 0.9,
            'asymmetry': 0.03,
            'visual_score': 90,
        },
        'calibration_version': 'test-only',
        'algorithm_version': 'test-only',
        'reason': 'Synthetic only.',
    }
    assert (
        client.post('/api/ingest/analyses', json={'items': [item]}, headers=headers).status_code
        == 200
    )
    assert (
        client.post(
            '/api/ingest/analyses',
            json={'items': [{**item, 'user_id': str(UUID(int=99))}]},
            headers=headers,
        ).status_code
        == 422
    )
    assert (
        client.post(
            '/api/ingest/analyses',
            json={'items': [{**item, 'device_id': str(UUID(int=99))}]},
            headers=headers,
        ).status_code
        == 422
    )
    assert (
        client.post(
            '/api/ingest/analyses', json={'items': [item] * 51}, headers=headers
        ).status_code
        == 422
    )
    assert (
        client.post(
            '/api/ingest/analyses',
            json={'items': [item, {**item, 'inspection_session_id': str(UUID(int=11))}]},
            headers=headers,
        ).status_code
        == 422
    )
    bad = {**item, 'metrics': {**item['metrics'], 'visual_score': float('nan')}}
    assert (
        client.post(
            '/api/ingest/analyses',
            content=json.dumps({'items': [bad]}),
            headers={**headers, 'Content-Type': 'application/json'},
        ).status_code
        == 422
    )


def test_body_limit_applies_before_json_parse(context):
    client, _ = context
    assert client.post('/api/ingest/analyses', content=b'x' * 262145).status_code == 413


def test_owned_records_never_fall_back_to_shared_legacy_device_access():
    filters = Filters()
    legacy, legacy_params = scope(UUID(int=1), filters)
    owned, owned_params = scope(UUID(int=1), filters, inspection_owner_only=True)
    assert "to_jsonb(a)->>'inspection_session_id'" in legacy
    assert 'device_access' in legacy
    assert 'owned.user_id=%s' in owned and 'owned.id=a.inspection_session_id' in owned
    assert 'device_access' not in owned
    assert legacy_params == owned_params == [UUID(int=1)]


def test_public_state_expires_without_leaking_or_mutating_stored_secrets():
    row = inspection_row()
    row['pairing_expires_at'] = datetime.now(UTC) - timedelta(seconds=1)
    result = public_inspection(row)
    assert result['state'] == 'expired'
    assert row['state'] == 'pending'
    assert 'pairing_hash' not in result and 'lease_hash' not in result


def test_device_auth_failure_is_generic_without_store_lookup_for_missing_secret():
    with pytest.raises(ApplicationError) as result:
        InspectionService(None).authenticate_device(None)
    assert result.value.status_code == 401


def test_pairing_retries_do_not_reactivate_or_reassign_the_original_operator():
    now = datetime.now(UTC)
    row = {**inspection_row('active'), 'activation_id': UUID(int=5), 'lease_hash': digest('s' * 32)}
    assert pairing_action(row, UUID(int=2), UUID(int=5), digest('s' * 32), now) == 'retry'
    assert row['user_id'] == UUID(int=1)
    for device, activation, token in [
        (UUID(int=99), UUID(int=5), digest('s' * 32)),
        (UUID(int=2), UUID(int=6), digest('s' * 32)),
        (UUID(int=2), UUID(int=5), digest('x' * 32)),
    ]:
        with pytest.raises(ApplicationError):
            pairing_action(row, device, activation, token, now)


def test_late_upload_keeps_its_capture_window_and_rejects_new_work_after_closure():
    now = datetime.now(UTC)
    row = {
        **inspection_row('closed'),
        'started_at': now - timedelta(hours=1),
        'authorization_expires_at': now + timedelta(hours=1),
        'closed_at': now - timedelta(minutes=1),
    }
    assert capture_within_authorization(now - timedelta(minutes=2), row, now + timedelta(days=3))
    assert not capture_within_authorization(now, row, now)
    assert not capture_within_authorization(row['started_at'] - timedelta(seconds=31), row, now)
    assert not capture_within_authorization(row['authorization_expires_at'], row, now)


def test_duplicate_receipt_requires_same_session_and_same_content():
    receipt = {'inspection_session_id': UUID(int=10), 'payload_hash': 'test-only-hash'}
    assert receipt_status(receipt, UUID(int=10), 'test-only-hash') == 'duplicate'
    assert receipt_status(receipt, UUID(int=11), 'test-only-hash') == 'conflict'
    assert receipt_status(receipt, UUID(int=10), 'modified') == 'conflict'
    assert receipt_status(None, UUID(int=10), 'test-only-hash') == 'conflict'
    assert payload_digest({'a': 1, 'b': 2}) == payload_digest({'b': 2, 'a': 1})


def test_ingestion_digest_normalizes_timestamp_offsets_without_changing_owner():
    store = InspectionStore()
    service = InspectionService(store)
    payload = {
        'id': str(UUID(int=20)),
        'inspection_session_id': str(UUID(int=10)),
        'timestamp': '2026-10-20T12:00:00Z',
        'classification': 'APROVADA',
        'metrics': {
            'orange_color_ratio': 0.8,
            'abnormal_region_ratio': 0.02,
            'circularity': 0.9,
            'asymmetry': 0.03,
            'visual_score': 90,
        },
        'calibration_version': 'test-only',
        'algorithm_version': 'test-only',
        'reason': 'Synthetic fixture only.',
    }
    first = IngestAnalysis.model_validate(payload)
    second = IngestAnalysis.model_validate({**payload, 'timestamp': '2026-10-20T09:00:00-03:00'})
    service.ingest(UUID(int=2), 's' * 32, [first])
    one = store.calls[-1][-1][0]
    service.ingest(UUID(int=2), 's' * 32, [second])
    two = store.calls[-1][-1][0]
    assert one == two
    assert one[0]['inspection_session_id'] == str(UUID(int=10))


def test_pairing_and_public_expiry_use_database_observation_not_a_skewed_api_host():
    local_now = datetime.now(UTC)
    database_now = local_now - timedelta(minutes=10)
    row = {
        **inspection_row(),
        'activation_id': None,
        'lease_hash': None,
        'observed_at': database_now,
        'pairing_expires_at': database_now + timedelta(minutes=5),
    }
    assert public_inspection(row)['state'] == 'pending'
    assert public_inspection(row)['observed_at'] == database_now
    assert (
        pairing_action(row, UUID(int=2), UUID(int=5), digest('s' * 32), database_now) == 'activate'
    )
