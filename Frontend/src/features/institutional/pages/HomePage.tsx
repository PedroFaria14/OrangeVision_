import { Box, Button, Paper, Stack, Typography } from '@mui/material';
import { Link as RouterLink } from 'react-router-dom';
export default function HomePage() {
  return (
    <Stack spacing={7}>
      <Box
        sx={{
          borderLeft: 6,
          borderColor: 'primary.main',
          pl: { xs: 2, md: 4 },
          maxWidth: 900,
        }}
      >
        <Typography color="secondary" sx={{ fontWeight: 700 }} gutterBottom>
          AGRICULTURA · TECNOLOGIA · PESQUISA
        </Typography>
        <Typography variant="h1" gutterBottom>
          Visão Computacional aplicada à triagem inteligente de laranjas
        </Typography>
        <Typography sx={{ maxWidth: 700, mb: 3 }}>
          O OrangeVision propõe avaliar características externas da fruta com
          câmera, Raspberry Pi e OpenCV, registrando análises localmente e
          sincronizando dados para consulta online.
        </Typography>
        <Stack direction="row" sx={{ gap: 2, flexWrap: 'wrap' }}>
          <Button component={RouterLink} to="/projeto" variant="contained">
            Conhecer o projeto
          </Button>
          <Button
            component={RouterLink}
            to="/dashboard"
            variant="outlined"
            color="secondary"
          >
            Consultar dashboard
          </Button>
        </Stack>
      </Box>
      <Box
        sx={{
          display: 'grid',
          gridTemplateColumns: {
            xs: '1fr',
            sm: 'repeat(2,1fr)',
            md: 'repeat(3,1fr)',
          },
          gap: 3,
        }}
      >
        {[
          [
            'Visão Computacional',
            'Cor, regiões anormais, circularidade e assimetria são as métricas previstas para a inspeção externa.',
          ],
          [
            'Edge Computing',
            'A arquitetura prevê processamento no Raspberry Pi e registro local, mesmo sem internet.',
          ],
          [
            'Agronegócio',
            'Protótipo acadêmico relacionado ao Primeiro Setor e ao ODS 2.',
          ],
        ].map(([title, text]) => (
          <Paper variant="outlined" key={title} sx={{ p: 3 }}>
            <Typography variant="h3" gutterBottom>
              {title}
            </Typography>
            <Typography>{text}</Typography>
          </Paper>
        ))}
      </Box>
      <Box component="section">
        <Typography variant="h2" gutterBottom>
          Da captura ao registro
        </Typography>
        <Typography>
          Fluxo previsto — implementação física pendente de validação.
        </Typography>
        <Box
          component="ol"
          sx={{
            display: 'grid',
            gridTemplateColumns: {
              xs: '1fr',
              sm: '1fr 1fr',
              md: 'repeat(3,1fr)',
            },
            gap: 3,
            pl: 3,
            mt: 3,
          }}
        >
          {[
            'Posicionar e detectar a fruta',
            'Capturar a imagem',
            'Segmentar e extrair métricas',
            'Classificar e sinalizar',
            'Registrar no SQLite',
            'Sincronizar com Neon e consultar via API',
          ].map((step) => (
            <Typography component="li" key={step}>
              {step}
            </Typography>
          ))}
        </Box>
      </Box>
      <Box
        sx={{
          bgcolor: 'secondary.main',
          color: 'common.white',
          p: { xs: 3, md: 5 },
          borderRadius: 1,
        }}
      >
        <Typography variant="h2" gutterBottom>
          Pesquisa aplicada ao campo
        </Typography>
        <Typography>
          Uma proposta de padronização da triagem e do registro de ocorrências.
          O protótipo não determina integridade interna, inocuidade ou doenças
          específicas, e não possui acurácia validada.
        </Typography>
      </Box>
    </Stack>
  );
}
