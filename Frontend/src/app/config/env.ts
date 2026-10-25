import { z } from 'zod';

const config = z.object({
  base: z
    .string()
    .refine(
      (value) => value.startsWith('/') && !value.startsWith('//'),
      'Use um caminho de mesma origem, como /api.',
    ),
  enabled: z.boolean(),
});

export const env = config.parse({
  base: (import.meta.env.VITE_API_BASE_URL || '/api').replace(/\/$/, ''),
  enabled: import.meta.env.VITE_API_ENABLED !== 'false',
});
