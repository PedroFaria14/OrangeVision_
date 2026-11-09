import { z } from 'zod';

export const deviceNameSchema = z
  .string()
  .trim()
  .min(2)
  .max(100)
  .refine((value) =>
    Array.from(value).every(
      (character) => character === ' ' || !/[\p{C}\p{Z}]/u.test(character),
    ),
  );

export function apiOrigin(value: string): string | null {
  try {
    const url = new URL(value.trim());
    if (
      url.protocol !== 'https:' ||
      url.username ||
      url.password ||
      url.search ||
      url.hash ||
      url.pathname !== '/'
    )
      return null;
    return url.origin;
  } catch {
    return null;
  }
}
