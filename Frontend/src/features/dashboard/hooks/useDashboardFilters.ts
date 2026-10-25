import { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import type { Filters } from '../api/analyses';
import { periodSchema } from '../model/filter_validation';
import { recentPeriod } from '../model/period';

function initialPeriod() {
  return {
    ...recentPeriod(30),
    classification: '',
  };
}

export function useDashboardFilters(historyOnly: boolean) {
  const [params, setParams] = useSearchParams();
  const [defaults] = useState(initialPeriod);
  const period = periodSchema.safeParse({
    start: params.get('start') || defaults.start,
    end: params.get('end') || defaults.end,
  });
  const { start, end } = period.success ? period.data : defaults;
  const candidate = params.get('classification') || '';
  const filters: Filters = {
    start,
    end,
    classification: ['APROVADA', 'ATENCAO', 'REVISAR'].includes(candidate)
      ? candidate
      : '',
  };
  const offset = historyOnly
    ? Math.floor(
        Math.min(100000, Math.max(0, Number(params.get('offset')) || 0)) / 20,
      ) * 20
    : 0;
  return {
    filters,
    offset,
    valid: period.success,
    apply: (value: Filters) => setParams({ ...value, offset: '0' }),
    changePage: (value: number) =>
      setParams({ ...Object.fromEntries(params), offset: String(value) }),
  };
}

export function useValidHistoryPage(total: number | undefined, offset: number) {
  const [, setParams] = useSearchParams();
  useEffect(() => {
    if (total !== undefined && offset > 0 && offset >= total) {
      const last = Math.max(0, Math.ceil(total / 20) - 1) * 20;
      setParams(
        (previous) => {
          previous.set('offset', String(last));
          return previous;
        },
        { replace: true },
      );
    }
  }, [total, offset, setParams]);
}
