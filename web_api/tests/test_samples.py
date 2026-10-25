from datetime import UTC, datetime
from io import BytesIO
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from pydantic import ValidationError

from web_api.api.dependencies import current_session
from web_api.api.sample_routes import sample_service
from web_api.application.auth_service import digest
from web_api.application.errors import ApplicationError
from web_api.application.sample_service import SampleService
from web_api.infrastructure.sample_images import SampleImages
from web_api.main import create_app
from web_api.sample_contracts import SampleResult

from .test_web_api import SETTINGS

TOKEN = 'test-only-device-credential-000000000000'
OWNER, OTHER, DEVICE = UUID(int=1), UUID(int=2), UUID(int=3)
HEADERS = {
    'Origin': SETTINGS.origins[0],
    'X-CSRF-Token': 'test-csrf',
    'Content-Type': 'application/octet-stream',
}


def picture(width=80, height=60, mode='RGB', format='PNG'):
    output = BytesIO()
    Image.new(mode, (width, height), 128).save(output, format=format)
    return output.getvalue()


def metadata(identity, filename, width, height):
    now = datetime.now(UTC)
    return dict(
        id=identity,
        filename=filename,
        width=width,
        height=height,
        state='received',
        device_id=None,
        metrics=None,
        classification=None,
        reason=None,
        calibration_version=None,
        algorithm_version=None,
        image_url=f'/api/samples/{identity}/image',
        mask_url=None,
        created_at=now,
        updated_at=now,
        started_at=None,
        finished_at=None,
        claim_expires_at=None,
    )


class SampleStore:
    enabled = True

    def __init__(self):
        self.rows, self.writes = {}, []

    def ready(self):
        return self.enabled

    def authenticate_device(self, token_hash):
        return {'device_id': DEVICE} if token_hash == digest(TOKEN) else None

    def devices(self, owner):
        return [{'id': DEVICE, 'name': 'Equipamento de teste'}]

    def heartbeat(self, device, payload):
        assert device == DEVICE
        self.last_heartbeat = payload
        return {'last_seen_at': datetime.now(UTC)}

    def upload(self, owner, request, source_hash, name, image, width, height):
        self.writes.append((owner, request))
        for row in self.rows.values():
            if row['owner'] == owner and row['request'] == request:
                if row['hash'] != source_hash:
                    raise ApplicationError(409, 'Conflito de arquivo.')
                return row['public']
        identity = uuid4()
        self.rows[identity] = dict(
            owner=owner,
            request=request,
            hash=source_hash,
            image=image,
            public=metadata(identity, name, width, height),
        )
        return self.rows[identity]['public']

    def listing(self, owner, limit, offset):
        rows = [row['public'] for row in self.rows.values() if row['owner'] == owner]
        return {'items': rows[offset : offset + limit], 'total': len(rows)}

    def image(self, owner, identity, mask):
        row = self.rows.get(identity)
        if not row or row['owner'] != owner or mask:
            raise ApplicationError(404, 'Imagem indisponível.')
        return row['image']

    def queue(self, owner, identity, device):
        row = self.rows.get(identity)
        if not row or row['owner'] != owner:
            raise ApplicationError(404, 'Amostra indisponível.')
        if device != DEVICE:
            raise ApplicationError(403, 'Equipamento não autorizado.')
        row['public'].update(state='queued', device_id=device)
        return row['public']

    def claim(self, device, claim, lease_hash):
        return None


@pytest.fixture
def samples():
    store = SampleStore()
    app = create_app(SETTINGS)
    app.dependency_overrides[sample_service] = lambda: SampleService(store, SampleImages())
    app.dependency_overrides[current_session] = lambda: {
        'user': {'id': OWNER},
        'csrf_token': 'test-csrf',
    }
    with TestClient(app) as client:
        yield client, store, app


def upload(client, **kwargs):
    return client.post(
        '/api/samples',
        params={'request_id': str(uuid4()), 'filename': 'foto.png'},
        content=picture(),
        headers=HEADERS,
        **kwargs,
    )


def test_upload_requires_csrf_and_never_accepts_arbitrary_owner(samples):
    client, store, _ = samples
    response = client.post(
        '/api/samples',
        params={'request_id': str(uuid4()), 'filename': 'foto.png'},
        content=picture(),
        headers={'Origin': SETTINGS.origins[0], 'Content-Type': 'application/octet-stream'},
    )
    assert response.status_code == 403
    assert not store.writes
    response = upload(client)
    assert response.status_code == 201
    assert store.writes[0][0] == OWNER
    assert response.json()['state'] == 'received'
    assert response.json()['classification'] is None
    assert 'image_data' not in response.json()


def test_other_account_cannot_list_read_or_queue_image(samples):
    client, _, app = samples
    identity = upload(client).json()['id']
    assert client.get(f'/api/samples/{identity}/image').status_code == 200
    app.dependency_overrides[current_session] = lambda: {
        'user': {'id': OTHER},
        'csrf_token': 'test-csrf',
    }
    assert client.get('/api/samples').json()['total'] == 0
    assert client.get(f'/api/samples/{identity}/image').status_code == 404
    assert (
        client.post(
            f'/api/samples/{identity}/queue',
            json={'device_id': str(DEVICE)},
            headers={key: value for key, value in HEADERS.items() if key != 'Content-Type'},
        ).status_code
        == 404
    )


