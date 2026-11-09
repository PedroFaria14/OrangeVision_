import { Alert, Box, Button, LinearProgress } from '@mui/material';
import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { useSession } from '../hooks/useSession';

export default function ProtectedLayout() {
  const auth = useSession();
  const location = useLocation();
  if (auth.pending)
    return (
      <Box sx={{ maxWidth: 520, mx: 'auto', mt: 12, p: 3 }}>
        <LinearProgress aria-label="Consultando sessão" />
      </Box>
    );
  if (auth.error)
    return (
      <Alert severity="error" sx={{ m: 3 }}>
        Não foi possível validar a sessão.{' '}
        <Button onClick={auth.retry}>Tentar novamente</Button>
      </Alert>
    );
  if (!auth.session)
    return (
      <Navigate
        to={`/login?next=${encodeURIComponent(location.pathname + location.search)}`}
        replace
      />
    );

  return <Outlet />;
}
