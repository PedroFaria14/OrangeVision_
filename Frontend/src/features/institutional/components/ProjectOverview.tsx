import { Alert, Box, Chip, Paper, Stack, Typography } from '@mui/material';
import { OrangeVisionDivider } from '@/shared/ui/OrangeVisionDivider';
import { ContextReferences } from './ContextReferences';
import {
  informationSteps,
  projectExpected,
  projectMetrics,
  projectNarrative,
  projectScope,
  projectSolution,
  projectStudy,
  projectSustainability,
  projectTopics,
} from '../model/project';

export function ProjectOverview() {
  return (
    <Stack spacing={0} divider={<OrangeVisionDivider />}>
      {projectNarrative.map((section) => (
        <Paper
          component="section"
          variant="outlined"
          key={section.id}
          aria-labelledby={`project-${section.id}`}
          sx={{
            p: { xs: 2.5, sm: 4 },
            borderLeft: 6,
            borderLeftColor: section.accent,
            boxShadow: '0 4px 14px rgb(0 0 0 / 8%)',
          }}
        >
          <Typography
            variant="overline"
            color={
              section.accent === 'primary.main'
                ? 'primary.dark'
                : 'secondary.main'
            }
            sx={{ letterSpacing: 1.5 }}
          >
            {section.label}
          </Typography>
          <Typography
            id={`project-${section.id}`}
            component="h2"
            variant="h3"
            sx={{ my: 1.5 }}
          >
            {section.title}
          </Typography>
          <Typography
            color="text.secondary"
            sx={{ lineHeight: 1.8, maxWidth: '75ch' }}
          >
            {section.text}
          </Typography>
          {section.id === 'problema' && (
            <Box sx={{ mt: 2, p: 2, bgcolor: '#FFF7ED', borderRadius: 1 }}>
              <Typography
                variant="body2"
                sx={{ color: '#9A3412', lineHeight: 1.8 }}
              >
                <strong>Desafio:</strong> analisar características externas de
                forma automática e gerar dados estruturados sobre cada inspeção.
              </Typography>
            </Box>
          )}
        </Paper>
      ))}

      <Paper
        component="section"
        variant="outlined"
        aria-labelledby="project-solution"
        sx={{
          p: { xs: 2.5, sm: 4 },
          borderLeft: 6,
          borderLeftColor: 'secondary.main',
          boxShadow: '0 4px 14px rgb(0 0 0 / 8%)',
        }}
      >
        <Typography
          variant="overline"
          color="secondary.main"
          sx={{ letterSpacing: 1.5 }}
        >
          03 · Solução
        </Typography>
        <Typography
          id="project-solution"
          component="h2"
          variant="h3"
          sx={{ my: 1.5 }}
        >
          {projectSolution.title}
        </Typography>
        <Typography
          color="text.secondary"
          sx={{ lineHeight: 1.8, maxWidth: '75ch' }}
        >
          {projectSolution.description}
        </Typography>
        <Box
          component="ul"
          sx={{
            display: 'grid',
            gridTemplateColumns: { xs: '1fr', md: 'repeat(3, minmax(0, 1fr))' },
            gap: 2,
            listStyle: 'none',
            p: 0,
            my: 3,
          }}
        >
          {projectSolution.classifications.map(([label, description]) => (
            <Box
              component="li"
              key={label}
              sx={{ p: 2, bgcolor: 'background.default', borderRadius: 1 }}
            >
              <Typography component="h3" variant="h6" gutterBottom>
                {label}
              </Typography>
              <Typography
                variant="body2"
                color="text.secondary"
                sx={{ lineHeight: 1.7 }}
              >
                {description}
              </Typography>
            </Box>
          ))}
        </Box>
        <Box
          component="figure"
          sx={{
            m: 0,
            p: { xs: 2, sm: 3 },
            bgcolor: 'text.primary',
            color: 'common.white',
            borderRadius: 2,
          }}
        >
          <Typography component="figcaption" variant="subtitle2" sx={{ mb: 2 }}>
            Da captura ao dashboard
          </Typography>
          <Box
            component="ol"
            sx={{
              m: 0,
              pl: 2.5,
              display: 'grid',
              gridTemplateColumns: {
                xs: '1fr',
                sm: 'repeat(2, minmax(0, 1fr))',
                lg: 'repeat(4, minmax(0, 1fr))',
              },
              gap: 2,
            }}
          >
            {projectSolution.steps.map((step) => (
              <Typography
                component="li"
                variant="body2"
                key={step}
                sx={{ pl: 0.5, lineHeight: 1.7 }}
              >
                {step}
              </Typography>
            ))}
          </Box>
        </Box>
        <Typography
          variant="body2"
          color="text.secondary"
          sx={{ mt: 2, lineHeight: 1.8 }}
        >
          {projectSolution.record}
        </Typography>
      </Paper>

      <Paper
        component="section"
        variant="outlined"
        aria-labelledby="project-study"
        sx={{
          p: { xs: 2.5, sm: 4 },
          borderLeft: 6,
          borderLeftColor: 'primary.main',
          boxShadow: '0 4px 14px rgb(0 0 0 / 8%)',
        }}
      >
        <Typography
          variant="overline"
          color="primary.dark"
          sx={{ letterSpacing: 1.5 }}
        >
          04 · Objeto de estudo
        </Typography>
        <Typography
          id="project-study"
          component="h2"
          variant="h3"
          sx={{ my: 1.5 }}
        >
          {projectStudy.title}
        </Typography>
        <Typography
          color="text.secondary"
          sx={{ lineHeight: 1.8, maxWidth: '75ch' }}
        >
          {projectStudy.description}
        </Typography>
        <Typography
          variant="body2"
          color="text.secondary"
          sx={{ mt: 1.5, lineHeight: 1.8 }}
        >
          {projectStudy.availability}
        </Typography>
      </Paper>

      <Box
        component="section"
        aria-labelledby="project-metrics"
        sx={{ textAlign: 'center' }}
      >
        <Typography
          variant="overline"
          color="primary.dark"
          sx={{ letterSpacing: 1.5 }}
        >
          Engenharia aplicada
        </Typography>
        <Typography
          id="project-metrics"
          component="h2"
          variant="h3"
          sx={{ my: 1.5 }}
        >
          Da fruta para os dados
        </Typography>
        <Typography
          color="text.secondary"
          sx={{ mb: 3, maxWidth: '75ch', mx: 'auto', lineHeight: 1.8 }}
        >
          Características observáveis da fruta são transformadas em métricas
          digitais para apoiar o processamento, o registro e a triagem.
        </Typography>
        <Box
          component="ul"
          sx={{
            m: 0,
            p: 0,
            listStyle: 'none',
            display: 'grid',
            gridTemplateColumns: {
              xs: '1fr',
              sm: 'repeat(2, minmax(0, 1fr))',
              xl: 'repeat(4, minmax(0, 1fr))',
            },
            gap: 2,
          }}
        >
          {projectMetrics.map((metric) => (
            <Paper
              component="li"
              variant="outlined"
              key={metric.name}
              sx={{
                p: 3,
                borderTop: 4,
                borderTopColor: metric.accent,
                minWidth: 0,
              }}
            >
              <Box component="span" aria-hidden="true" sx={{ fontSize: 30 }}>
                {metric.symbol}
              </Box>
              <Typography component="h3" variant="h6" sx={{ mt: 1, mb: 1.5 }}>
                {metric.name}
              </Typography>
              <Typography
                variant="body2"
                color="text.secondary"
                sx={{ lineHeight: 1.8 }}
              >
                {metric.description}
              </Typography>
            </Paper>
          ))}
        </Box>
        <Box
          component="figure"
          sx={{
            mx: 0,
            mt: 3,
            mb: 0,
            p: 3,
            bgcolor: 'text.primary',
            color: 'common.white',
            borderRadius: 2,
          }}
        >
          <Typography component="figcaption" variant="subtitle2" sx={{ mb: 2 }}>
            Transformação da informação
          </Typography>
          <Box
            component="ol"
            sx={{
              m: 0,
              pl: 2.5,
              display: 'grid',
              gridTemplateColumns: {
                xs: '1fr',
                sm: 'repeat(2, minmax(0, 1fr))',
                lg: 'repeat(3, minmax(0, 1fr))',
              },
              gap: 1.5,
            }}
          >
            {informationSteps.map((step) => (
              <Typography
                component="li"
                variant="body2"
                key={step}
                sx={{ lineHeight: 1.7 }}
              >
                {step}
              </Typography>
            ))}
          </Box>
        </Box>
      </Box>

      <Box
        component="section"
        aria-labelledby="project-sustainability"
        sx={{
          p: { xs: 2.5, sm: 4 },
          borderRadius: 2,
          bgcolor: 'secondary.main',
          color: 'common.white',
        }}
      >
        <Typography variant="overline" sx={{ letterSpacing: 1.5 }}>
          05 · Desenvolvimento sustentável
        </Typography>
        <Typography
          id="project-sustainability"
          component="h2"
          variant="h3"
          sx={{ my: 1.5 }}
        >
          {projectSustainability.title}
        </Typography>
        <Typography sx={{ lineHeight: 1.9, maxWidth: '75ch' }}>
          {projectSustainability.description}
        </Typography>
        <Box
          sx={{
            my: 3,
            p: 2.5,
            border: '1px solid',
            borderColor: 'rgba(255,255,255,.5)',
            borderRadius: 1,
          }}
        >
          <Typography component="h3" variant="h6" gutterBottom>
            Meta 2.a
          </Typography>
          <Typography variant="body2" sx={{ lineHeight: 1.9 }}>
            {projectSustainability.target}
          </Typography>
        </Box>
        <Typography variant="body2" sx={{ lineHeight: 1.9 }}>
          {projectSustainability.application}
        </Typography>
      </Box>

      <Paper
        component="section"
        variant="outlined"
        aria-labelledby="project-scope"
        sx={{
          p: { xs: 2.5, sm: 4 },
          bgcolor: '#FFF7ED',
          borderLeft: 5,
          borderLeftColor: 'primary.main',
        }}
      >
        <Typography id="project-scope" component="h2" variant="h3" gutterBottom>
          {projectScope.title}
        </Typography>
        <Stack spacing={2}>
          <Typography sx={{ lineHeight: 1.8, maxWidth: '75ch' }}>
            {projectScope.purpose}
          </Typography>
          <Typography sx={{ lineHeight: 1.8, maxWidth: '75ch' }}>
            {projectScope.limits}
          </Typography>
          <Typography
            variant="body2"
            sx={{ color: '#9A3412', lineHeight: 1.8 }}
          >
            {projectScope.calibration}
          </Typography>
        </Stack>
      </Paper>

      <Paper
        component="section"
        variant="outlined"
        aria-labelledby="project-expected"
        sx={{ p: { xs: 2.5, sm: 4 } }}
      >
        <Typography
          variant="overline"
          color="secondary.main"
          sx={{ letterSpacing: 1.5 }}
        >
          Resultado esperado
        </Typography>
        <Typography
          id="project-expected"
          component="h2"
          variant="h3"
          sx={{ my: 1.5 }}
        >
          {projectExpected.title}
        </Typography>
        <Typography
          color="text.secondary"
          sx={{ lineHeight: 1.8, maxWidth: '75ch' }}
        >
          {projectExpected.description}
        </Typography>
        <Alert severity="info" sx={{ mt: 2 }}>
          {projectExpected.hardware}
        </Alert>
      </Paper>

      <ContextReferences />
      <Box
        component="ul"
        aria-label="Áreas relacionadas ao OrangeVision"
        sx={{
          m: 0,
          p: 3,
          listStyle: 'none',
          display: 'flex',
          flexWrap: 'wrap',
          justifyContent: 'center',
          gap: 1,
          bgcolor: 'text.primary',
          borderRadius: 2,
        }}
      >
        {projectTopics.map((topic) => (
          <Box component="li" key={topic}>
            <Chip
              label={topic}
              variant="outlined"
              sx={{
                color: 'common.white',
                borderColor: 'rgba(255,255,255,.35)',
              }}
            />
          </Box>
        ))}
      </Box>
    </Stack>
  );
}
