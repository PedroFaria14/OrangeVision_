import {
  Avatar,
  Box,
  Button,
  IconButton,
  Skeleton,
  Stack,
  Typography,
} from '@mui/material';
import { Link } from 'react-router-dom';
import { useSession } from '@/features/auth/hooks/useSession';
import { Icon } from '@/shared/ui/Icon';

export function SiteHeader({
  section,
  openMenu,
  menuOpen,
}: {
  section: string;
  openMenu: () => void;
  menuOpen: boolean;
}) {
  const { session, pending } = useSession();
  return (
    <Stack
      component="header"
      direction="row"
      sx={{
        position: 'sticky',
        top: 0,
        zIndex: 1100,
        bgcolor: '#FFFFFFF5',
        borderBottom: '1px solid #E6EBEF',
        minHeight: 76,
        px: { xs: 2, sm: 3, lg: 5 },
        gap: 1.5,
        alignItems: 'center',
        justifyContent: 'space-between',
      }}
    >
      <Stack
        direction="row"
        sx={{ alignItems: 'center', gap: 1.5, minWidth: 0 }}
      >
        <IconButton
          aria-label="Abrir menu"
          aria-expanded={menuOpen}
          aria-controls={menuOpen ? 'menu-navegacao' : undefined}
          onClick={openMenu}
          sx={{ display: { md: 'none' }, color: 'text.primary' }}
        >
          <Icon name="menu" />
        </IconButton>
        <Typography
          sx={{
            color: '#657387',
            fontSize: 12,
            display: { xs: 'none', sm: 'block' },
          }}
        >
          OrangeVision{' '}
          <Box component="span" sx={{ px: 1, color: '#CCD2DA' }}>
            /
          </Box>
        </Typography>
        <Typography sx={{ fontSize: 13, fontWeight: 550 }}>
          {section}
        </Typography>
      </Stack>
      {pending ? (
        <Skeleton variant="circular" width={34} height={34} />
      ) : session ? (
        <Button
          component={Link}
          to="/dashboard/perfil"
          sx={{
            color: 'text.primary !important',
            gap: 1.2,
            minWidth: 0,
            textAlign: 'left',
          }}
        >
          <Avatar
            aria-hidden="true"
            sx={{
              bgcolor: '#FFF0E5',
              color: '#A3430B',
              width: 34,
              height: 34,
              fontSize: 14,
              fontWeight: 600,
            }}
          >
            {session.user.name.slice(0, 1).toUpperCase()}
          </Avatar>
          <Box
            component="span"
            sx={{
              display: { xs: 'block', sm: 'none' },
              position: 'absolute',
              width: 1,
              height: 1,
              overflow: 'hidden',
              clip: 'rect(0, 0, 0, 0)',
              whiteSpace: 'nowrap',
            }}
          >
            Abrir perfil
          </Box>
          <Box sx={{ display: { xs: 'none', sm: 'block' }, maxWidth: 180 }}>
            <Typography
              title={session.user.name}
              sx={{
                fontSize: 12,
                fontWeight: 600,
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
              }}
            >
              {session.user.name}
            </Typography>
            <Typography sx={{ fontSize: 12, color: 'text.secondary' }}>
              Minha conta
            </Typography>
          </Box>
        </Button>
      ) : (
        <Button component={Link} to="/login" variant="contained">
          Entrar
        </Button>
      )}
    </Stack>
  );
}
