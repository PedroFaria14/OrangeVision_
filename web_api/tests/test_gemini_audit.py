"""Auditoria das tentativas Gemini: log estruturado e detalhe persistido, sem segredos."""
import json
import logging
from uuid import uuid4

from web_api.evaluation_contracts import VisualAssessment
from web_api.infrastructure.gemini_jobs import process_once
from web_api.infrastructure.gemini_provider import ProviderFailure
from web_api.observability import JsonFormatter

JOB = {'id': uuid4(), 'sample_id': uuid4(), 'attempts': 2, 'model_version': 'gemini-3.5-flash-lite',
       'criteria_version': 'orange-surface-v1', 'image': b'private-image-bytes'}


class Jobs:
    def __init__(self):
        self.finished = []

    def claim(self):
        return dict(JOB)

    def finish(self, job, assessment=None, usage=None, failure=None):
        self.finished.append({'assessment': assessment, 'usage': usage, 'failure': failure})
        return True


class Provider:
    def __init__(self, result=None, failure=None):
        self.result, self.failure = result, failure

    def assess(self, image, model):
        if self.failure:
            raise self.failure
        return self.result, {'total_tokens': 40, 'duration_ms': 1200, 'http_status': 200}


def records(caplog):
    return [json.loads(JsonFormatter().format(r)) for r in caplog.records if r.getMessage() == 'gemini_attempt']


def test_failure_detail_is_persisted_and_logged(caplog):
    caplog.set_level(logging.INFO, logger='orangevision.web')
    jobs = Jobs()
    failure = ProviderFailure('provider_unavailable', True, detail={
        'http_status': 503, 'provider_status': 'UNAVAILABLE', 'duration_ms': 3100,
    })
    assert process_once(jobs, Provider(failure=failure)) == 'provider_unavailable'
    assert jobs.finished[0]['usage'] == failure.detail
    [line] = records(caplog)
    assert line['outcome'] == 'provider_unavailable' and line['http_status'] == 503
    assert line['provider_status'] == 'UNAVAILABLE' and line['duration_ms'] == 3100
    assert line['job_id'] == str(JOB['id']) and line['attempt'] == 2
    assert line['model'] == 'gemini-3.5-flash-lite'
    assert 'private-image-bytes' not in json.dumps(line)


def test_success_logs_category_and_duration(caplog):
    caplog.set_level(logging.INFO, logger='orangevision.web')
    result = VisualAssessment(evaluable=True, classification='APROVADA', reason='Casca uniforme.')
    assert process_once(Jobs(), Provider(result=result)) == 'completed'
    [line] = records(caplog)
    assert line['outcome'] == 'completed' and line['classification'] == 'APROVADA'
    assert line['duration_ms'] == 1200 and 'reason' not in line


def test_formatter_only_emits_allowlisted_fields():
    record = logging.LogRecord('orangevision.web', logging.INFO, __file__, 1, 'evento', None, None)
    record.http_status, record.api_key, record.cookie = 500, 'segredo', 'sessao'
    line = json.loads(JsonFormatter().format(record))
    assert line['http_status'] == 500 and 'api_key' not in line and 'cookie' not in line
