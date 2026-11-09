import { Box, Button, Link, Paper, Stack, Typography } from '@mui/material';
import { OrangeVisionDivider } from '@/shared/ui/OrangeVisionDivider';
import { projectSustainability } from '../model/project';
import {
  bibliographySources,
  opencvTopics,
  theoryApplications,
  theoryFlow,
  theorySections,
} from '../model/theory';

const panel = { p: { xs: 2.5, sm: 4 }, minWidth: 0 };

export function ReferencesOverview() {
  return (
    <Stack spacing={0} divider={<OrangeVisionDivider />}>
      {theorySections.map((section) => (
        <Paper
          component="section"
          variant="outlined"
          aria-labelledby={`theory-${section.id}`}
          key={section.id}
          sx={{
            ...panel,
            borderLeft: '6px solid',
            borderLeftColor: section.accent,
            boxShadow: '0 4px 14px rgb(0 0 0 / 8%)',
          }}
        >
          <Typography
            variant="overline"
            color={
              section.accent === 'secondary.main'
                ? 'secondary.main'
                : 'primary.dark'
            }
            sx={{ letterSpacing: 1.5 }}
          >
            {section.label}
          </Typography>
          <Typography
            component="h2"
            variant="h3"
            id={`theory-${section.id}`}
            sx={{ mt: 1, mb: 2 }}
          >
            <Box component="span" aria-hidden="true" sx={{ mr: 1 }}>
              {section.symbol}
            </Box>
            {section.title}
          </Typography>
          <Stack spacing={2}>
            {section.paragraphs.map((paragraph) => (
              <Typography
                key={paragraph}
                color="text.secondary"
                sx={{ lineHeight: 1.8 }}
              >
                {paragraph}
              </Typography>
            ))}
          </Stack>
          <Link
            href={`#reference-${section.sourceId}`}
            sx={{
              display: 'inline-flex',
              alignItems: 'center',
              minHeight: 44,
              mt: 1,
              fontSize: 14,
              fontWeight: 700,
            }}
          >
            Fonte: {section.sourceLabel}
          </Link>
        </Paper>
      ))}

      <Box component="section" aria-labelledby="theory-applications">
        <Box sx={{ textAlign: 'center', mb: 3 }}>
          <Typography
            variant="overline"
            color="primary.dark"
            sx={{ letterSpacing: 2 }}
          >
            Teoria → implementação
          </Typography>
          <Typography
            component="h2"
            variant="h2"
            id="theory-applications"
            sx={{ mt: 1 }}
          >
            Aplicação no OrangeVision
          </Typography>
        </Box>
        <Box
          component="ul"
          sx={{
            display: 'grid',
            gridTemplateColumns: {
              xs: 'minmax(0, 1fr)',
              sm: 'repeat(2, minmax(0, 1fr))',
            },
            gap: 2.5,
            m: 0,
            p: 0,
            listStyle: 'none',
          }}
        >
          {theoryApplications.map((application, index) => (
            <Paper
              component="li"
              key={application.title}
              sx={{
                ...panel,
                textAlign: 'center',
                borderTop: '5px solid',
                borderTopColor:
                  index % 2 === 0 ? 'primary.main' : 'secondary.main',
                display: 'flex',
                flexDirection: 'column',
              }}
            >
              <Box component="span" aria-hidden="true" sx={{ fontSize: 32 }}>
                {application.symbol}
              </Box>
              <Typography component="h3" variant="h3" sx={{ my: 1.5 }}>
                {application.title}
              </Typography>
              <Typography
                variant="body2"
                color="text.secondary"
                sx={{ lineHeight: 1.8, mb: 2 }}
              >
                {application.description}
              </Typography>
              <Box
                sx={{
                  mt: 'auto',
                  p: 1.5,
                  borderRadius: 1,
                  bgcolor: index % 2 === 0 ? '#FFF7ED' : '#F0FDF4',
                  color: index % 2 === 0 ? '#9A3412' : '#166534',
                }}
              >
                <Typography variant="body2" sx={{ fontWeight: 700 }}>
                  {application.technique}
                </Typography>
                <Typography
                  variant="caption"
                  sx={{ display: 'block', mt: 1, lineHeight: 1.8 }}
                >
                  {application.detail}
                </Typography>
              </Box>
            </Paper>
          ))}
        </Box>
      </Box>

      <Box
        component="section"
        aria-labelledby="theory-score"
        sx={{
          ...panel,
          bgcolor: 'text.primary',
          color: 'common.white',
          borderRadius: 2,
        }}
      >
        <Typography
          variant="overline"
          color="primary.main"
          sx={{ letterSpacing: 2 }}
        >
          Fundamentação da triagem
        </Typography>
        <Typography
          component="h2"
          variant="h3"
          id="theory-score"
          sx={{ mt: 1, mb: 2 }}
        >
          Score visual e classificação experimental
        </Typography>
        <Box
          component="ol"
          sx={{
            display: 'flex',
            flexWrap: 'wrap',
            gap: 1.5,
            m: 0,
            pl: 2.5,
            mb: 3,
          }}
        >
          {theoryFlow.map((step) => (
            <Typography
              component="li"
              variant="body2"
              key={step}
              sx={{ pl: 0.5, mr: 2 }}
            >
              {step}
            </Typography>
          ))}
        </Box>
        <Typography sx={{ lineHeight: 1.8, color: '#E5E7EB' }}>
          O executor normaliza as quatro métricas segundo faixas e direção
          configuradas, combina os valores por pesos positivos e compara o score
          com limiares de Aprovada, Atenção e Revisar. Essa é uma regra
          experimental configurável do projeto.
        </Typography>
        <Typography
          sx={{
            my: 2,
            p: 2,
            border: '1px solid rgba(255,255,255,.35)',
            borderRadius: 1,
            fontSize: { xs: 13, sm: 16 },
            overflowWrap: 'anywhere',
          }}
        >
          Score visual = 100 × Σ(wᵢ × nᵢ) / Σwᵢ
        </Typography>
        <Typography variant="body2" sx={{ lineHeight: 1.8, color: '#E5E7EB' }}>
          Os termos nᵢ representam as métricas normalizadas e orientadas para o
          score; wᵢ são seus pesos. Faixas, pesos e limiares exigem calibração e
          avaliação com imagens rotuladas. As referências não validam
          automaticamente esses parâmetros. Score não é probabilidade nem
          acurácia, e detecção da fruta não é classificação de qualidade.
        </Typography>
      </Box>

      <Box
        component="section"
        aria-labelledby="theory-ods"
        sx={{
          ...panel,
          bgcolor: 'secondary.main',
          color: 'common.white',
          borderRadius: 2,
        }}
      >
        <Typography variant="overline" sx={{ letterSpacing: 1.5 }}>
          Agricultura e tecnologia
        </Typography>
        <Typography
          component="h2"
          variant="h3"
          id="theory-ods"
          sx={{ mt: 1, mb: 2 }}
        >
          Relação com o ODS 2
        </Typography>
        <Typography sx={{ lineHeight: 1.8 }}>
          {projectSustainability.target}
        </Typography>
        <Typography sx={{ lineHeight: 1.8, mt: 2 }}>
          {projectSustainability.application}
        </Typography>
        <Link
          href="#reference-onu"
          color="inherit"
          sx={{
            display: 'inline-flex',
            alignItems: 'center',
            minHeight: 44,
            mt: 1,
            fontWeight: 700,
          }}
        >
          Fonte: Nações Unidas — ODS 2 e meta 2.a
        </Link>
      </Box>

      <Paper
        component="section"
        variant="outlined"
        aria-labelledby="theory-limits"
        sx={{
          ...panel,
          bgcolor: '#FFF7ED',
          borderLeft: '6px solid',
          borderLeftColor: 'primary.main',
        }}
      >
        <Typography
          component="h2"
          variant="h3"
          id="theory-limits"
          sx={{ mb: 2 }}
        >
          Limitação do sistema
        </Typography>
        <Typography sx={{ color: '#7C2D12', lineHeight: 1.8 }}>
          O OrangeVision não realiza diagnóstico de greening ou de qualquer
          outra doença. As referências fitossanitárias fundamentam
          características externas observáveis. A triagem visual preliminar não
          determina qualidade interna ou sanitária e não substitui avaliação
          técnica especializada.
        </Typography>
      </Paper>

      <Box component="section" aria-labelledby="theory-bibliography">
        <Box sx={{ textAlign: 'center', mb: 3 }}>
          <Typography
            variant="overline"
            color="primary.dark"
            sx={{ letterSpacing: 2 }}
          >
            Fontes consultadas
          </Typography>
          <Typography
            component="h2"
            variant="h2"
            id="theory-bibliography"
            sx={{ mt: 1, mb: 2 }}
          >
            Referências Bibliográficas e Técnicas
          </Typography>
          <Typography
            color="text.secondary"
            sx={{ maxWidth: 880, mx: 'auto', lineHeight: 1.8 }}
          >
            Fontes de citricultura, visão computacional, sistemas embarcados,
            persistência, API, dashboard e sustentabilidade, acompanhadas de sua
            utilização no projeto. A lista distingue fundamentação de contexto e
            documentação técnica; a normalização acadêmica permanece em revisão.
          </Typography>
        </Box>
        <Stack
          component="ol"
          aria-label="Fontes bibliográficas e técnicas"
          spacing={2.5}
          sx={{ m: 0, p: 0, listStyle: 'none' }}
        >
          {bibliographySources.map((source, index) => (
            <Paper
              component="li"
              variant="outlined"
              key={source.id}
              id={`reference-${source.id}`}
              tabIndex={-1}
              sx={{ ...panel, bgcolor: '#F9FAFB', scrollMarginTop: 120 }}
            >
              <Typography
                variant="overline"
                color={index % 2 === 0 ? 'secondary.main' : 'primary.dark'}
                sx={{ letterSpacing: 1.5 }}
              >
                {String(index + 1).padStart(2, '0')} • {source.category}
              </Typography>
              <Typography component="h3" variant="h3" sx={{ mt: 1, mb: 2 }}>
                {source.name}
              </Typography>
              <Box
                sx={{
                  p: { xs: 2, sm: 2.5 },
                  bgcolor: 'common.white',
                  borderLeft: '5px solid',
                  borderLeftColor:
                    index % 2 === 0 ? 'secondary.main' : 'primary.main',
                  borderRadius: 1,
                }}
              >
                <Typography
                  variant="body2"
                  sx={{ lineHeight: 1.8, fontWeight: 600 }}
                >
                  {source.citation}
                </Typography>
                <Typography
                  variant="body2"
                  color="text.secondary"
                  sx={{ lineHeight: 1.8, mt: 1.5 }}
                >
                  <strong>Utilização no OrangeVision: </strong>
                  {source.usage}
                </Typography>
                <Button
                  component="a"
                  href={source.url}
                  variant="contained"
                  color={source.id === 'onu' ? 'primary' : 'secondary'}
                  sx={{
                    mt: 2,
                    maxWidth: '100%',
                    textAlign: 'left',
                    whiteSpace: 'normal',
                  }}
                >
                  {source.linkLabel}
                </Button>
                {source.id === 'opencv' && (
                  <Box component="ul" sx={{ mt: 2, mb: 0, pl: 2.5 }}>
                    {opencvTopics.map((topic) => (
                      <Typography
                        component="li"
                        key={topic.url}
                        variant="body2"
                        sx={{ lineHeight: 1.8 }}
                      >
                        <Link
                          href={topic.url}
                          sx={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            minHeight: 44,
                          }}
                        >
                          {topic.label}
                        </Link>
                      </Typography>
                    ))}
                  </Box>
                )}
              </Box>
            </Paper>
          ))}
        </Stack>
      </Box>

      <Paper
        component="section"
        variant="outlined"
        aria-labelledby="theory-articles"
        sx={{ ...panel, borderStyle: 'dashed', borderWidth: 2 }}
      >
        <Typography
          variant="overline"
          color="primary.dark"
          sx={{ letterSpacing: 1.5 }}
        >
          Pesquisa acadêmica
        </Typography>
        <Typography
          component="h2"
          variant="h3"
          id="theory-articles"
          sx={{ mt: 1, mb: 2 }}
        >
          Artigos Científicos
        </Typography>
        <Typography color="text.secondary" sx={{ lineHeight: 1.8 }}>
          Seleção e fichamento pendentes. Este espaço receberá artigos sobre
          classificação de frutas, processamento digital de imagens, visão
          computacional no agronegócio e inspeção automatizada, após revisão de
          autores, título, ano e DOI ou URL. Nenhum resultado de pesquisa é
          atribuído a um artigo ainda não selecionado.
        </Typography>
      </Paper>

      <Box
        sx={{
          ...panel,
          bgcolor: 'secondary.main',
          color: 'common.white',
          borderRadius: 2,
          textAlign: 'center',
        }}
      >
        <Typography variant="overline" sx={{ letterSpacing: 1.6 }}>
          OrangeVision
        </Typography>
        <Typography sx={{ fontWeight: 600, lineHeight: 1.8 }}>
          Fundamentação → Desenvolvimento → Validação → Resultados
        </Typography>
      </Box>
    </Stack>
  );
}
