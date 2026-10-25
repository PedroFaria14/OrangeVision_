import { createContext } from 'react';
import type { Session } from '../api/session';

export type AuthState = {
  session: Session | null | undefined;
  pending: boolean;
  error: boolean;
  retry: () => void;
  replace: (value: Session | null) => Promise<void>;
};
export const AuthContext = createContext<AuthState | null>(null);