def test_device_credential_does_not_authorize_browser_image(samples):
    client, _, app = samples
    identity = upload(client).json()['id']
    del app.dependency_overrides[current_session]
    assert (
        client.get(
            f'/api/samples/{identity}/image', headers={'Authorization': f'Bearer {TOKEN}'}
        ).status_code
        == 401
    )
    assert (
        client.post(
            '/api/device/samples/claim', json={'claim_id': str(uuid4()), 'lease_token': 'x' * 40}
        ).status_code
        == 401
    )
    assert (
        client.post(
            '/api/device/samples/claim',
            json={'claim_id': str(uuid4()), 'lease_token': 'x' * 40},
            headers={'Authorization': f'Bearer {TOKEN}'},
        ).json()
        is None
    )


def test_not_activated_is_not_reported_as_empty_gallery(samples):
    client, store, _ = samples
    store.enabled = False
    assert client.get('/api/samples/config').json()['enabled'] is False
    assert client.get('/api/samples').status_code == 503


def test_heartbeat_requires_device_credential_not_browser_session(samples):
    client, store, _ = samples
    payload = {
        'state': 'ready',
        'model_version': 'test-detector',
        'message': 'Executor consultando fila.',
    }
    assert client.post('/api/device/samples/heartbeat', json=payload).status_code == 401
    response = client.post(
        '/api/device/samples/heartbeat', json=payload, headers={'Authorization': f'Bearer {TOKEN}'}
    )
    assert response.status_code == 200
    assert store.last_heartbeat['model_version'] == 'test-detector'
    assert 'lease' not in response.text


def test_camera_upload_does_not_accept_browser_cookie_as_equipment(samples):
    client, _, _ = samples
    response = client.post(
        '/api/device/samples/capture',
        params={
            'inspection_id': str(uuid4()),
            'request_id': str(uuid4()),
            'captured_at': datetime.now(UTC).isoformat(),
        },
        content=picture(),
        headers={**HEADERS, 'X-Inspection-Lease': 'x' * 40},
    )
    assert response.status_code == 401


def test_invalid_image_and_oversize_body_do_not_create_samples(samples):
    client, store, _ = samples
    params = {'request_id': str(uuid4()), 'filename': 'image.png'}
    assert (
        client.post(
            '/api/samples', params=params, headers=HEADERS, content=b'<svg>fake image</svg>'
        ).status_code
        == 422
    )
    assert (
        client.post(
            '/api/samples', params=params, headers=HEADERS, content=b'x' * (5242880 + 1)
        ).status_code
        == 413
    )
    assert not store.writes


def test_upload_retry_keeps_one_sample_and_sanitizes_filename(samples):
    client, store, _ = samples
    params = {'request_id': str(uuid4()), 'filename': 'C:\\folder\\foto.png'}
    first = client.post('/api/samples', params=params, content=picture(), headers=HEADERS)
    again = client.post('/api/samples', params=params, content=picture(), headers=HEADERS)
    assert first.json()['id'] == again.json()['id']
    assert first.json()['filename'] == 'foto.png'
    assert len(store.rows) == 1
    assert (
        client.post('/api/samples', params=params, content=picture(81), headers=HEADERS).status_code
        == 409
    )


def test_normalization_strips_exif_and_bounds_resolution():
    output = BytesIO()
    image = Image.new('RGB', (2000, 1000), 'orange')
    exif = Image.Exif()
    exif[274] = 6
    image.save(output, format='JPEG', exif=exif)
    content, width, height = SampleImages().normalize(output.getvalue())
    assert (width, height) == (800, 1600)
    with Image.open(BytesIO(content)) as normalized:
        assert normalized.format == 'JPEG'
        assert not normalized.getexif()


def test_mask_requires_binary_pixels_and_same_dimensions():
    codec = SampleImages()
    valid = BytesIO()
    Image.new('L', (80, 60), 0).save(valid, format='PNG')
    assert codec.mask(valid.getvalue(), 80, 60)
    for content, width, height in [
        (picture(mode='L'), 80, 60),
        (picture(), 80, 60),
        (picture(mode='L'), 10, 10),
    ]:
        with pytest.raises(ApplicationError):
            codec.mask(content, width, height)


@pytest.mark.parametrize(
    'payload',
    [
        {'state': 'completed', 'classification': 'APROVADA', 'reason': 'incomplete'},
        {'state': 'awaiting_review', 'classification': 'REVISAR', 'reason': 'not a category'},
        {'state': 'not_evaluable', 'reason': 'bad input', 'metrics': {'circularity': 0}},
        {
            'state': 'awaiting_review',
            'reason': 'nonfinite',
            'metrics': {'circularity': float('nan')},
        },
    ],
)
def test_result_cannot_invent_classification_or_metrics(payload):
    with pytest.raises(ValidationError):
        SampleResult(claim_id=uuid4(), **payload)
