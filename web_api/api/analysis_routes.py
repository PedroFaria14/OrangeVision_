from uuid import UUID

from fastapi import APIRouter, Query

from ..contracts import Analysis, AnalysisPage, PeriodComparison, Summary, Timeseries
from .dependencies import CurrentSession, QueryDependency, QueryFilters

router = APIRouter()


@router.get('/api/analyses', response_model=AnalysisPage)
def analyses(
    filters: QueryFilters,
    value: CurrentSession,
    service: QueryDependency,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0, le=100000),
):
    return service.analyses(value['user']['id'], filters, limit, offset)


@router.get('/api/analyses/{analysis_id}', response_model=Analysis)
def detail(analysis_id: UUID, value: CurrentSession, service: QueryDependency):
    return service.detail(value['user']['id'], analysis_id)


@router.get('/api/metrics/summary', response_model=Summary)
def summary(filters: QueryFilters, value: CurrentSession, service: QueryDependency):
    return service.summary(value['user']['id'], filters)


@router.get('/api/metrics/distribution', response_model=Summary)
def distribution(filters: QueryFilters, value: CurrentSession, service: QueryDependency):
    return service.summary(value['user']['id'], filters)


@router.get('/api/metrics/timeseries', response_model=Timeseries)
def timeseries(filters: QueryFilters, value: CurrentSession, service: QueryDependency):
    return service.timeseries(value['user']['id'], filters)


@router.get('/api/metrics/comparison', response_model=PeriodComparison)
def comparison(filters: QueryFilters, value: CurrentSession, service: QueryDependency):
    return service.comparison(value['user']['id'], filters)
