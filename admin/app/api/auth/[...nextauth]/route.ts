import NextAuth from 'next-auth';
import { authOptions } from '../../../../lib/auth';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

async function handler(request: Request, context: { params: Promise<{ nextauth: string[] }> }) {
  try {
    return await NextAuth(authOptions())(request, { params: await context.params });
  } catch {
    return Response.json({ error: 'Configure o login administrativo no servidor.' }, {
      status: 503, headers: { 'Cache-Control': 'no-store' },
    });
  }
}

export { handler as GET, handler as POST };
