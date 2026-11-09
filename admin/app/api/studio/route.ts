import { isAdmin } from '../../../lib/auth';
import { authSettings } from '../../../lib/settings';
import { executeReadOnly } from '../../../lib/database';
import { handleStudio } from '../../../lib/studio-handler';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';
export const maxDuration = 20;

export async function POST(request: Request) {
  return handleStudio(request, {
    authorize: isAdmin,
    origin: () => authSettings().origin,
    execute: executeReadOnly,
  });
}
