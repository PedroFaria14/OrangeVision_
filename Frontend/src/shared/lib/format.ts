export function formatDate(value: string | null) {
  if (!value || !Number.isFinite(Date.parse(value))) return 'Não informado';
  return new Intl.DateTimeFormat('pt-BR', {
    dateStyle: 'short',
    timeStyle: 'short',
    timeZone: 'America/Sao_Paulo',
  }).format(new Date(value));
}
export function formatNumber(value: number | null, digits = 1) {
  return value === null
    ? '—'
    : new Intl.NumberFormat('pt-BR', { maximumFractionDigits: digits }).format(
        value,
      );
}
export function formatRatio(value: number | null) {
  return value === null ? '—' : `${formatNumber(value * 100)}%`;
}
