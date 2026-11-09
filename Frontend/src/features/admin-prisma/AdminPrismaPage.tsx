import { useState } from 'react';
import { Link as RouterLink, useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Container,
  Paper,
  Stack,
  Typography,
} from '@mui/material';

const authPath = '/api/admin/auth';

async function loadSession() {
  const response = await fetch(`${authPath}/session`, {
    cache: 'no-store',
    credentials: 'same-origin',
  });
  if (response.status === 503)
    return { authenticated: false, unconfigured: true };
  if (!response.ok)
    throw new Error('Não foi possível confirmar a sessão administrativa.');
  const value: unknown = await response.json();
  const user =
    value && typeof value === 'object' && 'user' in value ? value.user : null;
  const authenticated =
    !!user &&
    typeof user === 'object' &&
    'id' in user &&
    typeof user.id === 'string' &&
    !!user.id;
  return { authenticated, unconfigured: false };
}

async function submitAuth(action: 'signin/github' | 'signout') {
  const response = await fetch(`${authPath}/csrf`, {
    cache: 'no-store',
    credentials: 'same-origin',
  });
  const value: unknown = await response.json();
  if (
    !response.ok ||
    !value ||
    typeof value !== 'object' ||
    !('csrfToken' in value) ||
    typeof value.csrfToken !== 'string'
  ) {
    throw new Error('Não foi possível iniciar a autenticação.');
  }
  // POST nativo mantém a navegação OAuth e o CSRF sob o controle do Auth.js.
  const form = document.createElement('form');
  form.method = 'POST';
  form.action = `${authPath}/${action}`;
  for (const [name, inputValue] of Object.entries({
    csrfToken: value.csrfToken,
    callbackUrl: `${location.origin}/admin/prisma`,
  })) {
    const input = document.createElement('input');
    input.type = 'hidden';
    input.name = name;
    input.value = inputValue;
    form.append(input);
  }
  document.body.append(form);
  form.submit();
}

export default function AdminPrismaPage() {
  const [params] = useSearchParams();
  const [pending, setPending] = useState(false);
  const [error, setError] = useState(false);
  const session = useQuery({
    queryKey: ['admin-prisma-session'],
    queryFn: loadSession,
    retry: false,
    staleTime: 0,
    refetchInterval: 30000,
  });
  const authenticate = async (action: 'signin/github' | 'signout') => {
    setPending(true);
    setError(false);
    try {
      await submitAuth(action);
    } catch {
      setError(true);
      setPending(false);
    }
  };
  const authenticated =
    !session.isError && session.data?.authenticated === true;
  return (
    <Box sx={{ minHeight: '100dvh', display: 'flex', flexDirection: 'column' }}>
      <title>Prisma Studio · OrangeVision</title>
      <meta name="robots" content="noindex, nofollow" />
      <Paper
        component="header"
        square
        elevation={0}
        sx={{ borderBottom: 1, borderColor: 'divider', p: 2 }}
      >
        <Stack
          direction="row"
          sx={{
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: 2,
            flexWrap: 'wrap',
          }}
        >
          <Stack direction="row" sx={{ alignItems: 'center', gap: 2 }}>
            <Button component={RouterLink} to="/" variant="text">
              Voltar ao OrangeVision
            </Button>
            <Typography component="h1" variant="h6">
              Prisma Studio
            </Typography>
          </Stack>
          <Stack direction="row" sx={{ alignItems: 'center', gap: 2 }}>
            <Chip label="Somente leitura" color="success" variant="outlined" />
            {authenticated && (
              <Button
                variant="outlined"
                disabled={pending}
                onClick={() => void authenticate('signout')}
              >
                Sair do painel
              </Button>
            )}
          </Stack>
        </Stack>
      </Paper>
      {authenticated ? (
        <Box component="main" sx={{ flex: 1, display: 'flex', minHeight: 520 }}>
          <iframe
            title="Prisma Studio — banco de dados"
            src="/admin-prisma.html"
            style={{
              width: '100%',
              height: 'calc(100dvh - 90px)',
              minHeight: 520,
              border: 0,
            }}
          />
        </Box>
      ) : (
        <Container component="main" maxWidth="sm" sx={{ py: { xs: 4, md: 8 } }}>
          <Paper variant="outlined" sx={{ p: { xs: 3, md: 4 } }}>
            <Stack sx={{ gap: 3 }}>
              <Typography variant="overline" color="text.secondary">
                ÁREA ADMINISTRATIVA
              </Typography>
              <Typography component="h2" variant="h3">
                Visualize o banco do OrangeVision
              </Typography>
              <Typography color="text.secondary">
                Entre com a conta GitHub autorizada para consultar as tabelas do
                Neon. O acesso é independente do login de usuários do site.
              </Typography>
              {session.isPending ? (
                <Stack
                  direction="row"
                  sx={{ gap: 2, alignItems: 'center' }}
                  role="status"
                >
                  <CircularProgress size={22} />
                  <Typography>Confirmando acesso administrativo…</Typography>
                </Stack>
              ) : session.data?.unconfigured ? (
                <Alert severity="info">
                  A rota do Prisma está instalada. Configure NEXTAUTH_URL,
                  NEXTAUTH_SECRET, GITHUB_CLIENT_ID, GITHUB_CLIENT_SECRET,
                  ADMIN_GITHUB_ID e STUDIO_DATABASE_URL nas variáveis privadas
                  deste projeto Vercel e faça um novo deploy.
                </Alert>
              ) : session.isError ? (
                <Alert
                  severity="error"
                  action={
                    <Button onClick={() => void session.refetch()}>
                      Tentar novamente
                    </Button>
                  }
                >
                  Não foi possível confirmar o acesso administrativo.
                </Alert>
              ) : (
                <Button
                  variant="contained"
                  disabled={pending}
                  onClick={() => void authenticate('signin/github')}
                >
                  {pending ? 'Abrindo autenticação…' : 'Entrar com GitHub'}
                </Button>
              )}
              {(error || params.has('error')) && (
                <Alert severity="error">
                  Não foi possível autorizar o acesso. Use a conta GitHub
                  configurada pelo administrador e tente novamente.
                </Alert>
              )}
              <Typography variant="body2" color="text.secondary">
                As credenciais do banco permanecem no servidor. O painel não
                permite alterações nos dados.
              </Typography>
            </Stack>
          </Paper>
        </Container>
      )}
      {authenticated && error && (
        <Alert severity="error">
          Não foi possível encerrar a sessão. Tente novamente.
        </Alert>
      )}
    </Box>
  );
}
