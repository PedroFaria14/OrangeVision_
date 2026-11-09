import { Box, Button, Typography } from '@mui/material';
import { Link, Outlet, useLocation } from 'react-router-dom';
import { AuthVisual } from '@/features/auth/components/AuthVisual';
import { Icon } from '@/shared/ui/Icon';
import { SkipLink } from '@/shared/ui/SkipLink';
import { usePageFocus } from '../hooks/usePageFocus';
import { RenderApiStatus } from '@/features/service-status/RenderApiStatus';

export function AuthLayout() {
  const main = usePageFocus();
  const registering = useLocation().pathname === '/registrar';
  return (
    <Box
      sx={{
        minHeight: '100dvh',
        bgcolor: '#F3F6F8',
        display: 'flex',
        flexDirection: 'column',
        p: { xs: 2, sm: 3, md: 4 },
        '@media (max-height: 800px)': { py: 2 },
      }}
    >
      <SkipLink />
      <Button
        component={Link}
        to="/"
        startIcon={<Icon name="back" />}
        sx={{
          alignSelf: 'flex-start',
          mb: { xs: 2, md: 3 },
          color: 'text.secondary',
        }}
      >
        Voltar ao site
      </Button>
      <Box sx={{ mb: 2 }}>
        <RenderApiStatus />
      </Box>
      <Box
        sx={{
          m: 'auto',
          width: '100%',
          maxWidth: registering ? 520 : 1130,
          display: 'grid',
          gridTemplateColumns: {
            xs: 'minmax(0,1fr)',
            md: registering ? 'minmax(0,1fr)' : '1fr 1fr',
          },
          border: '1px solid #E4E9EC',
          borderRadius: '20px',
          bgcolor: 'white',
          boxShadow: '0 12px 50px #14233109',
          overflow: 'hidden',
        }}
      >
        {!registering && <AuthVisual />}
        <Box
          component="main"
          id="conteudo"
          tabIndex={-1}
          ref={main}
          sx={{
            outline: 'none',
            minWidth: 0,
            px: { xs: 2.5, sm: 6, lg: 7 },
            py: { xs: 3, md: 5 },
            '@media (max-height: 800px)': { py: 2.5, px: { xs: 2.5, sm: 4 } },
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <Outlet />
        </Box>
      </Box>
      <Typography
        variant="caption"
        sx={{ textAlign: 'center', color: 'text.secondary', mt: 3 }}
      >
        OrangeVision · Engenharia da Computação · USF
      </Typography>
    </Box>
  );
}
