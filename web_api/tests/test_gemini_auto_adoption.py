"""Adoção automática da categoria Gemini: só casos extremos ficam para revisão humana."""
import logging
from dataclasses import replace
from uuid import uuid4

import pytest

from web_api.config import Settings
from web_api.evaluation_contracts import VisualAssessment
from web_api.infrastructure.evaluation_repository import AutoAdoption, auto_adoption
from web_api.infrastructure.gemini_jobs import process_once

GEMINI = {'state': 'completed', 'classification': 'REVISAR'}
LOCAL_SAME = {'state': 'completed', 'classification': 'REVISAR'}
BASE = Settings('postgresql://fixture.invalid/db', ('https://example.test',), True, 3600)


NOT_EVALUABLE = {'state': 'not_evaluable', 'classification': None}


@pytest.mark.parametrize('gemini,local,decision,job,expected', [
    # As duas com categoria: concordância entra, divergência fica para a pessoa.
    (GEMINI, LOCAL_SAME, None, 'completed', (True, 'local', 'agreement')),
    (GEMINI, {'state': 'completed', 'classification': 'APROVADA'}, None, 'completed', (False, None, 'divergence')),
    # Uma falhou: vale a outra.
    (NOT_EVALUABLE, LOCAL_SAME, None, 'completed', (True, 'local', 'gemini_failed')),
    (None, LOCAL_SAME, None, 'failed', (True, 'local', 'gemini_failed')),
    (GEMINI, NOT_EVALUABLE, None, 'completed', (True, 'gemini', 'local_failed')),
    (GEMINI, {'state': 'awaiting_review', 'classification': None}, None, 'completed', (True, 'gemini', 'local_failed')),
    (GEMINI, {'state': 'failed', 'classification': None}, None, 'completed', (True, 'gemini', 'local_failed')),
    # As duas falharam: pessoa decide.
    (NOT_EVALUABLE, NOT_EVALUABLE, None, 'completed', (False, None, 'both_failed')),
    # Ainda rodando: espera (retry_wait/queued não são falha).
    (None, LOCAL_SAME, None, 'retry_wait', (False, None, 'awaiting_gemini')),
    (None, LOCAL_SAME, None, 'queued', (False, None, 'awaiting_gemini')),
    (GEMINI, None, None, 'completed', (False, None, 'awaiting_local')),
    # Decisão existente nunca é sobrescrita.
    (GEMINI, LOCAL_SAME, {'revision': 1}, 'completed', (False, None, 'existing_decision')),
])
def test_one_failure_uses_the_other_and_only_divergence_needs_a_person(gemini, local, decision, job, expected):
    assert auto_adoption(gemini, local, decision, job) == expected


def test_disabled_flag_never_touches_database():
    assert AutoAdoption(BASE).run(uuid4(), uuid4()) == 'disabled'
    assert AutoAdoption(replace(BASE, gemini_auto_adopt=True)).run(uuid4(), uuid4()) == 'disabled'


class Jobs:
    def __init__(self):
        self.job = {'id': uuid4(), 'sample_id': uuid4(), 'user_id': uuid4(), 'attempts': 1,
                    'model_version': 'gemini-3.5-flash-lite', 'criteria_version': 'orange-surface-v1',
                    'image': b'x'}

    def claim(self):
        return self.job

    def finish(self, job, **kwargs):
        return True


class Provider:
    def assess(self, image, model):
        return VisualAssessment(evaluable=True, classification='ATENCAO', reason='Casca verde.'), {'duration_ms': 5}


class Adopter:
    def __init__(self, outcome='adopted', error=None):
        self.calls, self.outcome, self.error = [], outcome, error

    def run(self, sample_id, user_id):
        self.calls.append((sample_id, user_id))
        if self.error:
            raise self.error
        return self.outcome


def test_completed_evaluation_triggers_adoption_and_is_logged(caplog):
    caplog.set_level(logging.INFO, logger='orangevision.web')
    jobs, adopter = Jobs(), Adopter()
    assert process_once(jobs, Provider(), adopter) == 'completed'
    assert adopter.calls == [(jobs.job['sample_id'], jobs.job['user_id'])]
    lines = [r for r in caplog.records if r.getMessage() == 'gemini_auto_adoption']
    assert lines and lines[0].outcome == 'adopted'


def test_adoption_failure_never_breaks_worker(caplog):
    caplog.set_level(logging.INFO, logger='orangevision.web')
    adopter = Adopter(error=RuntimeError('db'))
    assert process_once(Jobs(), Provider(), adopter) == 'completed'
    assert any(r.getMessage() == 'gemini_auto_adoption_failed' for r in caplog.records)


def test_auto_adopt_flag_is_validated(monkeypatch):
    monkeypatch.setenv('WEB_GEMINI_AUTO_ADOPT', 'talvez')
    with pytest.raises(RuntimeError, match='WEB_GEMINI_AUTO_ADOPT'):
        Settings.load()


class FailingProvider:
    def assess(self, image, model):
        from web_api.infrastructure.gemini_provider import ProviderFailure

        raise ProviderFailure('response_invalid', detail={'duration_ms': 3})


def test_gemini_failure_also_triggers_check_so_local_can_stand_alone():
    adopter = Adopter(outcome='gemini_failed')
    assert process_once(Jobs(), FailingProvider(), adopter) == 'response_invalid'
    assert len(adopter.calls) == 1
