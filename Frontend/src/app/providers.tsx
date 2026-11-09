import { ThemeProvider, CssBaseline } from '@mui/material';
import { QueryClientProvider } from '@tanstack/react-query';
import { RouterProvider } from 'react-router-dom';
import { theme } from '@/shared/theme/theme';
import { queryClient } from './query-client';
import { router } from './router';
import { SessionProvider } from '@/features/auth/components/SessionProvider';
import { env } from './config/env';
export function AppProviders() {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <QueryClientProvider client={queryClient}>
        <SessionProvider enabled={env.enabled}>
          <RouterProvider router={router} />
        </SessionProvider>
      </QueryClientProvider>
    </ThemeProvider>
  );
}
