import { Box, Button, Divider, Stack, Typography } from '@mui/material';
import { Link, useLocation } from 'react-router-dom';
import { useSession } from '@/features/auth/hooks/useSession';
import { Icon, type IconName } from '@/shared/ui/Icon';
import { navigation } from '../navigation';
import { NavigationSidebar } from './NavigationSidebar';

const icons: Record<string, IconName> = {
  '/': 'home',
  '/projeto': 'info',
  '/planejamento': 'calendar',
  '/desenvolvimento': 'device',
  '/dashboard': 'analyses',
  '/resultados': 'check',
  '/equipe': 'user',
  '/referencias': 'analyses',
};

export function SiteSidebar({
  close,
  logout,
  busy,
}: {
  close: () => void;
  logout: () => void;
  busy: boolean;
}) {
  const { pathname } = useLocation();
  const { session, pending } = useSession();
  const footer = (
    <Stack spacing={1}>
      <Divider sx={{ borderColor: '#FFFFFF12', mb: 1 }} />
      {pending ? (
        <Typography
          role="status"
          sx={{ color: '#B9C7D2', fontSize: 12, px: 1 }}
        >
          Consultando sessão…
        </Typography>
      ) : session ? (
        <>
          <Box sx={{ px: 1, pb: 1 }}>
            <Typography sx={{ color: '#B8C5D0', fontSize: 12 }}>
              Conectado como
            </Typography>
            <Typography
              sx={{
                color: '#E8EDF2',
                fontSize: 13,
                mt: 0.5,
                overflowWrap: 'anywhere',
              }}
            >
              {session.user.name}
            </Typography>
          </Box>
          <Button
            component={Link}
            to="/dashboard"
            onClick={close}
            variant="contained"
            endIcon={<Icon name="arrow" sx={{ fontSize: 17 }} />}
          >
            Meu dashboard
          </Button>
          <Button
            onClick={logout}
            disabled={busy}
            startIcon={<Icon name="logout" />}
            sx={{ color: '#E8EDF2 !important', justifyContent: 'flex-start' }}
          >
            {busy ? 'Saindo…' : 'Sair da conta'}
          </Button>
        </>
      ) : (
        <>
          <Button
            component={Link}
            to="/login"
            onClick={close}
            variant="contained"
            aria-label="Entrar na sua conta"
            endIcon={<Icon name="arrow" sx={{ fontSize: 17 }} />}
          >
            Entrar
          </Button>
          <Button
            component={Link}
            to="/registrar"
            onClick={close}
            sx={{ color: '#D3DDE6 !important' }}
          >
            Criar uma conta
          </Button>
        </>
      )}
    </Stack>
  );
  return (
    <NavigationSidebar
      items={navigation.map(([to, label]) => ({ to, label, icon: icons[to] }))}
      activePath={pathname}
      label="Navegação principal"
      caption="CONHEÇA O ORANGEVISION"
      footer={footer}
      close={close}
    />
  );
}
