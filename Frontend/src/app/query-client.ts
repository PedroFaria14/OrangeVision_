import { QueryClient } from '@tanstack/react-query';
import { ApiError } from '@/shared/api/client';
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      refetchOnWindowFocus: false,
      retry: (count, error) =>
        count < 1 &&
        ((error instanceof ApiError && error.status >= 500) ||
          error instanceof TypeError ||
          (error instanceof DOMException && error.name === 'TimeoutError')),
    },
  },
});
