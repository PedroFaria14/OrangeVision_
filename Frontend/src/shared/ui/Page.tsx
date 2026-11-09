import { Box, Stack, Typography } from '@mui/material';
import type { PropsWithChildren, ReactNode } from 'react';
export function Page({
  title,
  description,
  children,
  eyebrow,
  action,
  centered = false,
}: PropsWithChildren<{
  title: string;
  description?: string;
  eyebrow?: string;
  action?: ReactNode;
  centered?: boolean;
}>) {
  return (
    <Stack spacing={3}>
      <Stack
        direction={{ xs: 'column', sm: 'row' }}
        sx={{
          justifyContent: 'space-between',
          alignItems: { xs: 'flex-start', sm: 'center' },
          gap: 2,
        }}
      >
        <Box
          sx={{
            minWidth: 0,
            flex: 1,
            width: centered ? '100%' : undefined,
            textAlign: centered ? 'center' : 'left',
          }}
        >
          {eyebrow && (
            <Typography
              sx={{
                color: centered ? 'primary.dark' : 'text.secondary',
                fontSize: 12,
                letterSpacing: 1.8,
                fontWeight: centered ? 700 : 600,
                mb: 1,
              }}
            >
              {eyebrow}
            </Typography>
          )}
          <Typography
            component="h1"
            variant="h2"
            sx={{ letterSpacing: '-.8px', mb: 1, overflowWrap: 'anywhere' }}
          >
            {title}
          </Typography>
          {centered && (
            <Box
              aria-hidden="true"
              sx={{
                width: 55,
                height: 4,
                bgcolor: 'secondary.main',
                borderRadius: 2,
                mx: 'auto',
                my: 2,
              }}
            />
          )}
          {description && (
            <Typography
              color="text.secondary"
              sx={{
                maxWidth: centered ? 850 : 760,
                mx: centered ? 'auto' : 0,
                overflowWrap: 'anywhere',
                lineHeight: centered ? 1.8 : undefined,
              }}
            >
              {description}
            </Typography>
          )}
        </Box>
        {action}
      </Stack>
      {children}
    </Stack>
  );
}
