import { useEffect, type ReactNode } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { readSession, type Session } from '../api/session';

import { AuthContext } from '../model/auth_context';

export function SessionProvider({
  children,
  enabled = true,
}: {
  children: ReactNode;
  enabled?: boolean;
}) {
  const client = useQueryClient();
  const query = useQuery({
    queryKey: ['session'],
    queryFn: ({ signal }) =>
      enabled ? readSession(signal) : Promise.resolve(null),
    retry: false,
    staleTime: 0,
    refetchOnWindowFocus: true,
    refetchInterval: 60_000,
    refetchIntervalInBackground: false,
  });

  async function replace(value: Session | null) {
    // Cancelamento aguardado antes de remover cache: respostas antigas não repovoam a conta nova.
    await client.cancelQueries();
    client.removeQueries({ predicate: (q) => q.queryKey[0] === 'private' });
    client.setQueryData(['session'], value);
  }

  useEffect(() => {
    const expired = () => {
      void client.cancelQueries().then(() => {
        client.removeQueries({ predicate: (q) => q.queryKey[0] === 'private' });
        client.setQueryData(['session'], null);
      });
    };
    window.addEventListener('orangevision:session-expired', expired);
    return () =>
      window.removeEventListener('orangevision:session-expired', expired);
  }, [client]);

  useEffect(() => {
    if (query.data === null || query.isError) {
      void client
        .cancelQueries({ queryKey: ['private'] })
        .then(() => client.removeQueries({ queryKey: ['private'] }));
    }
  }, [client, query.data, query.isError]);

  return (
    <AuthContext.Provider
      value={{
        session: query.isError ? undefined : query.data,
        pending: query.isPending,
        error: query.isError,
        retry: () => {
          void query.refetch();
        },
        replace,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}
