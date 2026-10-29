import {
  Link,
  NavLink,
  Navigate,
  Outlet,
  useLocation,
  useRouteError,
} from 'react-router-dom';
import { lazy, Suspense } from 'react';
import { useSession } from '@/features/auth/hooks/useSession';
import { useLogout } from '@/features/auth/hooks/useLogout';
import styles from '@/shared/ui/public.module.css';

const DashboardShell = lazy(() => import('./DashboardShell'));

export function Layout() {
  const { pathname } = useLocation();
  return pathname === '/dashboard' || pathname.startsWith('/dashboard/') ? (
    <Outlet />
  ) : (
    <PublicLayout />
  );
}

function PublicLayout() {
  const auth = useSession();
  const logout = useLogout();
  return (
    <div className={styles.shell}>
      <>
        <a href="#conteudo">Pular para o conteúdo</a>
        <header className={styles.sidebar}>
          <p className={styles.brand}>
            <Link to="/">OrangeVision</Link>
          </p>
          {auth.session && (
            <p>
              Conta: {auth.session.user.name} ·{' '}
              <Link to="/dashboard/perfil">Meu perfil</Link>
            </p>
          )}
          <nav aria-label="Navegação principal">
            <ul>
              {[
                ['/', 'Início'],
                ['/projeto', 'O Projeto'],
                ['/planejamento', 'Planejamento'],
                ['/desenvolvimento', 'Desenvolvimento'],
                ['/resultados', 'Resultados'],
                ['/equipe', 'Equipe'],
                ['/referencias', 'Referências'],
              ].map(([to, label]) => (
                <li key={to}>
                  <NavLink to={to} end>
                    {label}
                  </NavLink>
                </li>
              ))}
              {auth.session ? (
                <>
                  <li>
                    <Link to="/dashboard">Dashboard</Link>
                  </li>
                  <li>
                    <Link to="/dashboard/historico">Histórico</Link>
                  </li>
                  <li>
                    <Link to="/dashboard/inspecoes">Inspeções</Link>
                  </li>
                  <li>
                    <Link to="/dashboard/amostras">Amostras</Link>
                  </li>
                  <li>
                    <button
                      type="button"
                      disabled={logout.busy}
                      onClick={() => void logout.signOut()}
                    >
                      Sair da conta
                    </button>
                  </li>
                </>
              ) : (
                <>
                  <li>
                    <Link to="/login">Entrar</Link>
                  </li>
                  <li>
                    <Link to="/registrar">Criar conta</Link>
                  </li>
                </>
              )}
            </ul>
          </nav>
        </header>
        <div className={styles.topbar}>
          <span>OrangeVision</span>
          <Link to="/login">Entrar</Link>
        </div>
        <main id="conteudo" tabIndex={-1}>
          {logout.failed ? (
            <div role="alert">
              <p>
                Conteúdo privado ocultado, mas não foi possível confirmar o
                encerramento da sessão no servidor.
              </p>
              <button
                disabled={logout.busy}
                onClick={() => void logout.signOut()}
              >
                Tentar sair novamente
              </button>
            </div>
          ) : (
            <Outlet />
          )}
        </main>
        <footer>
          <p>OrangeVision · Protótipo acadêmico de inspeção visual externa.</p>
        </footer>
      </>
    </div>
  );
}

export function ProtectedLayout() {
  const auth = useSession();
  const location = useLocation();
  if (auth.pending) return <p role="status">Consultando sessão…</p>;
  if (auth.error)
    return (
      <div role="alert">
        <p>Não foi possível validar a sessão.</p>
        <button onClick={auth.retry}>Tentar novamente</button>
      </div>
    );
  if (!auth.session)
    return (
      <Navigate
        to={`/login?next=${encodeURIComponent(location.pathname + location.search)}`}
        replace
      />
    );
  return (
    <Suspense fallback={<p role="status">Carregando área de trabalho…</p>}>
      <DashboardShell />
    </Suspense>
  );
}

export function RouteError() {
  useRouteError();
  return (
    <main>
      <h1>Não foi possível abrir esta página</h1>
      <p role="alert">A operação não foi concluída.</p>
      <Link to="/">Voltar ao início</Link>
    </main>
  );
}
