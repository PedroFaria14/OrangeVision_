"""Fachada de compatibilidade; SQL e casos de uso vivem em módulos separados."""

from .application.query_service import QueryService
from .infrastructure.analysis_mapping import adapt as adapt
from .infrastructure.analysis_repository import AnalysisRepository
from .infrastructure.analysis_repository import scope as scope


def analyses(settings, user_id, filters, limit, offset):
    return QueryService(AnalysisRepository(settings)).analyses(user_id, filters, limit, offset)


def detail(settings, user_id, analysis_id):
    return QueryService(AnalysisRepository(settings)).detail(user_id, analysis_id)


def summary(settings, user_id, filters):
    return QueryService(AnalysisRepository(settings)).summary(user_id, filters)


def timeseries(settings, user_id, filters):
    return QueryService(AnalysisRepository(settings)).timeseries(user_id, filters)
