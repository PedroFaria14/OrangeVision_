import { useContext } from 'react';
import { AuthContext } from '../model/auth_context';

export function useSession() {
  const value = useContext(AuthContext);
  if (!value) throw new Error('SessionProvider ausente.');
  return value;
}
