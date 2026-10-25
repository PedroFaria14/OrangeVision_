import { TZDate } from '@date-fns/tz';

export function recentPeriod(days: number, now = new Date()) {
  const endDate = new Intl.DateTimeFormat('en-CA', {
    timeZone: 'America/Sao_Paulo',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).format(now);
  const today = new Date(`${endDate}T12:00:00Z`);
  today.setUTCDate(today.getUTCDate() - days + 1);
  return {
    start: dayStart(today.toISOString().slice(0, 10)),
    end: nextDay(endDate),
  };
}

export function dayStart(date: string) {
  const [year, month, day] = date.split('-').map(Number);
  return new TZDate(
    year,
    month - 1,
    day,
    0,
    0,
    0,
    'America/Sao_Paulo',
  ).toISOString();
}
export function nextDay(date: string) {
  const value = new Date(`${date}T12:00:00Z`);
  value.setUTCDate(value.getUTCDate() + 1);
  return dayStart(value.toISOString().slice(0, 10));
}

export function previousCalendarDay(value: string) {
  const date = new TZDate(value, 'America/Sao_Paulo');
  date.setDate(date.getDate() - 1);
  return date.toISOString().slice(0, 10);
}
