import { Alert, Button } from '@mui/material';
import { isRouteErrorResponse, Link, useRouteError } from 'react-router-dom';

export function RouteError() {
  const error = useRouteError();
  return (
    <Alert severity="error">
      {isRouteErrorResponse(error) && error.status === 404
        ? 'Página não encontrada.'
        : 'Não foi possível abrir esta página.'}
      <Button component={Link} to="/">
        Voltar ao início
      </Button>
    </Alert>
  );
}
