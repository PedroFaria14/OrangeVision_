import {
  Alert,
  Box,
  Button,
  CircularProgress,
  Divider,
  Stack,
  Typography,
} from '@mui/material';
import { Link, Navigate, useNavigate, useSearchParams } from 'react-router-dom';
import { Brand } from '@/shared/ui/Brand';
import { login, register } from '../api/session';
import { AuthForm } from '../components/AuthForm';
import { useSession } from '../hooks/useSession';

export default function AuthPage({
  registering = false,
}: {
  registering?: boolean;
}) {
  const auth = useSession();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const created = params.get('registered') === '1';
  const requested = params.get('next') || '/dashboard';
  const destination = /^\/dashboard(?:\/|\?|$)/.test(requested)
    ? requested
    : '/dashboard';
  if (auth.session) return <Navigate to={destination} replace />;
  return (
    <Stack sx={{ width: '100%', maxWidth: 380 }} spacing={{ xs: 2, md: 2.5 }}>
      <Box sx={{ textAlign: 'center', mb: 0.5 }}>
        <Brand large />
        <Typography
          component="h1"
          sx={{
            fontFamily: 'Montserrat, sans-serif',
            fontWeight: 650,
            fontSize: 23,
            mt: 2,
            mb: 1,
          }}
        >
          {registering ? 'Criar conta' : 'Entrar'}
        </Typography>
        <Typography sx={{ fontSize: 14, color: 'text.secondary' }}>
          {registering
            ? 'Crie sua conta e comece a acompanhar.'
            : 'Acesse sua conta para continuar.'}
        </Typography>
      </Box>
      {auth.pending ? (
        <Stack
          role="status"
          direction="row"
          sx={{ gap: 2, alignItems: 'center' }}
        >
          <CircularProgress size={22} aria-label="Verificação da sessão" />
          <Typography variant="body2">Verificando sua sessão…</Typography>
        </Stack>
      ) : auth.error ? (
        <Alert
          severity="error"
          action={<Button onClick={auth.retry}>Tentar novamente</Button>}
        >
          Não foi possível confirmar sua sessão. Tente novamente antes de entrar
          ou criar uma conta.
        </Alert>
      ) : (
        <>
          {created && (
            <Alert severity="success">
              Conta criada. Entre para continuar. Em Equipamentos, você verá as
              opções de cadastro disponíveis neste ambiente.
            </Alert>
          )}
          <AuthForm
            key={registering ? 'register' : 'login'}
            registering={registering}
            submit={async ({ name, email, password }) => {
              if (registering) {
                await register(name, email, password);
                navigate('/login?registered=1');
              } else {
                const session = await login(email, password);
                await auth.replace(session);
                navigate(destination, { replace: true });
              }
            }}
          />
          <Divider sx={{ color: 'text.secondary', fontSize: 12 }}>
            {registering ? 'Já tem uma conta?' : 'ou'}
          </Divider>
          <Button
            component={Link}
            variant={registering ? 'text' : 'outlined'}
            to={registering ? '/login' : '/registrar'}
            sx={{ minHeight: 46 }}
          >
            {registering ? 'Fazer login' : 'Criar uma conta'}
          </Button>
        </>
      )}
    </Stack>
  );
}
