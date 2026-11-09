import { config } from 'dotenv';
import { fileURLToPath } from 'node:url';
import { defineConfig, env } from 'prisma/config';

// A conexão do Studio é independente da credencial de escrita usada pela API.
config({ path: fileURLToPath(new URL('./.env', import.meta.url)), quiet: true });

export default defineConfig({
  datasource: {
    url: env('STUDIO_DATABASE_URL'),
  },
});
