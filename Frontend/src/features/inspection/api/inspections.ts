import { z } from 'zod';
import { getJson, requestJson } from '@/shared/api/client';

const timestamp = z.string().datetime({ offset: true });
export const inspectionSchema = z.object({
  id: z.string().uuid(),
  device_id: z.string().uuid(),
  user_id: z.string().uuid(),
  operator_name: z.string(),
  state: z.enum(['pending', 'active', 'closing', 'closed', 'expired']),
  created_at: timestamp,
  pairing_expires_at: timestamp,
  started_at: timestamp.nullable(),
  authorization_expires_at: timestamp.nullable(),
  closed_at: timestamp.nullable(),
  observed_at: timestamp.nullish(),
});
export type Inspection = z.infer<typeof inspectionSchema>;
const configSchema = z.object({
  enabled: z.boolean(),
  ownership: z.enum(['inspection-session', 'device-access']),
});
const devicesSchema = z.array(
  z.object({ id: z.string().uuid(), name: z.string() }),
);

export async function inspectionConfig(signal?: AbortSignal) {
  return configSchema.parse(await getJson('/inspections/config', signal));
}
export async function inspectionDevices(signal?: AbortSignal) {
  return devicesSchema.parse(await getJson('/inspections/devices', signal));
}
export async function currentInspections(signal?: AbortSignal) {
  return z
    .array(inspectionSchema)
    .parse(await getJson('/inspections/current', signal));
}
export async function startInspection(
  data: { device_id: string; request_id: string; pairing_code: string },
  csrf: string,
) {
  return inspectionSchema.parse(
    await requestJson('/inspections', {
      method: 'POST',
      headers: { 'X-CSRF-Token': csrf },
      body: JSON.stringify(data),
    }),
  );
}
export async function closeInspection(id: string, csrf: string) {
  return inspectionSchema.parse(
    await requestJson(`/inspections/${encodeURIComponent(id)}/close`, {
      method: 'POST',
      headers: { 'X-CSRF-Token': csrf },
    }),
  );
}
