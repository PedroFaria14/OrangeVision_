import { z } from 'zod';
import { ApiError, getJson, requestJson } from '@/shared/api/client';

const sessionSchema = z.object({
  user: z.object({
    id: z.string().uuid(),
    name: z.string(),
    email: z.string().email(),
  }),
  csrf_token: z.string().min(1),
});
export type Session = z.infer<typeof sessionSchema>;

export async function readSession(signal?: AbortSignal) {
  try {
    return sessionSchema.parse(await getJson('/auth/session', signal));
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) return null;
    throw error;
  }
}
export async function login(email: string, password: string) {
  return sessionSchema.parse(
    await requestJson('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    }),
  );
}
export async function register(name: string, email: string, password: string) {
  await requestJson('/auth/register', {
    method: 'POST',
    body: JSON.stringify({ name, email, password }),
  });
}
export async function logout(csrf: string) {
  await requestJson('/auth/logout', {
    method: 'POST',
    headers: { 'X-CSRF-Token': csrf },
  });
}
