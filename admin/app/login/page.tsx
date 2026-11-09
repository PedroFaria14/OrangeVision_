import { authSettings } from '../../lib/settings';
import { LoginButton } from '../ui/auth-buttons';

export const dynamic = 'force-dynamic';

export default async function LoginPage({ searchParams }: {
  searchParams: Promise<{ error?: string }>;
}) {
  let configured = true;
  try { authSettings(); } catch { configured = false; }
  const { error } = await searchParams;
  return <main className="login-page">
    <section className="login-panel" aria-labelledby="login-title">
      <p className="wordmark"><span aria-hidden="true">●</span> OrangeVision</p>
      <p className="eyebrow">ACESSO ADMINISTRATIVO</p>
      <h1 id="login-title">Seu banco,<br />em uma visão.</h1>
      <p className="intro">Consulte tabelas e explore os dados do OrangeVision com Prisma Studio.</p>
      <p className="read-badge">Somente leitura · Neon PostgreSQL</p>
      {!configured ? <p role="status" className="notice">O painel está instalado. Configure as variáveis privadas de autenticação na Vercel para liberar o login.</p>
        : <>
          {error && <p role="alert" className="notice">Não foi possível autorizar o acesso. Use a conta GitHub cadastrada pelo administrador e tente novamente.</p>}
          <LoginButton />
        </>}
      <p className="footnote">Acesso restrito à conta GitHub autorizada. As credenciais do banco permanecem no servidor.</p>
    </section>
  </main>;
}
