import { Box, Container, Stack, Typography } from '@mui/material';
import { Brand } from '@/shared/ui/Brand';
export function SiteFooter() {
  return (
    <Box
      component="footer"
      sx={{
        bgcolor: 'text.primary',
        color: 'common.white',
        '& a:focus-visible': { outlineColor: 'common.white' },
      }}
    >
      <Box
        sx={{
          bgcolor: 'secondary.main',
          py: { xs: 3.5, sm: 4.5 },
          px: 3,
          textAlign: 'center',
        }}
      >
        <Container maxWidth="lg">
          <Typography
            variant="overline"
            sx={{
              display: 'block',
              fontSize: 13,
              fontWeight: 700,
              letterSpacing: 2,
              mb: 1,
              lineHeight: 1.8,
            }}
          >
            Engenharia • Tecnologia • Agronegócio
          </Typography>
          <Typography
            component="p"
            variant="h3"
            sx={{ fontSize: { xs: 22, sm: 25 }, lineHeight: 1.4 }}
          >
            Tecnologia aplicada a desafios reais do campo.
          </Typography>
        </Container>
      </Box>
      <Container maxWidth="lg" sx={{ py: 4 }}>
        <Box
          sx={{
            display: 'grid',
            gridTemplateColumns: {
              xs: 'minmax(0, 1fr)',
              sm: 'minmax(0, 1fr) auto',
            },
            alignItems: 'center',
            gap: 3,
          }}
        >
          <Stack spacing={1}>
            <Brand light large />
            <Typography variant="body2" sx={{ color: '#D1D5DB' }}>
              Visão Computacional aplicada ao Agronegócio
            </Typography>
          </Stack>
          <Box sx={{ textAlign: { xs: 'left', sm: 'right' } }}>
            <Typography variant="body2" sx={{ fontWeight: 700 }}>
              Universidade São Francisco — USF
            </Typography>
            <Typography
              variant="body2"
              sx={{ color: '#D1D5DB', mt: 0.5, lineHeight: 1.8 }}
            >
              Engenharia da Computação
            </Typography>
            <Typography
              variant="body2"
              sx={{ color: '#D1D5DB', lineHeight: 1.8 }}
            >
              Projeto Acadêmico • 2026
            </Typography>
          </Box>
        </Box>
        <Box
          sx={{
            borderTop: '1px solid rgba(255,255,255,.15)',
            mt: 3,
            pt: 2.5,
            textAlign: 'center',
          }}
        >
          <Typography
            component="p"
            variant="caption"
            sx={{ color: '#D1D5DB', lineHeight: 1.8 }}
          >
            OrangeVision • Sistemas Embarcados • Visão Computacional • Edge
            Computing
          </Typography>
          <Typography
            component="p"
            variant="caption"
            sx={{ color: '#D1D5DB', lineHeight: 1.8, mt: 1 }}
          >
            Protótipo acadêmico de inspeção visual externa. Resultados
            experimentais sujeitos à validação.
          </Typography>
        </Box>
      </Container>
    </Box>
  );
}
