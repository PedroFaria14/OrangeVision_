from datetime import UTC, datetime
from email.utils import parsedate_to_datetime

import requests


class ApiFailure(Exception):
    def __init__(self, status, retry_after=None):
        super().__init__(f'API indisponível ou operação recusada (HTTP {status}).')
        self.status = status
        self.retry_after = retry_after


class Offline(Exception):
    pass


class DeviceApi:
    def __init__(self, settings):
        self.base = settings.api_url
        self.http = requests.Session()
        self.http.trust_env = False
        self.http.headers.update(
            {'Authorization': f'Bearer {settings.credential}', 'Accept': 'application/json'}
        )

    def close(self):
        self.http.close()

    def _request(
        self, method, path, *, lease=None, payload=None, timeout=(5, 30), extra_headers=None
    ):
        try:
            response = self.http.request(
                method,
                self.base + path,
                json=payload,
                headers={
                    **({'X-Inspection-Lease': lease} if lease else {}),
                    **(extra_headers or {}),
                },
                timeout=timeout,
                allow_redirects=False,
            )
        except (requests.ConnectionError, requests.Timeout) as exc:
            raise Offline('Sem comunicação com a API.') from exc
        if response.status_code not in (200, 201):
            retry_after = None
            header = response.headers.get('Retry-After')
            if header:
                try:
                    retry_after = (
                        max(0, float(header))
                        if header.isdigit()
                        else max(
                            0, (parsedate_to_datetime(header) - datetime.now(UTC)).total_seconds()
                        )
                    )
                except (ValueError, TypeError, OverflowError):
                    pass
            raise ApiFailure(response.status_code, retry_after)
        try:
            return response.json()
        except ValueError as exc:
            raise ApiFailure(502) from exc

    def pair(self, attempt):
        return self._request('POST', '/api/device/inspections/pair', payload=attempt)

    def status(self, grant):
        return self._request(
            'GET',
            f'/api/device/inspections/{grant["id"]}',
            lease=grant['lease_token'],
            timeout=(2, 3),
        )

    def closed(self, grant):
        return self._request(
            'POST', f'/api/device/inspections/{grant["id"]}/closed', lease=grant['lease_token']
        )

    def ingest(self, grant, items):
        return self._request(
            'POST',
            '/api/ingest/analyses',
            lease=grant['lease_token'],
            payload={'contract_version': '1', 'items': items},
        )

    def claim_sample(self, attempt):
        return self._request('POST', '/api/device/samples/claim', payload=attempt)

    def heartbeat_samples(self, state='ready', model_version=None, message=None):
        return self._request(
            'POST',
            '/api/device/samples/heartbeat',
            payload={'state': state, 'model_version': model_version, 'message': message},
        )

    def authorize_camera_review(self, original, review):
        return self._request(
            'POST',
            '/api/device/samples/authorize-review',
            payload={
                'original_inspection_id': original['id'] if original else None,
                'review_inspection_id': review['id'],
            },
            extra_headers={
                'X-Inspection-Lease': review['lease_token'],
                **({'X-Original-Inspection-Lease': original['lease_token']} if original else {}),
            },
        )

    def upload_camera_review(self, original, review, identity, captured_at, content):
        from urllib.parse import urlencode

        query = {
            'review_inspection_id': review['id'],
            'request_id': identity,
            'captured_at': captured_at,
        }
        if original:
            query['original_inspection_id'] = original['id']
        headers = {
            'Content-Type': 'application/octet-stream',
            'X-Inspection-Lease': review['lease_token'],
        }
        if original:
            headers['X-Original-Inspection-Lease'] = original['lease_token']
        try:
            response = self.http.post(
                self.base + '/api/device/samples/review-capture?' + urlencode(query),
                data=content,
                headers=headers,
                timeout=(5, 30),
                allow_redirects=False,
            )
        except (requests.ConnectionError, requests.Timeout) as exc:
            raise Offline('Sem comunicação com a API.') from exc
        if response.status_code not in (200, 201):
            raise ApiFailure(response.status_code)
        return response.json()

    def upload_camera_sample(self, grant, identity, captured_at, content):
        from urllib.parse import urlencode

        query = urlencode(
            {'inspection_id': grant['id'], 'request_id': identity, 'captured_at': captured_at}
        )
        try:
            response = self.http.post(
                self.base + '/api/device/samples/capture?' + query,
                data=content,
                headers={
                    'Content-Type': 'application/octet-stream',
                    'X-Inspection-Lease': grant['lease_token'],
                },
                timeout=(5, 30),
                allow_redirects=False,
            )
        except (requests.ConnectionError, requests.Timeout) as exc:
            raise Offline('Sem comunicação com a API.') from exc
        if response.status_code not in (200, 201):
            raise ApiFailure(response.status_code)
        return response.json()

    def sample_image(self, identity, lease):
        from uuid import UUID

        identity = str(UUID(identity))
        try:
            with self.http.get(
                self.base + f'/api/device/samples/{identity}/image',
                headers={'X-Sample-Lease': lease},
                stream=True,
                timeout=(5, 30),
                allow_redirects=False,
            ) as response:
                if response.status_code != 200:
                    raise ApiFailure(response.status_code)
                data = bytearray()
                for chunk in response.iter_content(65536):
                    data.extend(chunk)
                    if len(data) > 5242880:
                        raise ApiFailure(413)
                return bytes(data)
        except (requests.ConnectionError, requests.Timeout) as exc:
            raise Offline('Sem comunicação com a API.') from exc

    def finish_sample(self, identity, lease, payload):
        from uuid import UUID

        return self._request(
            'POST',
            f'/api/device/samples/{UUID(identity)}/result',
            payload=payload,
            extra_headers={'X-Sample-Lease': lease},
        )
