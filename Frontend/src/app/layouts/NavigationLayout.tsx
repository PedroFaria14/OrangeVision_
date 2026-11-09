import { Box, Drawer, useMediaQuery, useTheme } from '@mui/material';
import { useState, type ReactNode } from 'react';
import { SkipLink } from '@/shared/ui/SkipLink';
import { usePageFocus } from '../hooks/usePageFocus';
import { SiteHeader } from '../components/SiteHeader';
import { RenderApiStatus } from '@/features/service-status/RenderApiStatus';

const sidebarWidth = 238;
type Props = {
  section: string;
  sidebar: (close: () => void) => ReactNode;
  children: ReactNode;
  footer?: ReactNode;
};

export function NavigationLayout({
  section,
  sidebar,
  children,
  footer,
}: Props) {
  const [open, setOpen] = useState(false);
  const theme = useTheme();
  const desktop = useMediaQuery(theme.breakpoints.up('md'));
  const main = usePageFocus();
  const content = sidebar(() => setOpen(false));
  return (
    <Box sx={{ minHeight: '100dvh', bgcolor: '#F4F6F8' }}>
      <SkipLink />
      <Box
        component="aside"
        sx={{
          display: { xs: 'none', md: 'block' },
          position: 'fixed',
          inset: '0 auto 0 0',
          width: sidebarWidth,
          zIndex: 1200,
        }}
      >
        {content}
      </Box>
      <Drawer
        variant="temporary"
        open={open && !desktop}
        onClose={() => setOpen(false)}
        sx={{
          display: { xs: 'block', md: 'none' },
          '& .MuiDrawer-paper': { width: sidebarWidth, bgcolor: '#16212B' },
        }}
      >
        <Box id="menu-navegacao" sx={{ height: '100%' }}>
          {content}
        </Box>
      </Drawer>
      <Box
        sx={{
          ml: { md: `${sidebarWidth}px` },
          minWidth: 0,
          minHeight: '100dvh',
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        <SiteHeader
          section={section}
          openMenu={() => setOpen(true)}
          menuOpen={open && !desktop}
        />
        <RenderApiStatus />
        <Box
          component="main"
          id="conteudo"
          ref={main}
          tabIndex={-1}
          sx={{
            outline: 'none',
            width: '100%',
            maxWidth: 1480,
            mx: 'auto',
            flex: 1,
            p: { xs: 2, sm: 3, lg: 5 },
            minWidth: 0,
          }}
        >
          {children}
        </Box>
        {footer}
      </Box>
    </Box>
  );
}
