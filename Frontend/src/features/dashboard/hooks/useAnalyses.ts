import { useQuery } from '@tanstack/react-query';
import { listAnalyses, readSeries, type Filters } from '../api/analyses';
import { useSession } from '@/features/auth/hooks/useSession';
import { readComparison } from '../api/comparison';
export const apiEnabled = import.meta.env.VITE_API_ENABLED !== 'false';
export function useDashboard(
  offset: number,
  filters: Filters,
  includeMetrics = true,
) {
  const { session } = useSession();
  const shared = {
    enabled: apiEnabled && !!session,
    refetchInterval: 30_000,
    refetchIntervalInBackground: false,
  };
  const scope = ['private', session?.user.id];
  const analyses = useQuery({
    ...shared,
    queryKey: [...scope, 'analyses', filters, offset],
    queryFn: ({ signal }) => listAnalyses(offset, filters, signal),
  });
  const comparison = useQuery({
    ...shared,
    enabled: shared.enabled && includeMetrics,
    queryKey: [...scope, 'comparison', filters],
    queryFn: ({ signal }) => readComparison(filters, signal),
  });
  const series = useQuery({
    ...shared,
    queryKey: [...scope, 'series', filters],
    queryFn: ({ signal }) => readSeries(filters, signal),
    enabled:
      shared.enabled && includeMetrics && !!filters.start && !!filters.end,
  });
  const summary = { ...comparison, data: comparison.data?.current };
  return { analyses, summary, series, comparison };
}
