import { Auth, type AuthConfig } from '@auth/core';
import GitHub from '@auth/core/providers/github';
import {
  authSettings,
  ConfigurationError,
  type AdminEnvironment,
} from './settings.js';
import { limitedBody, privateHeaders } from './http.js';

export const ADMIN_AUTH_PATH = '/api/admin/auth';
export const ADMIN_PAGE_PATH = '/admin/prisma';

export function adminAuthConfig(
  env: AdminEnvironment = process.env,
): AuthConfig {
  const settings = authSettings(env);
  const secure = settings.origin.startsWith('https://');
  const prefix = secure ? '__Secure-' : '';
  const cookie = (name: string, path: string) => ({
    name: `${prefix}orangevision_admin_${name}`,
    options: { httpOnly: true, sameSite: 'lax' as const, secure, path },
  });
  return {
    basePath: ADMIN_AUTH_PATH,
    trustHost: true, // O request é reconstruído abaixo com a origem fixa da configuração.
    secret: settings.secret,
    providers: [
      GitHub({
        clientId: settings.clientId,
        clientSecret: settings.clientSecret,
        checks: ['pkce', 'state'],
      }),
    ],
    session: { strategy: 'jwt', maxAge: 3600 },
    jwt: { maxAge: 3600 },
    useSecureCookies: secure,
    cookies: {
      sessionToken: cookie('session', '/api/admin'),
      csrfToken: cookie('csrf', ADMIN_AUTH_PATH),
      pkceCodeVerifier: cookie('pkce', ADMIN_AUTH_PATH),
      state: cookie('state', ADMIN_AUTH_PATH),
      nonce: cookie('nonce', ADMIN_AUTH_PATH),
      callbackUrl: cookie('callback', ADMIN_AUTH_PATH),
    },
    pages: {
      signIn: `${settings.origin}${ADMIN_PAGE_PATH}`,
      error: `${settings.origin}${ADMIN_PAGE_PATH}`,
    },
    callbacks: {
      async signIn({ account, profile }) {
        return (
          account?.provider === 'github' &&
          String(profile?.id ?? '') === settings.githubId
        );
      },
      async jwt({ token, account }) {
        if (account) {
          token.githubId = account.providerAccountId;
          token.provider = account.provider;
        }
        return token;
      },
      async session({ session, token }) {
        return {
          ...session,
          user:
            token.provider === 'github' && token.githubId === settings.githubId
              ? { id: settings.githubId, name: 'Administrador' }
              : undefined,
        };
      },
      async redirect({ url }) {
        try {
          const target = new URL(url, settings.origin);
          if (
            target.origin === settings.origin &&
            target.pathname === ADMIN_PAGE_PATH
          )
            return target.href;
        } catch {
          /* destino inválido usa a página administrativa */
        }
        return `${settings.origin}${ADMIN_PAGE_PATH}`;
      },
    },
    logger: {
      error(error) {
        console.error('admin_auth_error', error.name);
      },
      warn(code) {
        console.warn('admin_auth_warning', code);
      },
      debug() {},
    },
  };
}

export async function handleAdminAuth(
  request: Request,
  env: AdminEnvironment = process.env,
) {
  try {
    const settings = authSettings(env);
    const incoming = new URL(request.url);
    const rewritten = incoming.pathname === ADMIN_AUTH_PATH;
    if (!rewritten && !incoming.pathname.startsWith(`${ADMIN_AUTH_PATH}/`)) {
      return Response.json(
        { detail: 'Rota administrativa inválida.' },
        { status: 404, headers: privateHeaders },
      );
    }
    if (rewritten && incoming.searchParams.getAll('__path').length !== 1) {
      return Response.json(
        { detail: 'Rota administrativa inválida.' },
        { status: 404, headers: privateHeaders },
      );
    }
    // __path é preenchido pelo rewrite Vercel; em Vite a URL original já contém a ação.
    const action = rewritten
      ? (incoming.searchParams.get('__path') ?? '')
      : incoming.pathname.slice(`${ADMIN_AUTH_PATH}/`.length);
    if (
      !/^(session|csrf|providers|error|signout|signin(?:\/github)?|callback\/github)$/.test(
        action,
      )
    ) {
      return Response.json(
        { detail: 'Rota administrativa inválida.' },
        { status: 404, headers: privateHeaders },
      );
    }
    if (!['GET', 'POST'].includes(request.method)) {
      return Response.json(
        { detail: 'Método não permitido.' },
        { status: 405, headers: privateHeaders },
      );
    }
    if (
      request.method === 'POST' &&
      request.headers.get('origin') !== settings.origin
    ) {
      return Response.json(
        { detail: 'Origem não permitida.' },
        { status: 403, headers: privateHeaders },
      );
    }
    const body =
      request.method === 'POST' ? await limitedBody(request) : undefined;
    if (body === null)
      return Response.json(
        { detail: 'Request acima de 64 KiB.' },
        { status: 413, headers: privateHeaders },
      );
    const target = new URL(`${ADMIN_AUTH_PATH}/${action}`, settings.origin);
    for (const [key, value] of incoming.searchParams) {
      if (key !== '__path') target.searchParams.append(key, value);
    }
    const canonical = new Request(target, {
      method: request.method,
      headers: request.headers,
      body,
    });
    const response = await Auth(canonical, adminAuthConfig(env));
    // Response.redirect usa headers imutáveis; preserve redirects e todos os Set-Cookie.
    const headers = new Headers(response.headers);
    for (const [key, value] of Object.entries(privateHeaders))
      headers.set(key, value);
    return new Response(response.body, { status: response.status, headers });
  } catch (error) {
    return Response.json(
      {
        detail:
          error instanceof ConfigurationError
            ? error.message
            : 'Autenticação administrativa indisponível.',
      },
      { status: 503, headers: privateHeaders },
    );
  }
}

export async function isAdmin(
  request: Request,
  env: AdminEnvironment = process.env,
) {
  const settings = authSettings(env);
  const response = await Auth(
    new Request(`${settings.origin}${ADMIN_AUTH_PATH}/session`, {
      headers: { cookie: request.headers.get('cookie') ?? '' },
    }),
    adminAuthConfig(env),
  );
  const session: unknown = await response.json();
  if (!session || typeof session !== 'object' || !('user' in session))
    return false;
  const user: unknown = session.user;
  return (
    !!user &&
    typeof user === 'object' &&
    'id' in user &&
    user.id === settings.githubId
  );
}
