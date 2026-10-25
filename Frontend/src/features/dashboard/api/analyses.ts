import { z } from 'zod';
import { getJson } from '@/shared/api/client';
const ratio = z.number().min(0).max(1).nullable();
const timestamp = z.string().datetime({ offset: true });
export const analysisSchema = z.object({
  id: z.string().uuid(),
  timestamp,
  classification: z.enum(['APROVADA', 'ATENCAO', 'REVISAR']),
  metrics: z.object({
    orange_color_ratio: ratio,
    abnormal_region_ratio: ratio,
    circularity: z.number().nonnegative().nullable(),
    asymmetry: ratio,
    visual_score: z.number().min(0).max(100).nullable(),
  }),
  image_url: z.null(),
  lot: z.null(),
  calibration_version: z.string().nullable(),
  device_id: z.string().uuid().nullable(),
  synced_at: z.null(),
  inspection_session_id: z.string().uuid().nullish(),
  classification_reason: z.string().nullish(),
});
export type Analysis = z.infer<typeof analysisSchema>;
const count = z.number().int().nonnegative();
const pageSchema = z.object({
  items: z.array(analysisSchema),
  total: count,
  as_of: timestamp,
});
export const summarySchema = z.object({
  total: count,
  approved: count,
  attention: count,
  review: count,
  approval_rate: ratio,
  latest_analysis_at: timestamp.nullable(),
  as_of: timestamp,
});
export type Summary = z.infer<typeof summarySchema>;
const seriesSchema = z.object({
  items: z.array(
    z.object({
      start: timestamp,
      approved: count,
      attention: count,
      review: count,
    }),
  ),
  coverage: z.literal('observed-only'),
  granularity: z.literal('day'),
  timezone: z.literal('America/Sao_Paulo'),
  as_of: timestamp,
});
export type Series = z.infer<typeof seriesSchema>;
export type Filters = { start: string; end: string; classification: string };
export function filterParams(filters: Filters) {
  const params = new URLSearchParams();
  if (filters.start) params.set('start', filters.start);
  if (filters.end) params.set('end', filters.end);
  if (filters.classification)
    params.set('classification', filters.classification);
  return params;
}
export async function listAnalyses(
  offset: number,
  filters: Filters,
  signal?: AbortSignal,
) {
  const params = filterParams(filters);
  params.set('limit', '20');
  params.set('offset', String(offset));
  return pageSchema.parse(await getJson(`/analyses?${params}`, signal));
}
export async function readSummary(filters: Filters, signal?: AbortSignal) {
  return summarySchema.parse(
    await getJson(`/metrics/summary?${filterParams(filters)}`, signal),
  );
}
export async function readSeries(filters: Filters, signal?: AbortSignal) {
  return seriesSchema.parse(
    await getJson(`/metrics/timeseries?${filterParams(filters)}`, signal),
  );
}
export async function readAnalysis(id: string, signal?: AbortSignal) {
  return analysisSchema.parse(
    await getJson(`/analyses/${encodeURIComponent(id)}`, signal),
  );
}
