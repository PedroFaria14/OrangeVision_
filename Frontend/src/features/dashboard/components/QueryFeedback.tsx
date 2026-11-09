import { Alert, Button, LinearProgress } from '@mui/material';
import { ApiError } from '@/shared/api/client';
import { ZodError } from 'zod';

export function QueryFeedback({
  pending,
  error,
  stale = false,
  retry,
}: {
  pending: boolean;
  error: Error | null;
  stale?: boolean;
  retry: () => void;
}) {
  if (error)
    return (
      <Alert severity="error">
        {error instanceof ZodError
          ? 'Os dados recebidos são incompatíveis com esta versão.'
          : error instanceof ApiError && error.status === 404
            ? 'Registro não encontrado ou sem acesso.'
            : error instanceof ApiError && error.status === 403
              ? 'Você não tem permissão para consultar este recurso.'
              : error instanceof ApiError && error.status === 422
                ? 'Revise o período e os filtros selecionados.'
                : 'Não foi possível atualizar os dados.'}{' '}
        {stale &&
          'A última consulta permanece visível e pode estar desatualizada.'}
        <Button onClick={retry}>Tentar novamente</Button>
      </Alert>
    );
  return pending ? <LinearProgress aria-label="Consultando dados" /> : null;
}
