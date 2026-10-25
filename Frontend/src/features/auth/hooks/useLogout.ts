import { useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { ApiError } from '@/shared/api/client';
import { logout } from '../api/session';
import { useSession } from './useSession';

export function useLogout() {
  const auth = useSession();
  const client = useQueryClient();
  const [busy, setBusy] = useState(false);
  const [failed, setFailed] = useState(false);
  async function signOut() {
    if (!auth.session || busy) return;
    setBusy(true);
    setFailed(false);
    try {
      await logout(auth.session.csrf_token);
      await auth.replace(null);
    } catch (error) {
      if (error instanceof ApiError && error.status === 401)
        await auth.replace(null);
      else {
        await client.cancelQueries({ queryKey: ['private'] });
        client.removeQueries({ queryKey: ['private'] });
        setFailed(true);
      }
    } finally {
      setBusy(false);
    }
  }
  return { busy, failed, signOut };
}
