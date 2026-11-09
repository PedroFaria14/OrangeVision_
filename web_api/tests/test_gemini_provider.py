import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from email.utils import format_datetime
from urllib.error import HTTPError, URLError

import pytest

from web_api.infrastructure.gemini_provider import GeminiProvider, ProviderFailure, retry_delay

from .test_web_api import SETTINGS


class Response:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, limit):
        return json.dumps(self.payload).encode()[:limit]


def provider(payload=None, error=None):
    class Opener:
        def open(self, request, timeout):
            assert request.full_url == 'https://generativelanguage.googleapis.com/v1beta/interactions'
            assert timeout == 30
            body = json.loads(request.data)
            assert body['store'] is False and 'tools' not in body
            assert body['input'][1]['mime_type'] == 'image/jpeg'
            assert 'metrics' not in body['response_format']['schema']['properties']
            if error:
                raise error
            return Response(payload)
    return GeminiProvider(replace(SETTINGS, gemini_api_key='synthetic-never-log'), Opener())


def test_structured_assessment_and_usage_allowlist():
    result, usage = provider({'status': 'completed', 'outputs': [{'type': 'text', 'text': json.dumps({'evaluable': True, 'classification': 'ATENCAO', 'reason': 'Alterações visíveis.'})}], 'usage': {'total_tokens': 100, 'secret': 'ignore'}}).assess(b'fixture', 'gemini-3.8-flash')
    assert result.classification == 'ATENCAO'
    assert {key: usage[key] for key in ('total_tokens', 'http_status')} == {'total_tokens': 100, 'http_status': 200}
    assert 'secret' not in usage and type(usage['duration_ms']) is int


@pytest.mark.parametrize('text', ['not json', '{"evaluable":true,"classification":null,"reason":"x"}', '{"evaluable":true,"classification":"APROVADA","reason":"x","metrics":{}}'])
def test_invalid_or_invented_metrics_are_rejected(text):
    with pytest.raises(ProviderFailure) as error:
        provider({'status': 'completed', 'outputs': [{'type': 'text', 'text': text}]}).assess(b'fixture', 'model')
    assert error.value.code == 'response_invalid'


@pytest.mark.parametrize('status,code,retryable', [(400, 'provider_request_invalid', False), (401, 'provider_credentials', False), (403, 'provider_credentials', False), (404, 'model_unavailable', False), (412, 'provider_request_invalid', False), (429, 'provider_rate_limit', True), (503, 'provider_unavailable', True), (302, 'provider_unavailable', False)])
def test_controlled_errors_do_not_expose_secrets(status, code, retryable):
    with pytest.raises(ProviderFailure) as error:
        provider(error=HTTPError('https://provider', status, 'raw synthetic-never-log', {'Retry-After': '20'}, None)).assess(b'fixture', 'model')
    assert error.value.code == code and error.value.retryable is retryable
    assert 'synthetic-never-log' not in str(error.value)


def test_network_uncertainty_consumes_attempt_without_claiming_success():
    with pytest.raises(ProviderFailure) as error:
        provider(error=URLError('private-transport-details')).assess(b'fixture', 'model')
    assert error.value.code == 'network_uncertain' and error.value.retryable


def test_retry_after_accepts_http_dates_and_clamps_limits():
    now = datetime(2026, 11, 6, 12, tzinfo=UTC)
    assert retry_delay('20', now) == 20
    assert retry_delay(format_datetime(now + timedelta(seconds=45)), now) == 45
    assert retry_delay(format_datetime(now - timedelta(seconds=10)), now) == 0
    assert retry_delay('999999', now) == 86400
    assert retry_delay('invalid', now) == 0
    assert retry_delay(None, now) == 0


STEPS = {
    'status': 'completed', 'object': 'interaction', 'model': 'gemini-3.5-flash-lite',
    'steps': [
        {'type': 'thought', 'signature': 'opaque-signature'},
        {'type': 'model_output', 'content': [{'type': 'text', 'text': json.dumps(
            {'evaluable': False, 'classification': None, 'reason': 'Nenhuma laranja visível.'}
        )}]},
    ],
    'usage': {'total_input_tokens': 10, 'total_thought_tokens': 5, 'total_tokens': 30},
}


def test_current_steps_format_is_read_and_thoughts_are_ignored():
    result, usage = provider(STEPS).assess(b'fixture', 'gemini-3.5-flash-lite')
    assert result.evaluable is False and result.classification is None
    assert usage['total_thought_tokens'] == 5 and usage['http_status'] == 200


@pytest.mark.parametrize('payload,reason', [
    ({'status': 'completed', 'steps': [{'type': 'thought'}]}, 'no_text'),
    ({'status': 'incomplete', 'steps': []}, 'status_incomplete'),
    ({'status': 'completed', 'steps': [{'type': 'model_output', 'content': [{'type': 'text', 'text': '{}'}]}]}, 'schema'),
])
def test_invalid_response_records_reason_code_only(payload, reason):
    with pytest.raises(ProviderFailure) as error:
        provider(payload).assess(b'fixture', 'model')
    assert error.value.code == 'response_invalid'
    assert error.value.detail['reason'] == reason and error.value.detail['http_status'] == 200


def test_http_error_detail_keeps_google_enum_but_not_free_text():
    import io
    body = io.BytesIO(json.dumps({'error': {'status': 'RESOURCE_EXHAUSTED', 'message': 'synthetic-never-log'}}).encode())
    with pytest.raises(ProviderFailure) as error:
        provider(error=HTTPError('https://provider', 429, 'x', {}, body)).assess(b'fixture', 'model')
    assert error.value.detail['http_status'] == 429
    assert error.value.detail['provider_status'] == 'RESOURCE_EXHAUSTED'
    assert 'synthetic-never-log' not in json.dumps(error.value.detail)


def test_unsafe_provider_status_is_dropped():
    import io
    body = io.BytesIO(json.dumps({'error': {'status': 'chave sk-123 vazou'}}).encode())
    with pytest.raises(ProviderFailure) as error:
        provider(error=HTTPError('https://provider', 503, 'x', {}, body)).assess(b'fixture', 'model')
    assert error.value.detail['provider_status'] is None


def test_timeout_is_distinguished_from_network_error():
    with pytest.raises(ProviderFailure) as error:
        provider(error=TimeoutError()).assess(b'fixture', 'model')
    assert error.value.detail['reason'] == 'timeout'
