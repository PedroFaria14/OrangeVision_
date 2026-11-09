import { loadFrontendApiConfig } from '../dev-api-config.ts';

try {
  // Saída exclusiva da URL pública; nunca serializar todo o ambiente.
  console.log(loadFrontendApiConfig().renderOrigin);
} catch {
  console.error('Configure a origem HTTPS da API remota no Frontend/.env.');
  process.exitCode = 1;
}
