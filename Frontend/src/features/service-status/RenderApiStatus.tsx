import { Box, Button, Chip, Stack, Typography } from '@mui/material';
import { useQuery } from '@tanstack/react-query';
import { z } from 'zod';

const schema = z.object({
  state: z.enum(['available', 'unavailable', 'unreachable', 'unexpected']),
  checkedAt: z.iso.datetime(),
  durationMs: z.number().int().nonnegative(),
  httpStatus: z.number().int().min(100).max(599).nullable(),
});

async function fetchStatus(signal: AbortSignal) {
  const response = await fetch('/api/status/render', {
    credentials: 'omit',
    cache: 'no-store',
    signal: AbortSignal.any([signal, AbortSignal.timeout(15000)]),
  });
  if (!response.ok) throw new Error('Status indisponível');
  return schema.parse(await response.json());
}

const labels = {
  available: 'Disponível',
  unavailable: 'Indisponível',
  unreachable: 'Sem resposta',
  unexpected: 'Resposta inesperada',
} as const;

export function RenderApiStatus() {
  const { data, isFetching, isError, refetch } = useQuery({
    queryKey: ['render-api-status'],
    queryFn: ({ signal }) => fetchStatus(signal),
    retry: false,
    staleTime: 15000,
    refetchInterval: 60000,
    refetchIntervalInBackground: false,
    refetchOnWindowFocus: true,
  });
  const label = isFetching
    ? 'Verificando'
    : isError
      ? 'Status não confirmado'
      : data
        ? labels[data.state]
        : 'Status não confirmado';
  const color = isFetching
    ? 'warning'
    : !isError && data?.state === 'available'
      ? 'success'
      : !isError && data?.state === 'unavailable'
        ? 'error'
        : 'default';
  return (
    <Stack
      component="section"
      aria-label="Status da API do Render"
      direction={{ xs: 'column', sm: 'row' }}
      sx={{
        gap: 1,
        alignItems: { sm: 'center' },
        justifyContent: 'space-between',
        bgcolor: 'white',
        borderBottom: '1px solid #E6EBEF',
        px: { xs: 2, sm: 3, lg: 5 },
        py: 1,
      }}
    >
      <Box>
        <Stack
          direction="row"
          sx={{ gap: 1, alignItems: 'center', flexWrap: 'wrap' }}
        >
          <Typography variant="body2" sx={{ fontWeight: 600 }}>
            API do Render
          </Typography>
          <Box role="status" aria-live="polite" aria-atomic="true">
            <Chip size="small" label={label} color={color} variant="outlined" />
          </Box>
          {data && (
            <Typography variant="caption" color="text.secondary">
              {isError ? 'Última resposta: ' : 'Verificação: '}
              {new Date(data.checkedAt).toLocaleTimeString('pt-BR')} ·{' '}
              {data.durationMs} ms
              {data.httpStatus !== null ? ` · HTTP ${data.httpStatus}` : ''}
            </Typography>
          )}
        </Stack>
        <Typography variant="caption" color="text.secondary">
          Serviço remoto; não representa a API local nem confirma o banco.
          Atualização a cada 60 s com esta aba visível.
        </Typography>
      </Box>
      <Button
        size="small"
        disabled={isFetching}
        onClick={() => void refetch()}
        sx={{
          flexShrink: 0,
          alignSelf: { xs: 'flex-start', sm: 'center' },
          minHeight: 44,
        }}
      >
        Verificar novamente
      </Button>
    </Stack>
  );
}
