import { Box, Button, Stack, Typography } from '@mui/material';
import { Link } from 'react-router-dom';
import type { ReactNode } from 'react';
import { Brand } from '@/shared/ui/Brand';
import { Icon, type IconName } from '@/shared/ui/Icon';

export type NavigationItem = { to: string; label: string; icon: IconName };
type Props = {
  items: NavigationItem[];
  activePath: string;
  label: string;
  caption: string;
  footer: ReactNode;
  close?: () => void;
};

export function NavigationSidebar({
  items,
  activePath,
  label,
  caption,
  footer,
  close,
}: Props) {
  return (
    <Stack
      sx={{
        height: '100%',
        minHeight: 0,
        overflowY: 'auto',
        bgcolor: '#16212B',
        color: '#E8EDF2',
        p: 2.5,
      }}
    >
      <Box sx={{ px: 0.5, pt: 1, mb: 4 }}>
        <Brand light />
      </Box>
      <Typography
        sx={{
          px: 1.5,
          color: '#91A1AF',
          fontSize: 12,
          fontWeight: 600,
          letterSpacing: 1.6,
          mb: 2,
        }}
      >
        {caption}
      </Typography>
      <Stack component="nav" aria-label={label} spacing={1}>
        {items.map((item) => (
          <Button
            key={item.to}
            component={Link}
            to={item.to}
            className={activePath === item.to ? 'active' : undefined}
            aria-current={activePath === item.to ? 'page' : undefined}
            onClick={close}
            startIcon={<Icon name={item.icon} sx={{ fontSize: 20 }} />}
            sx={{
              minHeight: 48,
              justifyContent: 'flex-start',
              px: 2,
              color: '#D3DDE6 !important',
              fontWeight: 450,
              borderRadius: 2,
              '&:hover': { bgcolor: '#FFFFFF0B' },
              '&.active': {
                bgcolor: '#F97316',
                color: '#111827 !important',
                fontWeight: 650,
                '&:hover': { bgcolor: '#FB8C38' },
              },
            }}
          >
            {item.label}
          </Button>
        ))}
      </Stack>
      <Box sx={{ mt: 'auto', pt: 4 }}>{footer}</Box>
    </Stack>
  );
}
