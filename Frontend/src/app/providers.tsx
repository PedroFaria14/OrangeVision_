import { QueryClientProvider } from '@tanstack/react-query';
import { RouterProvider } from 'react-router-dom';
import { SessionProvider } from '@/features/auth/components/SessionProvider';
import { queryClient } from './query-client';
import { router } from './router';
import { env } from './config/env';

export function AppProviders() {
  return (
    <QueryClientProvider client={queryClient}>
      <SessionProvider enabled={env.enabled}>
        <RouterProvider router={router} />
      </SessionProvider>
    </QueryClientProvider>
  );
}
