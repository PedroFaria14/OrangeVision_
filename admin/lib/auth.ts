import { getServerSession, type NextAuthOptions } from 'next-auth';
import GitHubProvider from 'next-auth/providers/github';
import { authSettings } from './settings';

export function authOptions(): NextAuthOptions {
  const settings = authSettings();
  return {
    secret: settings.secret,
    providers: [GitHubProvider({
      clientId: settings.clientId, clientSecret: settings.clientSecret,
      checks: ['pkce', 'state'],
    })],
    session: { strategy: 'jwt', maxAge: 60 * 60 },
    jwt: { maxAge: 60 * 60 },
    useSecureCookies: settings.origin.startsWith('https://'),
    pages: { signIn: '/login', error: '/login' },
    callbacks: {
      async signIn({ account, profile }) {
        const id = profile && 'id' in profile ? String(profile.id) : '';
        return account?.provider === 'github' && id === settings.githubId;
      },
      async jwt({ token, account }) {
        if (account) {
          token.githubId = account.providerAccountId;
          token.provider = account.provider;
        }
        return token;
      },
      async session({ session, token }) {
        // Revalida a allowlist: trocar o ID no ambiente invalida o acesso anterior.
        session.user = token.provider === 'github' && token.githubId === settings.githubId
          ? { id: settings.githubId, name: 'Administrador' }
          : undefined;
        return session;
      },
      async redirect({ url }) {
        try {
          const target = new URL(url, settings.origin);
          if (target.origin === settings.origin) return target.href;
        } catch { /* destino inválido retorna para a origem confiável */ }
        return settings.origin;
      },
    },
    logger: {
      // Os metadados do provedor podem conter credenciais; registre apenas o código.
      error(code) { console.error('admin_auth_error', code); },
      warn(code) { console.warn('admin_auth_warning', code); },
      debug() {},
    },
  };
}

export async function isAdmin() {
  const session = await getServerSession(authOptions());
  return session?.user?.id === authSettings().githubId;
}
