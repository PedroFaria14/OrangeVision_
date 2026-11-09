import { probeApiHealth } from '../dev-api-status.ts';
import { loadFrontendApiConfig } from '../dev-api-config.ts';

const args = process.argv.slice(2);
if (args.length && (args.length !== 2 || args[0] !== '--url')) {
  console.error('Uso: yarn status:api [--url https://origem-da-api]');
  process.exitCode = 2;
} else {
  try {
    const origin = args[1] || loadFrontendApiConfig().renderOrigin;
    const result = await probeApiHealth(origin);
    const labels = {
      available: 'DISPONIVEL',
      unavailable: 'INDISPONIVEL',
      unreachable: 'SEM RESPOSTA (timeout ou falha de conexao)',
      unexpected: 'RESPOSTA INESPERADA (API nao confirmada)',
    };
    console.log(`API ${origin}: ${labels[result.state]}`);
    console.log(
      `HTTP: ${result.httpStatus ?? 'sem resposta'} | ${result.durationMs} ms | ${result.checkedAt}`,
    );
    console.log(
      'Health verifica o processo da API, nao a disponibilidade do banco.',
    );
    if (result.state !== 'available') process.exitCode = 1;
  } catch {
    console.error(
      'Configure uma origem valida no Frontend/.env ou informe --url.',
    );
    process.exitCode = 2;
  }
}
