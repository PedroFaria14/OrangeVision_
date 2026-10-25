// Dados de contrato APENAS para testes de interface; não entram no aplicativo.
type Counts = { approved: number; attention: number; review: number };
const asOf = '2026-10-20T15:00:00Z';

export function comparisonFixture(
  url: string,
  currentCounts: Counts = { approved: 1, attention: 0, review: 0 },
  previousCounts: Counts = { approved: 2, attention: 1, review: 1 },
) {
  const query = new URL(url).searchParams;
  const start = Date.parse(query.get('start') || '2026-09-21T03:00:00Z');
  const end = Date.parse(query.get('end') || '2026-10-21T03:00:00Z');
  function period(counts: Counts, from: number, to: number) {
    const total = counts.approved + counts.attention + counts.review;
    const observed = Math.min(to, Date.parse(asOf));
    return {
      ...counts,
      total,
      not_approved: counts.attention + counts.review,
      approval_rate: total ? counts.approved / total : null,
      latest_analysis_at: total
        ? new Date(
            Math.max(
              from,
              Math.min(Date.parse('2026-10-20T12:00:00Z'), observed - 1),
            ),
          ).toISOString()
        : null,
      start: new Date(from).toISOString(),
      end: new Date(to).toISOString(),
      observed_end: new Date(observed).toISOString(),
      in_progress: observed < to,
      as_of: asOf,
    };
  }
  const current = period(currentCounts, start, end);
  const previous = period(previousCounts, start - (end - start), start);
  const changes = Object.fromEntries(
    (['total', 'approved', 'attention', 'review', 'not_approved'] as const).map(
      (key) => [
        key,
        {
          absolute: current[key] - previous[key],
          percent: previous[key]
            ? ((current[key] - previous[key]) / previous[key]) * 100
            : null,
        },
      ],
    ),
  );
  return {
    current,
    previous,
    changes: {
      ...changes,
      approval_rate_pp:
        current.approval_rate !== null && previous.approval_rate !== null
          ? (current.approval_rate - previous.approval_rate) * 100
          : null,
    },
    as_of: asOf,
    timezone: 'America/Sao_Paulo',
    boundary: 'start-inclusive-end-exclusive',
  };
}
