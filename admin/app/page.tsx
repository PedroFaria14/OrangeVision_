import { redirect } from 'next/navigation';
import { isAdmin } from '../lib/auth';
import { StudioPanel } from './ui/studio-panel';
import { LogoutButton } from './ui/auth-buttons';

export const dynamic = 'force-dynamic';

export default async function AdminPage() {
  let authorized = false;
  try { authorized = await isAdmin(); } catch { /* falha fechada */ }
  if (!authorized) redirect('/login');
  return <div className="admin-shell">
    <a className="skip-link" href="#database">Pular para o banco de dados</a>
    <header className="admin-header">
      <div><p className="wordmark"><span aria-hidden="true">●</span> OrangeVision</p><h1>Banco de dados</h1></div>
      <div className="header-actions"><span className="read-badge">Somente leitura</span><LogoutButton /></div>
    </header>
    <main id="database" className="database-panel" aria-label="Prisma Studio">
      <StudioPanel />
    </main>
  </div>;
}
