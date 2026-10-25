import { useRef, useState } from 'react';
import { Link, NavLink, Outlet } from 'react-router-dom';
import { useSession } from '@/features/auth/hooks/useSession';
import { useLogout } from '@/features/auth/hooks/useLogout';
import { useInspectionConfig } from '@/features/inspection/hooks/useInspectionConfig';
import styles from '@/shared/ui/dashboard.module.css';

const links = [
  ['/dashboard', 'Dashboard', '▦'],
  ['/dashboard/historico', 'Histórico', '≡'],
  ['/dashboard/inspecoes', 'Inspeções', '◎'],
  ['/dashboard/amostras', 'Amostras', '▧'],
  ['/dashboard/perfil', 'Meu perfil', '○'],
] as const;

export default function DashboardShell() {
  const auth = useSession();
  const logout = useLogout();
  const inspection = useInspectionConfig();
  const [menuOpen, setMenuOpen] = useState(false);
  const menuButton = useRef<HTMLButtonElement>(null);
  const name = auth.session?.user.name || 'Sua conta';

  return (
    <div
      className={styles.shell}
      data-dashboard-shell
      onKeyDown={(event) => {
        if (event.key === 'Escape' && menuOpen) {
          setMenuOpen(false);
          menuButton.current?.focus();
        }
      }}
    >
      <a className={styles.skip} href="#conteudo">
        Pular para o conteúdo
      </a>
      <aside className={styles.sidebar} data-open={menuOpen}>
        <Link className={styles.brand} to="/">
          <span className={styles.brandMark} aria-hidden="true">
            O
          </span>
          <span>
            Orange<span className={styles.brandAccent}>Vision</span>
            <small>INSPEÇÃO VISUAL</small>
          </span>
        </Link>
        <p className={styles.navLabel}>ÁREA DE TRABALHO</p>
        <nav id="dashboard-navigation" aria-label="Navegação da área logada">
          {links
            .filter(
              ([to]) =>
                to !== '/dashboard/inspecoes' || inspection.data?.enabled,
            )
            .map(([to, label, icon]) => (
              <NavLink
                key={to}
                to={to}
                end={to === '/dashboard'}
                onClick={() => setMenuOpen(false)}
              >
                <span className={styles.navIcon} aria-hidden="true">
                  {icon}
                </span>
                {label}
              </NavLink>
            ))}
        </nav>
        <div className={styles.sidebarBottom}>
          <Link to="/" onClick={() => setMenuOpen(false)}>
            ← Voltar ao site
          </Link>
          <p>
            Projeto acadêmico
            <br />
            Inspeção visual externa
          </p>
        </div>
      </aside>
      <header className={styles.topbar}>
        <button
          ref={menuButton}
          className={styles.menuToggle}
          type="button"
          aria-expanded={menuOpen}
          aria-controls="dashboard-navigation"
          onClick={() => setMenuOpen(!menuOpen)}
        >
          {menuOpen ? 'Fechar menu' : 'Abrir menu'}
        </button>
        <span className={styles.workspaceLabel}>Painel de inspeção</span>
        <div className={styles.account}>
          <span className={styles.avatar} aria-hidden="true">
            {name.slice(0, 1).toLocaleUpperCase('pt-BR')}
          </span>
          <Link to="/dashboard/perfil">
            {name}
            <small>Minha conta</small>
          </Link>
          <button
            type="button"
            disabled={logout.busy}
            onClick={() => void logout.signOut()}
          >
            Sair da conta
          </button>
        </div>
      </header>
      <div className={styles.workspace}>
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
        <footer className={styles.footer}>
          OrangeVision · Protótipo acadêmico. Classificação experimental de
          características externas.
        </footer>
      </div>
    </div>
  );
}
