import { z } from 'zod';
import type { Filters } from '../api/analyses';
import { dayStart, nextDay } from './period';

export const periodSchema = z
  .object({
    start: z.string().datetime({ offset: true }),
    end: z.string().datetime({ offset: true }),
  })
  .refine(
    (value) =>
      Date.parse(value.end) > Date.parse(value.start) &&
      Date.parse(value.end) - Date.parse(value.start) <= 366 * 86400000,
  );

const calendarDate = z
  .string()
  .regex(/^\d{4}-\d{2}-\d{2}$/)
  .refine((value) => {
    const date = new Date(`${value}T12:00:00Z`);
    return (
      Number.isFinite(date.getTime()) &&
      date.toISOString().slice(0, 10) === value
    );
  });

const formSchema = z.object({
  start: calendarDate,
  end: calendarDate,
  classification: z.enum(['', 'APROVADA', 'ATENCAO', 'REVISAR']),
});

export function validateFilterForm(form: FormData): Filters | null {
  const result = formSchema.safeParse(Object.fromEntries(form));
  if (!result.success) return null;
  const filters = {
    start: dayStart(result.data.start),
    end: nextDay(result.data.end),
    classification: result.data.classification,
  };
  return periodSchema.safeParse(filters).success ? filters : null;
}
