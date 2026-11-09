import { Box, Typography } from '@mui/material';

const dot = {
  width: { xs: 8, sm: 10 },
  height: { xs: 8, sm: 10 },
  bgcolor: 'primary.main',
  borderRadius: '50%',
  flexShrink: 0,
  '@media (max-width: 380px)': { width: 7, height: 7 },
};

const line = {
  height: 2,
  flex: 1,
  bgcolor: 'secondary.main',
  opacity: 0.35,
  minWidth: { xs: 10, sm: 20 },
};

export function OrangeVisionDivider() {
  return (
    <Box
      aria-hidden="true"
      data-testid="orangevision-divider"
      sx={{
        width: '100%',
        maxWidth: 1100,
        mx: 'auto',
        py: 2.25,
        px: { xs: 0, sm: 2.5 },
        display: 'flex',
        alignItems: 'center',
        gap: { xs: 1.25, sm: 2.25 },
        '@media (max-width: 380px)': { gap: 0.875 },
      }}
    >
      <Box sx={line} />
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          gap: { xs: 0.875, sm: 1.25 },
          whiteSpace: 'nowrap',
          flexShrink: 0,
          '@media (max-width: 380px)': { gap: 0.625 },
        }}
      >
        <Box component="span" sx={dot} />
        <Typography
          component="span"
          sx={{
            color: 'text.primary',
            fontSize: { xs: 11, sm: 13 },
            fontWeight: 700,
            letterSpacing: { xs: 1.4, sm: 2 },
            textTransform: 'uppercase',
            '@media (max-width: 380px)': {
              fontSize: 10,
              letterSpacing: 1,
            },
          }}
        >
          OrangeVision
        </Typography>
        <Box component="span" sx={dot} />
      </Box>
      <Box sx={line} />
    </Box>
  );
}
