import { z } from 'zod';
import { getJson, requestJson } from '@/shared/api/client';

const deviceSchema = z.object({
  id: z.string().uuid(),
  name: z.string(),
  created_at: z.string().datetime({ offset: true }).nullable(),
  can_manage_credentials: z.boolean(),
});
export const deviceListSchema = z.object({
  items: z.array(deviceSchema),
  registration_enabled: z.boolean(),
  managed_count: z.number().int().nonnegative(),
  max_devices: z.number().int().positive(),
  api_base_url: z.string().nullable().optional(),
});
const issuedSchema = z.object({
  device: deviceSchema,
  credential: z
    .string()
    .regex(/^[A-Za-z0-9_-]{32,128}$/)
    .nullable(),
  replayed: z.boolean(),
});
export type UserDevice = z.infer<typeof deviceSchema>;
export type IssuedCredential = z.infer<typeof issuedSchema>;

export async function listDevices(signal?: AbortSignal) {
  return deviceListSchema.parse(await getJson('/devices', signal));
}

export async function registerDevice(
  name: string,
  requestId: string,
  csrf: string,
) {
  return issuedSchema.parse(
    await requestJson('/devices', {
      method: 'POST',
      headers: { 'X-CSRF-Token': csrf },
      body: JSON.stringify({ name, request_id: requestId }),
    }),
  );
}

export async function rotateDeviceCredential(
  id: string,
  requestId: string,
  csrf: string,
) {
  return issuedSchema.parse(
    await requestJson(`/devices/${id}/credentials`, {
      method: 'POST',
      headers: { 'X-CSRF-Token': csrf },
      body: JSON.stringify({ request_id: requestId }),
    }),
  );
}
