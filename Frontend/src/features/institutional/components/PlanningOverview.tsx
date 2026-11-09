import {
  Alert,
  Box,
  Paper,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
} from '@mui/material';
import {
  planningDeliverables,
  planningFlow,
  planningMonths,
  planningOverview,
  planningQuestions,
  planningStages,
} from '../model/planning';

const panel = { p: { xs: 2.5, sm: 4 }, minWidth: 0 };
const cards = {
  display: 'grid',
  gridTemplateColumns: {
    xs: 'minmax(0, 1fr)',
    sm: 'repeat(2, minmax(0, 1fr))',
    lg: 'repeat(3, minmax(0, 1fr))',
  },
  gap: 2.5,
};

function SectionHeading({
  id,
  eyebrow,
  title,
  description,
}: {
  id: string;
  eyebrow: string;
  title: string;
  description: string;
}) {
  return (
    <Box sx={{ textAlign: 'center', mb: 4 }}>
      <Typography
        variant="overline"
        color="primary.dark"
        sx={{ letterSpacing: 2 }}
      >
        {eyebrow}
      </Typography>
      <Typography id={id} component="h2" variant="h2" sx={{ mt: 1 }}>
        {title}
      </Typography>
      <Box
        aria-hidden="true"
        sx={{
          width: 55,
          height: 4,
          bgcolor: 'secondary.main',
          borderRadius: 2,
          mx: 'auto',
          my: 2,
        }}
      />
      <Typography
        color="text.secondary"
        sx={{ maxWidth: 760, mx: 'auto', lineHeight: 1.8 }}
      >
        {description}
      </Typography>
    </Box>
  );
}

