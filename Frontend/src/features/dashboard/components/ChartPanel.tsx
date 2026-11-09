import { Paper, Stack, Typography } from '@mui/material';
import type { ReactNode } from 'react';
export function ChartPanel({
  title,
  description,
  children,
}: {
  title: string;
  description: string;
  children: ReactNode;
}) {
  return (
    <Paper
      component="section"
      variant="outlined"
      sx={{ p: { xs: 2, md: 3 }, minWidth: 0 }}
    >
      <Stack spacing={2}>
        <Typography variant="h6" component="h2">
          {title}
        </Typography>
        <Typography variant="body2" color="text.secondary">
          {description}
        </Typography>
        {children}
      </Stack>
    </Paper>
  );
}
