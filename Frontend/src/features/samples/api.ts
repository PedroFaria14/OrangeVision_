import { z } from 'zod';
import { getJson, requestJson } from '@/shared/api/client';

export const sampleStates = {
  received: 'Imagem recebida',
  queued: 'Aguardando análise',
  processing: 'Em análise',
  awaiting_review: 'Aguardando avaliação',
  completed: 'Concluída',
  not_evaluable: 'Não foi possível avaliar',
  failed: 'Falha no processamento',
} as const;
const metric = z.number().finite().nullable();
const category = z.enum(['APROVADA', 'ATENCAO', 'REVISAR']);
const evaluationSchema = z.object({
  id: z.string().uuid(),
  origin: z.enum(['local', 'gemini']),
  state: z.enum(['completed', 'awaiting_review', 'not_evaluable', 'failed']),
  classification: category.nullable(),
  reason: z.string(),
  criteria_version: z.string(),
  model_version: z.string().nullable(),
  created_at: z.string().datetime({ offset: true }),
});
export type Evaluation = z.infer<typeof evaluationSchema>;
export const sampleSchema = z.object({
  id: z.string().uuid(),
  filename: z.string(),
  width: z.number().int().positive(),
  height: z.number().int().positive(),
  state: z.enum([
    'received',
    'queued',
    'processing',
    'awaiting_review',
    'completed',
    'not_evaluable',
    'failed',
  ]),
  device_id: z.string().uuid().nullable(),
  metrics: z
    .object({
      orange_color_ratio: metric,
      abnormal_region_ratio: metric,
      circularity: metric,
      asymmetry: metric,
      visual_score: metric,
    })
    .nullable(),
  classification: z.enum(['APROVADA', 'ATENCAO', 'REVISAR']).nullable(),
  reason: z.string().nullable(),
  calibration_version: z.string().nullable(),
  algorithm_version: z.string().nullable(),
  image_url: z.string().regex(/^\/api\/samples\/[0-9a-f-]+\/image$/i),
  mask_url: z
    .string()
    .regex(/^\/api\/samples\/[0-9a-f-]+\/mask$/i)
    .nullable(),
  created_at: z.string().datetime({ offset: true }),
  updated_at: z.string().datetime({ offset: true }),
  started_at: z.string().datetime({ offset: true }).nullable(),
  finished_at: z.string().datetime({ offset: true }).nullable(),
  claim_expires_at: z.string().datetime({ offset: true }).nullable(),
  detection: z
    .object({
      status: z.enum(['detected', 'not_detected', 'ambiguous']),
      label: z.literal('orange').nullable(),
      score: z.number().min(0).max(1).nullable(),
      box: z.array(z.number().int().nonnegative()).length(4).nullable(),
      count: z.number().int().nonnegative(),
      model: z.string(),
      inference_ms: z.number().finite().nonnegative(),
    })
    .nullish(),
  source_inspection_id: z.string().uuid().nullish(),
  analysis_id: z.string().uuid().nullish(),
  evaluations: z.array(evaluationSchema).optional().default([]),
  comparison: z
    .enum(['pending', 'agreement', 'divergence', 'inconclusive'])
    .optional()
    .default('pending'),
  gemini_job: z
    .object({
      id: z.string().uuid(),
      state: z.enum(['queued', 'running', 'retry_wait', 'completed', 'failed']),
      attempts: z.number().int(),
      error_code: z.string().nullable(),
      updated_at: z.string().datetime({ offset: true }),
    })
    .nullish(),
  decision: z
    .object({
      revision: z.number().int(),
      origin: z.enum(['local', 'gemini', 'human']),
      classification: category,
      reason: z.string(),
      created_at: z.string().datetime({ offset: true }),
    })
    .nullish(),
  captured_at: z.string().datetime({ offset: true }).nullish(),
  review_authorization_id: z.string().uuid().nullish(),
});
export type Sample = z.infer<typeof sampleSchema>;

export async function samplesConfig(signal?: AbortSignal) {
  return z
    .object({
      enabled: z.boolean(),
      dashboard_enabled: z.boolean().optional(),
      dashboard_status: z
        .enum([
          'enabled',
          'inspections_disabled',
          'schema_unavailable',
          'permissions_missing',
        ])
        .optional(),
      evaluations_enabled: z.boolean().optional(),
      gemini_enabled: z.boolean().optional(),
      processing: z.literal('device'),
      max_upload_bytes: z.number().int().positive(),
    })
    .parse(await getJson('/samples/config', signal));
}
export async function sampleDevices(signal?: AbortSignal) {
  return z
    .array(
      z.object({
        id: z.string().uuid(),
        name: z.string(),
        last_seen_at: z.string().datetime({ offset: true }).nullish(),
        executor_state: z
          .enum(['starting', 'ready', 'error', 'stopped'])
          .nullish(),
        executor_message: z.string().nullish(),
        executor_recent: z.boolean().optional().default(false),
        model_version: z.string().nullish(),
      }),
    )
    .parse(await getJson('/samples/executors', signal));
}
export async function listSamples(offset: number, signal?: AbortSignal) {
  return z
    .object({
      items: z.array(sampleSchema),
      total: z.number().int().nonnegative(),
    })
    .parse(await getJson(`/samples?limit=20&offset=${offset}`, signal));
}
export async function uploadSample(
  file: File,
  requestId: string,
  csrf: string,
) {
  const query = new URLSearchParams({
    request_id: requestId,
    filename: file.name,
  });
  return sampleSchema.parse(
    await requestJson(`/samples?${query}`, {
      method: 'POST',
      body: file,
      headers: {
        'Content-Type': 'application/octet-stream',
        'X-CSRF-Token': csrf,
      },
    }),
  );
}
export async function queueSample(id: string, deviceId: string, csrf: string) {
  return sampleSchema.parse(
    await requestJson(`/samples/${id}/queue`, {
      method: 'POST',
      body: JSON.stringify({ device_id: deviceId }),
      headers: { 'X-CSRF-Token': csrf },
    }),
  );
}

export async function publishSample(id: string, csrf: string) {
  return sampleSchema.parse(
    await requestJson(`/samples/${id}/analysis`, {
      method: 'POST',
      headers: { 'X-CSRF-Token': csrf },
    }),
  );
}

export type DecisionCommand = {
  request_id: string;
  expected_revision: number;
  evaluation_id: string | null;
  classification: 'APROVADA' | 'ATENCAO' | 'REVISAR';
  reason: string;
};
export async function requestGemini(
  id: string,
  requestId: string,
  csrf: string,
) {
  return sampleSchema.parse(
    await requestJson(`/samples/${id}/evaluations/gemini`, {
      method: 'POST',
      headers: { 'X-CSRF-Token': csrf },
      body: JSON.stringify({ request_id: requestId }),
    }),
  );
}
export async function adoptDecision(
  id: string,
  command: DecisionCommand,
  csrf: string,
) {
  return sampleSchema.parse(
    await requestJson(`/samples/${id}/decisions`, {
      method: 'POST',
      headers: { 'X-CSRF-Token': csrf },
      body: JSON.stringify(command),
    }),
  );
}