export function PlanningOverview() {
  return (
    <Stack spacing={{ xs: 3, sm: 4 }}>
      <Paper
        component="section"
        variant="outlined"
        aria-labelledby="planning-intro"
        sx={panel}
      >
        <Typography
          component="h2"
          variant="h2"
          id="planning-intro"
          sx={{ mb: 2 }}
        >
          {planningOverview.title}
        </Typography>
        <Box
          aria-hidden="true"
          sx={{
            width: 60,
            height: 4,
            bgcolor: 'secondary.main',
            borderRadius: 2,
            mb: 3,
          }}
        />
        <Typography
          color="text.secondary"
          sx={{ lineHeight: 1.8, maxWidth: '85ch' }}
        >
          {planningOverview.description}
        </Typography>
        <Box
          sx={{
            mt: 3,
            p: 2.5,
            bgcolor: 'text.primary',
            color: 'common.white',
            borderLeft: '5px solid',
            borderLeftColor: 'primary.main',
            borderRadius: 1,
          }}
        >
          <Typography variant="body2" sx={{ lineHeight: 1.8 }}>
            <Box component="strong" sx={{ color: 'primary.main' }}>
              Objetivo do planejamento:{' '}
            </Box>
            {planningOverview.objective}
          </Typography>
        </Box>
      </Paper>

      <Paper
        component="section"
        variant="outlined"
        aria-labelledby="planning-5w2h"
        sx={panel}
      >
        <SectionHeading
          id="planning-5w2h"
          eyebrow="Planejamento estratégico"
          title="5W2H do OrangeVision"
          description="A metodologia 5W2H organiza o que será desenvolvido, sua finalidade, responsáveis, local, período, metodologia e recursos necessários."
        />
        <Box sx={cards}>
          {planningQuestions.map((item, index) => {
            const dark = item.key === 'cost';
            const accent = index % 2 === 0 ? 'primary.main' : 'secondary.main';
            return (
              <Box
                key={item.key}
                component="article"
                aria-labelledby={`planning-${item.key}`}
                sx={{
                  p: 3,
                  minWidth: 0,
                  borderRadius: 2,
                  borderTop: '5px solid',
                  borderTopColor: accent,
                  bgcolor: dark ? 'text.primary' : 'common.white',
                  color: dark ? 'common.white' : 'text.primary',
                  boxShadow: '0 4px 14px rgb(0 0 0 / 8%)',
                }}
              >
                <Stack
                  direction="row"
                  spacing={1.5}
                  sx={{ mb: 2, alignItems: 'center' }}
                >
                  <Box
                    aria-hidden="true"
                    sx={{
                      width: 42,
                      height: 42,
                      flexShrink: 0,
                      display: 'grid',
                      placeItems: 'center',
                      borderRadius: '50%',
                      bgcolor: accent,
                      color: index % 2 === 0 ? 'text.primary' : 'common.white',
                      fontWeight: 700,
                      fontSize: 18,
                    }}
                  >
                    {item.label[0]}
                  </Box>
                  <Box>
                    <Typography
                      variant="overline"
                      sx={{
                        color: dark
                          ? 'primary.main'
                          : index % 2 === 0
                            ? 'primary.dark'
                            : 'secondary.main',
                        letterSpacing: 1.5,
                        lineHeight: 1.5,
                      }}
                    >
                      {item.label}
                    </Typography>
                    <Typography
                      component="h3"
                      variant="h3"
                      id={`planning-${item.key}`}
                    >
                      {item.question}
                    </Typography>
                  </Box>
                </Stack>
                <Typography
                  variant="body2"
                  sx={{
                    color: dark ? '#E5E7EB' : 'text.secondary',
                    lineHeight: 1.8,
                  }}
                >
                  {item.text}
                </Typography>
              </Box>
            );
          })}
        </Box>
        <Box
          sx={{
            mt: 3,
            p: 2.5,
            bgcolor: 'secondary.main',
            color: 'common.white',
            textAlign: 'center',
            borderRadius: 2,
          }}
        >
          <Typography sx={{ lineHeight: 1.8 }}>
            <strong>OrangeVision:</strong> planejamento estruturado para
            transformar visão computacional, sistemas embarcados e análise de
            dados em uma solução aplicada ao agronegócio.
          </Typography>
        </Box>
      </Paper>

      <Paper
        component="section"
        variant="outlined"
        aria-labelledby="planning-stages"
        sx={panel}
      >
        <SectionHeading
          id="planning-stages"
          eyebrow="Desenvolvimento"
          title="Etapas do Projeto"
          description="Sete etapas organizam o desenvolvimento, desde a pesquisa inicial até a validação do protótipo e apresentação dos resultados."
        />
        <Stack
          component="ol"
          spacing={2.5}
          sx={{ m: 0, p: 0, listStyle: 'none' }}
        >
          {planningStages.map((stage, index) => (
            <Box
              component="li"
              key={stage.id}
              sx={{
                display: 'flex',
                alignItems: 'flex-start',
                gap: { xs: 1.5, sm: 2.5 },
              }}
            >
              <Box
                aria-hidden="true"
                sx={{
                  width: { xs: 36, sm: 56 },
                  height: { xs: 36, sm: 56 },
                  flexShrink: 0,
                  display: 'grid',
                  placeItems: 'center',
                  borderRadius: '50%',
                  bgcolor: index % 2 === 0 ? 'primary.main' : 'secondary.main',
                  color: index % 2 === 0 ? 'text.primary' : 'common.white',
                  fontWeight: 700,
                }}
              >
                {String(index + 1).padStart(2, '0')}
              </Box>
              <Box
                sx={{
                  flex: 1,
                  minWidth: 0,
                  p: { xs: 2, sm: 3 },
                  borderLeft: '5px solid',
                  borderLeftColor:
                    index % 2 === 0 ? 'primary.main' : 'secondary.main',
                  borderRadius: 2,
                  boxShadow: '0 4px 14px rgb(0 0 0 / 8%)',
                }}
              >
                <Typography
                  variant="overline"
                  color={index % 2 === 0 ? 'primary.dark' : 'secondary.main'}
                  sx={{ letterSpacing: 1.5 }}
                >
                  {stage.category}
                </Typography>
                <Typography
                  component="h3"
                  variant="h3"
                  sx={{ mt: 0.5, mb: 1.5, overflowWrap: 'anywhere' }}
                >
                  <Box component="span" aria-hidden="true" sx={{ mr: 1 }}>
                    {stage.icon}
                  </Box>
                  {stage.title}
                </Typography>
                <Typography
                  variant="body2"
                  color="text.secondary"
                  sx={{ lineHeight: 1.8 }}
                >
                  {stage.description}
                </Typography>
              </Box>
            </Box>
          ))}
        </Stack>
      </Paper>

      <Paper
        component="section"
        variant="outlined"
        aria-labelledby="planning-schedule"
        sx={panel}
      >
        <SectionHeading
          id="planning-schedule"
          eyebrow="Planejamento temporal"
          title="Cronograma do Projeto"
          description="Previsão de setembro a novembro de 2026, com atividades que podem ocorrer simultaneamente. O cronograma não indica conclusão ou medição de progresso."
        />
        <TableContainer
          component={Box}
          role="region"
          aria-label="Cronograma previsto de setembro a novembro de 2026"
          tabIndex={0}
          sx={{ borderRadius: 2 }}
        >
          <Table sx={{ minWidth: 680 }}>
            <Box
              component="caption"
              sx={{
                textAlign: 'left',
                color: 'text.secondary',
                fontSize: 13,
                py: 2,
              }}
            >
              Períodos previstos para cada etapa · 2026
            </Box>
            <TableHead>
              <TableRow
                sx={{
                  '& th': {
                    bgcolor: 'text.primary',
                    color: 'common.white',
                    py: 2,
                  },
                }}
              >
                <TableCell scope="col">Etapa</TableCell>
                <TableCell scope="col">Atividade</TableCell>
                {planningMonths.map((month) => (
                  <TableCell scope="col" key={month.id} align="center">
                    {month.label}
                  </TableCell>
                ))}
              </TableRow>
            </TableHead>
            <TableBody>
              {planningStages.map((stage, index) => (
                <TableRow key={stage.id}>
                  <TableCell sx={{ fontWeight: 700 }}>
                    {String(index + 1).padStart(2, '0')}
                  </TableCell>
                  <TableCell
                    component="th"
                    scope="row"
                    sx={{ fontWeight: 600 }}
                  >
                    {stage.title}
                  </TableCell>
                  {planningMonths.map((month) => {
                    const planned = stage.months.some(
                      (value) => value === month.id,
                    );
                    return (
                      <TableCell key={month.id} align="center">
                        {planned ? (
                          <>
                            <Box
                              aria-hidden="true"
                              sx={{
                                height: 10,
                                minWidth: 70,
                                borderRadius: 2,
                                bgcolor:
                                  index % 2 === 0
                                    ? 'primary.main'
                                    : 'secondary.main',
                                mb: 0.75,
                              }}
                            />
                            <Typography variant="caption">Previsto</Typography>
                          </>
                        ) : (
                          '—'
                        )}
                      </TableCell>
                    );
                  })}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
        <Typography
          variant="body2"
          color="text.secondary"
          sx={{ mt: 2, lineHeight: 1.8 }}
        >
          <strong>Observação:</strong> hardware, visão computacional e software
          podem evoluir em paralelo, com ajustes do planejamento conforme a
          disponibilidade dos componentes e os resultados dos testes.
        </Typography>
      </Paper>

      <Paper
        component="section"
        variant="outlined"
        aria-labelledby="planning-deliverables"
        sx={panel}
      >
        <SectionHeading
          id="planning-deliverables"
          eyebrow="Resultados esperados"
          title="Entregas do Projeto"
          description="Entregas técnicas, acadêmicas e demonstrativas previstas para documentar a evolução do projeto até a validação do protótipo."
        />
        <Box sx={cards}>
          {planningDeliverables.map((item, index) => (
            <Box
              component="article"
              key={item.title}
              sx={{
                p: 3,
                minWidth: 0,
                borderRadius: 2,
                borderTop: '5px solid',
                borderTopColor:
                  index % 2 === 0 ? 'primary.main' : 'secondary.main',
                boxShadow: '0 4px 14px rgb(0 0 0 / 8%)',
              }}
            >
              <Box aria-hidden="true" sx={{ fontSize: 32, mb: 1.5 }}>
                {item.icon}
              </Box>
              <Typography
                variant="overline"
                color={index % 2 === 0 ? 'primary.dark' : 'secondary.main'}
              >
                Entrega {String(index + 1).padStart(2, '0')}
              </Typography>
              <Typography component="h3" variant="h3" sx={{ my: 1.5 }}>
                {item.title}
              </Typography>
              <Typography
                variant="body2"
                color="text.secondary"
                sx={{ lineHeight: 1.8 }}
              >
                {item.description}
              </Typography>
            </Box>
          ))}
        </Box>
        <Box
          sx={{
            mt: 3.5,
            p: { xs: 2.5, sm: 3.5 },
            bgcolor: 'text.primary',
            color: 'common.white',
            borderLeft: '6px solid',
            borderLeftColor: 'primary.main',
            borderRadius: 2,
          }}
        >
          <Typography
            variant="overline"
            color="primary.main"
            sx={{ letterSpacing: 2 }}
          >
            Entrega final prevista
          </Typography>
          <Typography component="h3" variant="h3" sx={{ my: 1.5 }}>
            Protótipo OrangeVision
          </Typography>
          <Typography
            variant="body2"
            sx={{ color: '#D1D5DB', lineHeight: 1.8 }}
          >
            Demonstração do sistema completo acompanhada de fotos do protótipo,
            dashboard, resultados, documentação técnica e vídeo demonstrando o
            ciclo de operação. As evidências serão registradas após os testes
            reais.
          </Typography>
          <Box
            component="figure"
            sx={{
              m: 0,
              mt: 3,
              pt: 2.5,
              borderTop: '1px solid rgba(255,255,255,.15)',
            }}
          >
            <Typography component="figcaption" sx={{ fontWeight: 700, mb: 2 }}>
              Ciclo previsto do protótipo
            </Typography>
            <Box
              component="ol"
              sx={{
                display: 'flex',
                flexWrap: 'wrap',
                gap: 1,
                m: 0,
                p: 0,
                listStyle: 'none',
              }}
            >
              {planningFlow.map((step, index) => (
                <Box
                  component="li"
                  key={step}
                  sx={{ fontSize: 14, lineHeight: 1.8 }}
                >
                  {index > 0 && (
                    <Box component="span" aria-hidden="true" sx={{ mr: 1 }}>
                      →
                    </Box>
                  )}
                  {step}
                </Box>
              ))}
            </Box>
            <Typography
              variant="body2"
              sx={{ color: '#D1D5DB', mt: 2, lineHeight: 1.8 }}
            >
              Sinalização e atuação física são opcionais. O fluxo com câmera não
              depende de LEDs, buzzer, servo ou sensor.
            </Typography>
          </Box>
        </Box>
        <Alert severity="info" sx={{ mt: 3 }}>
          Planejamento não é comprovação de conclusão. A classificação de
          qualidade exige calibração validada, e o desempenho do protótipo
          depende dos testes na bancada.
        </Alert>
      </Paper>
    </Stack>
  );
}
