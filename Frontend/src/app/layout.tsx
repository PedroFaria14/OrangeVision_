import { Alert, Button } from '@mui/material';
import { Outlet, useLocation } from 'react-router-dom';
import { pageTitle } from './navigation';
import { SiteFooter } from './components/SiteFooter';
import { SiteSidebar } from './components/SiteSidebar';
import { NavigationLayout } from './layouts/NavigationLayout';
import { useLogout } from '@/features/auth/hooks/useLogout';
export function Layout() {
  const { pathname } = useLocation();
  const { busy, failed, signOut } = useLogout();
  return (
    <NavigationLayout
      section={pageTitle(pathname)}
      sidebar={(close) => (
        <SiteSidebar close={close} logout={() => void signOut()} busy={busy} />
      )}
      footer={<SiteFooter />}
    >
      {failed && (
        <Alert severity="error" sx={{ mb: 3 }}>
          Dados locais removidos, mas não foi possível confirmar a revogação no
          servidor.{' '}
          <Button disabled={busy} onClick={() => void signOut()}>
            Tentar sair novamente
          </Button>
        </Alert>
      )}
      <Outlet />
    </NavigationLayout>
  );
}
