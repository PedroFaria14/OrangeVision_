import { Alert, Button } from '@mui/material';
import { Outlet, useLocation } from 'react-router-dom';
import { useLogout } from '@/features/auth/hooks/useLogout';
import { DashboardSidebar } from '../components/DashboardSidebar';
import { NavigationLayout } from './NavigationLayout';

export function PrivateLayout() {
  const { busy, failed, signOut } = useLogout();
  const { pathname } = useLocation();
  const section = pathname.includes('/dispositivos')
    ? 'Equipamentos'
    : pathname.includes('/amostras')
      ? 'Amostras'
      : pathname.includes('/inspecoes')
        ? 'Inspeções'
        : pathname.includes('/historico')
          ? 'Análises'
          : pathname.includes('/analises/')
            ? 'Detalhe da análise'
            : pathname.includes('/perfil')
              ? 'Meu perfil'
              : 'Visão geral';
  return (
    <NavigationLayout
      section={section}
      sidebar={(close) => (
        <DashboardSidebar
          close={close}
          logout={() => void signOut()}
          busy={busy}
        />
      )}
    >
      {failed ? (
        <Alert severity="error">
          Dados locais removidos, mas não foi possível confirmar a revogação no
          servidor.{' '}
          <Button disabled={busy} onClick={() => void signOut()}>
            Tentar sair novamente
          </Button>
        </Alert>
      ) : (
        <Outlet />
      )}
    </NavigationLayout>
  );
}
