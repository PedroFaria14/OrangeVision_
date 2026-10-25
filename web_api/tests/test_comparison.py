from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from web_api.api.dependencies import current_session, get_query_service
from web_api.application.comparison import comparison_windows, period_changes, summarize_period
from web_api.application.errors import ApplicationError
from web_api.application.query_service import QueryService
from web_api.contracts import Filters, PeriodComparison
from web_api.infrastructure import analysis_repository
from web_api.main import create_app

from .test_web_api import SETTINGS

NOW = datetime(2026, 10, 20, 15, tzinfo=UTC)


def counts(approved=0, attention=0, review=0):
    return {
        'total': approved + attention + review,
        'approved': approved,
        'attention': attention,
        'review': review,
        'latest_analysis_at': None,
    }


def test_previous_period_is_adjacent_equal_duration_and_crosses_year():
    start = datetime(2026, 1, 1, tzinfo=UTC)
    end = start + timedelta(days=7)
    current, previous = comparison_windows(start, end, NOW)
    assert previous.end == current.start
    assert previous.start == datetime(2025, 12, 25, tzinfo=UTC)
    assert current.end - current.start == previous.end - previous.start
    assert not current.in_progress


def test_offset_change_preserves_real_elapsed_duration():
    start = datetime.fromisoformat('2018-11-03T00:00:00-03:00')
    end = datetime.fromisoformat('2018-11-05T00:00:00-02:00')
    current, previous = comparison_windows(start, end, NOW)
    assert current.end - current.start == timedelta(hours=47)
    assert previous.end - previous.start == timedelta(hours=47)


def test_current_period_is_marked_partial_and_does_not_observe_future():
    current, previous = comparison_windows(NOW - timedelta(days=2), NOW + timedelta(days=1), NOW)
    assert current.in_progress
    assert current.observed_end == NOW
    assert previous.observed_end == previous.end
    assert not previous.in_progress


@pytest.mark.parametrize(
    'start,end',
    [
        (None, None),
        (datetime(2026, 10, 1), datetime(2026, 10, 2)),
        (NOW, NOW + timedelta(days=1)),
        (NOW - timedelta(days=1), NOW - timedelta(days=2)),
        (NOW - timedelta(days=367), NOW),
    ],
)
def test_invalid_period_fails_before_querying(start, end):
    with pytest.raises(ApplicationError) as result:
        comparison_windows(start, end, NOW)
    assert result.value.status_code == 422


def test_comparison_grouping_rates_and_differences_have_explicit_denominators():
    window, previous_window = comparison_windows(
        NOW - timedelta(days=2), NOW - timedelta(days=1), NOW
    )
    current = summarize_period(counts(approved=6, attention=3, review=1), window, NOW)
    previous = summarize_period(counts(approved=2, attention=1, review=2), previous_window, NOW)
    changes = period_changes(current, previous)
    assert current['not_approved'] == 4
    assert current['approval_rate'] == 0.6
    assert changes['total'] == {'absolute': 5, 'percent': 100}
    assert changes['approved'] == {'absolute': 4, 'percent': 200}
    assert changes['review'] == {'absolute': -1, 'percent': -50}
    assert changes['approval_rate_pp'] == pytest.approx(20)


def test_zero_previous_count_never_creates_infinite_growth_or_a_false_rate():
    window, previous_window = comparison_windows(
        NOW - timedelta(days=2), NOW - timedelta(days=1), NOW
    )
    current = summarize_period(counts(approved=2), window, NOW)
    previous = summarize_period(counts(), previous_window, NOW)
    changes = period_changes(current, previous)
    assert previous['approval_rate'] is None
    assert changes['approved'] == {'absolute': 2, 'percent': None}
    assert changes['approval_rate_pp'] is None
    empty_changes = period_changes(previous, previous)
    assert empty_changes['total'] == {'absolute': 0, 'percent': None}


def test_defined_zero_approval_rate_still_allows_percentage_point_comparison():
    window, previous_window = comparison_windows(
        NOW - timedelta(days=2), NOW - timedelta(days=1), NOW
    )
    current = summarize_period(counts(approved=3), window, NOW)
    previous = summarize_period(counts(attention=2), previous_window, NOW)
    changes = period_changes(current, previous)
    assert previous['approval_rate'] == 0
    assert changes['approval_rate_pp'] == 100
    assert changes['approved']['percent'] is None


class AccountReader:
    def __init__(self):
        self.calls = []

    def compare_periods(self, user_id, filters, current, previous):
        self.calls.append((user_id, filters, current, previous))
        return {
            'current': counts(approved=2 if user_id == UUID(int=1) else 7),
            'previous': counts(approved=1),
        }


def test_http_comparison_uses_authenticated_user_not_a_query_string_identity():
    reader = AccountReader()
    app = create_app(SETTINGS)
    app.dependency_overrides[get_query_service] = lambda: QueryService(reader, clock=lambda: NOW)
    app.dependency_overrides[current_session] = lambda: {'user': {'id': UUID(int=1)}}
    query = '/api/metrics/comparison?start=2026-10-01T00:00:00Z&end=2026-10-08T00:00:00Z&user_id=00000000-0000-0000-0000-000000000002'
    with TestClient(app) as client:
        response = client.get(query)
        assert response.status_code == 200
        parsed = PeriodComparison.model_validate(response.json())
        assert parsed.current.approved == 2
        assert parsed.current.as_of == parsed.previous.as_of == parsed.as_of
        assert reader.calls[-1][0] == UUID(int=1)
        app.dependency_overrides[current_session] = lambda: {'user': {'id': UUID(int=2)}}
        second = client.get(query)
        assert second.json()['current']['approved'] == 7
        assert reader.calls[-1][0] == UUID(int=2)


def test_http_comparison_requires_session():
    with TestClient(create_app(SETTINGS)) as client:
        assert client.get('/api/metrics/comparison').status_code == 401


def test_repository_keeps_authorization_inside_left_join_and_uses_periods_not_page(monkeypatch):
    calls = []

    class Database:
        def execute(self, sql, params=None):
            calls.append((sql, params))
            return self

        def fetchall(self):
            return [{'period_key': key, **counts()} for key in ('current', 'previous')]

    @contextmanager
    def fake_connection(settings):
        yield Database()

    monkeypatch.setattr(analysis_repository, 'connection', fake_connection)
    filters = Filters(
        start=NOW - timedelta(days=2),
        end=NOW - timedelta(days=1),
        classification='ATENCAO',
        device_id=UUID(int=9),
    )
    current, previous = comparison_windows(filters.start, filters.end, NOW)
    rows = analysis_repository.AnalysisRepository(SETTINGS).compare_periods(
        UUID(int=1), filters, current, previous
    )
    sql, params = calls[-1]
    assert 'LEFT JOIN analises a' in sql
    assert 'da.user_id=%s' in sql and 'da.device_id=a.dispositivo_id' in sql
    assert 'a.data_hora>=p.start_at AND a.data_hora<p.end_at' in sql
    assert 'LIMIT' not in sql and 'OFFSET' not in sql
    assert params == [
        current.start,
        current.observed_end,
        previous.start,
        previous.observed_end,
        UUID(int=1),
        'ATENCAO',
        UUID(int=9),
    ]
    assert rows['current']['total'] == rows['previous']['total'] == 0
