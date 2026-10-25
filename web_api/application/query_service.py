from datetime import UTC, datetime

from .comparison import comparison_windows, period_changes, summarize_period
from .errors import ApplicationError
from .ports import AnalysisReader


class QueryService:
    def __init__(self, reader: AnalysisReader, clock=None):
        self.reader = reader
        self.clock = clock or (lambda: datetime.now(UTC))

    def analyses(self, user_id, filters, limit, offset):
        items, total = self.reader.list_analyses(user_id, filters, limit, offset)
        return {'items': items, 'total': total, 'as_of': datetime.now(UTC)}

    def detail(self, user_id, analysis_id):
        record = self.reader.find_analysis(user_id, analysis_id)
        if not record:
            raise ApplicationError(404, 'Análise não encontrada ou sem acesso.')
        return record

    def summary(self, user_id, filters):
        row = self.reader.summarize(user_id, filters)
        return {
            **row,
            'approval_rate': row['approved'] / row['total'] if row['total'] else None,
            'as_of': datetime.now(UTC),
        }

    def timeseries(self, user_id, filters):
        if (
            not filters.start
            or not filters.end
            or (filters.end - filters.start).total_seconds() > 366 * 86400
        ):
            raise ApplicationError(
                422, [{'field': 'period', 'message': 'A evolução exige período de até 366 dias.'}]
            )
        return {'items': self.reader.aggregate_daily(user_id, filters), 'as_of': datetime.now(UTC)}

    def comparison(self, user_id, filters):
        as_of = self.clock()
        current_window, previous_window = comparison_windows(filters.start, filters.end, as_of)
        rows = self.reader.compare_periods(user_id, filters, current_window, previous_window)
        current = summarize_period(rows['current'], current_window, as_of)
        previous = summarize_period(rows['previous'], previous_window, as_of)
        return {
            'current': current,
            'previous': previous,
            'changes': period_changes(current, previous),
            'as_of': as_of,
        }
