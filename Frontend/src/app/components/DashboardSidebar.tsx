import { Box, Button, Divider, Link, Typography } from '@mui/material';
import { Link as RouterLink, useLocation } from 'react-router-dom';
import { Icon, type IconName } from '@/shared/ui/Icon';
import { NavigationSidebar } from './NavigationSidebar';
import { useInspectionConfig } from '@/features/inspection/hooks/useInspectionConfig';

const destinations: {
  to: string;
  label: string;
  icon: IconName;
}[] = [
  { to: '/dashboard', label: 'Início', icon: 'home' },
  { to: '/dashboard/historico', label: 'Análises', icon: 'analyses' },
  { to: '/dashboard/amostras', label: 'Amostras', icon: 'image' },
  { to: '/dashboard/dispositivos', label: 'Equipamentos', icon: 'device' },
  { to: '/dashboard/perfil', label: 'Perfil', icon: 'user' },
];

export function DashboardSidebar({
  close,
  logout,
  busy,
}: {
  close?: () => void;
  logout: () => void;
  busy: boolean;
}) {
  const { pathname } = useLocation();
  const inspection = useInspectionConfig();
  const items = inspection.data?.enabled
    ? [
        ...destinations,
        {
          to: '/dashboard/inspecoes',
          label: 'Inspeções',
          icon: 'device' as const,
        },
      ]
    : destinations;
  const activePath = pathname.startsWith('/dashboard/analises/')
    ? '/dashboard/historico'
    : pathname;
  return (
    <NavigationSidebar
      items={items}
      activePath={activePath}
      label="Navegação do dashboard"
      caption="ÁREA DE MONITORAMENTO"
      close={close}
      footer={
        <Box>
          <Box sx={{ px: 1.5, mb: 3 }}>
            <Typography sx={{ color: '#B9C7D2', fontSize: 12 }}>
              Cada análise, um registro.
            </Typography>
            <Typography
              sx={{ color: '#B8C5D0', fontSize: 12, mt: 0.75, lineHeight: 1.7 }}
            >
              Consulta segura dos seus dados
              <br />
              de inspeção visual externa.
            </Typography>
          </Box>
          <Divider sx={{ borderColor: '#FFFFFF12', mb: 2 }} />
          <Link
            component={RouterLink}
            to="/projeto"
            onClick={close}
            underline="none"
            sx={{
              display: 'block',
              px: 1.5,
              py: 1.5,
              color: '#B9C7D2',
              fontSize: 12,
              '&:hover': { color: 'white' },
            }}
          >
            Sobre o projeto{' '}
            <Box component="span" aria-hidden="true">
              ↗
            </Box>
          </Link>
          <Button
            startIcon={<Icon name="logout" />}
            disabled={busy}
            onClick={logout}
            sx={{
              color: '#E8EDF2 !important',
              justifyContent: 'flex-start',
              width: '100%',
              px: 1.5,
              mt: 0.5,
            }}
          >
            {busy ? 'Saindo…' : 'Sair da conta'}
          </Button>
        </Box>
      }
    />
  );
}
