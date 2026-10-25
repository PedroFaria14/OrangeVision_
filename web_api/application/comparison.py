from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from .errors import ApplicationError


@dataclass(frozen=True)
class PeriodWindow:
    start: datetime
    end: datetime
    observed_end: datetime

    @property
    def in_progress(self) -> bool:
        return self.observed_end < self.end


def comparison_windows(start: datetime | None, end: datetime | None, as_of: datetime):
    if not start or not end or start.utcoffset() is None or end.utcoffset() is None:
        raise ApplicationError(
            422, [{'field': 'period', 'message': 'Informe início e fim com fuso horário.'}]
        )
    start, end, as_of = start.astimezone(UTC), end.astimezone(UTC), as_of.astimezone(UTC)
    duration = end - start
    if not timedelta(0) < duration <= timedelta(days=366):
        raise ApplicationError(
            422, [{'field': 'period', 'message': 'Escolha um período válido de até 366 dias.'}]
        )
    if start >= as_of:
        raise ApplicationError(
            422, [{'field': 'period', 'message': 'O período selecionado ainda não começou.'}]
        )
    try:
        previous_start = start - duration
    except OverflowError as exc:
        raise ApplicationError(
            422, [{'field': 'period', 'message': 'Intervalo de datas não suportado.'}]
        ) from exc
    return PeriodWindow(start, end, min(end, as_of)), PeriodWindow(previous_start, start, start)


def summarize_period(row: dict, period: PeriodWindow, as_of: datetime) -> dict:
    return {
        **row,
        'not_approved': row['attention'] + row['review'],
        'approval_rate': row['approved'] / row['total'] if row['total'] else None,
        'start': period.start,
        'end': period.end,
        'observed_end': period.observed_end,
        'in_progress': period.in_progress,
        'as_of': as_of,
    }


def period_changes(current: dict, previous: dict) -> dict:
    result = {}
    for key in ('total', 'approved', 'attention', 'review', 'not_approved'):
        difference = current[key] - previous[key]
        result[key] = {
            'absolute': difference,
            'percent': difference / previous[key] * 100 if previous[key] else None,
        }
    current_rate, previous_rate = current['approval_rate'], previous['approval_rate']
    result['approval_rate_pp'] = (
        (current_rate - previous_rate) * 100
        if current_rate is not None and previous_rate is not None
        else None
    )
    return result
