export type AdminEnvironment = Record<string, string | undefined>;

export class ConfigurationError extends Error {
  constructor() {
    super('Configure as variáveis privadas do painel Prisma na Vercel.');
  }
}

export function authSettings(env: AdminEnvironment = process.env) {
  const {
    NEXTAUTH_URL,
    NEXTAUTH_SECRET,
    GITHUB_CLIENT_ID,
    GITHUB_CLIENT_SECRET,
    ADMIN_GITHUB_ID,
  } = env;
  if (
    !NEXTAUTH_URL ||
    !NEXTAUTH_SECRET ||
    NEXTAUTH_SECRET.length < 32 ||
    !GITHUB_CLIENT_ID ||
    !GITHUB_CLIENT_SECRET ||
    !ADMIN_GITHUB_ID ||
    !/^[1-9]\d*$/.test(ADMIN_GITHUB_ID)
  )
    throw new ConfigurationError();
  let url: URL;
  try {
    url = new URL(NEXTAUTH_URL);
  } catch {
    throw new ConfigurationError();
  }
  const local =
    !env.VERCEL && ['127.0.0.1', 'localhost'].includes(url.hostname);
  if (
    (url.protocol !== 'https:' && !(local && url.protocol === 'http:')) ||
    url.username ||
    url.password ||
    url.search ||
    url.hash ||
    url.pathname !== '/'
  ) {
    throw new ConfigurationError();
  }
  return {
    origin: url.origin,
    secret: NEXTAUTH_SECRET,
    clientId: GITHUB_CLIENT_ID,
    clientSecret: GITHUB_CLIENT_SECRET,
    githubId: ADMIN_GITHUB_ID,
  };
}

export function databaseUrl(env: AdminEnvironment = process.env) {
  const value = env.STUDIO_DATABASE_URL;
  if (!value) throw new ConfigurationError();
  let url: URL;
  try {
    url = new URL(value);
  } catch {
    throw new ConfigurationError();
  }
  if (!['postgres:', 'postgresql:'].includes(url.protocol))
    throw new ConfigurationError();
  const local =
    !env.VERCEL && ['127.0.0.1', 'localhost'].includes(url.hostname);
  if (
    !local &&
    !['require', 'verify-full'].includes(url.searchParams.get('sslmode') ?? '')
  ) {
    throw new ConfigurationError();
  }
  return value;
}
