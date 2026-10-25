import { z } from 'zod';
import { getJson } from '@/shared/api/client';
import { filterParams, summarySchema, type Filters } from './analyses';

const timestamp = z.string().datetime({ offset: true });
const periodSchema = summarySchema
  .extend({
    start: timestamp,
    end: timestamp,
    observed_end: timestamp,
    in_progress: z.boolean(),
    not_approved: z.number().int().nonnegative(),
  })
  .superRefine((period, context) => {
    if (
      period.total !== period.approved + period.attention + period.review ||
      period.not_approved !== period.attention + period.review
    ) {
      context.addIssue({
        code: 'custom',
        message: 'Contagens de classificação inconsistentes.',
      });
    }
    const start = Date.parse(period.start),
      end = Date.parse(period.end),
      observed = Date.parse(period.observed_end);
    if (
      end <= start ||
      observed < start ||
      observed > end ||
      period.in_progress !== observed < end
    ) {
      context.addIssue({
        code: 'custom',
        message: 'Período de comparação inconsistente.',
      });
    }
  });
const changeSchema = z.object({
  absolute: z.number().int(),
  percent: z.number().finite().nullable(),
});
export const comparisonSchema = z.object({
  current: periodSchema,
  previous: periodSchema,
  changes: z.object({
    total: changeSchema,
    approved: changeSchema,
    attention: changeSchema,
    review: changeSchema,
    not_approved: changeSchema,
    approval_rate_pp: z.number().finite().nullable(),
  }),
  as_of: timestamp,
  timezone: z.literal('America/Sao_Paulo'),
  boundary: z.literal('start-inclusive-end-exclusive'),
});
export type Comparison = z.infer<typeof comparisonSchema>;
export type CountChange = z.infer<typeof changeSchema>;

export async function readComparison(filters: Filters, signal?: AbortSignal) {
  return comparisonSchema.parse(
    await getJson(`/metrics/comparison?${filterParams(filters)}`, signal),
  );
}
