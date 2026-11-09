import {
  Alert,
  Box,
  LinearProgress,
  Paper,
  Stack,
  Typography,
} from '@mui/material';
import type { Analysis } from '../api/analyses';
import { formatDate, formatNumber, formatRatio } from '@/shared/lib/format';
import { ClassificationBadge } from './ClassificationBadge';
import { classifications } from '../model/classification';
import { Icon } from '@/shared/ui/Icon';

export function AnalysisDetails({ data }: { data: Analysis }) {
  const values = [
    ['Proporção de cor laranja', formatRatio(data.metrics.orange_color_ratio)],
    ['Regiões anormais', formatRatio(data.metrics.abnormal_region_ratio)],
    ['Circularidade', formatNumber(data.metrics.circularity, 3)],
    ['Assimetria', formatRatio(data.metrics.asymmetry)],
  ];
  const style = classifications[data.classification];
  return (
    <Stack spacing={3}>
      <Stack
        direction="row"
        sx={{ gap: 2, flexWrap: 'wrap', alignItems: 'center' }}
      >
        <ClassificationBadge value={data.classification} />
        <Typography variant="body2" color="text.secondary">
          {formatDate(data.timestamp)} · America/Sao_Paulo
        </Typography>
      </Stack>
      {data.evaluation_source && (
        <Alert severity="info">
          Origem do resultado adotado:{' '}
          {data.evaluation_source === 'gemini'
            ? 'Gemini confirmado pelo operador'
            : data.evaluation_source === 'human'
              ? 'Decisão humana'
              : 'Processamento local no Raspberry'}
          .
          {data.decision_revision
            ? ` Revisão ${data.decision_revision}.`
            : ' Publicação local automática.'}{' '}
          Métricas ausentes continuam não informadas; uma decisão qualitativa
          não gera medições OpenCV.
        </Alert>
      )}
      <Box
        sx={{
          display: 'grid',
          gridTemplateColumns: { xs: 'minmax(0,1fr)', lg: '1fr 1fr' },
          gap: 3,
        }}
      >
        <Paper variant="outlined" sx={{ overflow: 'hidden' }}>
          <Box
            sx={{
              minHeight: 250,
              bgcolor: '#EDF2F5',
              px: 3,
              py: 5,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexDirection: 'column',
              textAlign: 'center',
              gap: 1.5,
            }}
          >
            <Icon name="image" sx={{ fontSize: 38, color: '#A0ADBA' }} />
            <Typography
              sx={{ color: 'text.secondary', fontWeight: 550, fontSize: 14 }}
            >
              Imagem não disponibilizada
            </Typography>
            <Typography
              variant="caption"
              color="text.secondary"
              sx={{ maxWidth: 260 }}
            >
              Este registro não contém uma imagem privada autorizada para
              exibição.
            </Typography>
          </Box>
          <Stack
            direction="row"
            sx={{
              p: 3,
              gap: 2,
              alignItems: 'center',
              bgcolor: style.background,
              borderTop: `1px solid ${style.border}`,
            }}
          >
            <Box
              sx={{
                width: 42,
                height: 42,
                borderRadius: '50%',
                bgcolor: style.border,
                display: 'grid',
                placeItems: 'center',
                color: style.color,
              }}
            >
              <Icon name={style.icon} />
            </Box>
            <Box>
              <Typography sx={{ fontWeight: 700, color: style.color }}>
                {style.label}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Classificação experimental registrada.
              </Typography>
            </Box>
          </Stack>
        </Paper>
        <Paper
          component="section"
          aria-labelledby="analysis-metrics"
          variant="outlined"
          sx={{ p: { xs: 2.5, sm: 3 } }}
        >
          <Typography
            id="analysis-metrics"
            component="h2"
            variant="h6"
            sx={{ mb: 1 }}
          >
            Métricas da análise
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
            Valores calculados pelo processamento e recebidos pela API. O traço
            (—) indica uma métrica não informada. As medições são locais e podem
            ter origem diferente da classificação adotada; não são geradas pelo
            Gemini.
          </Typography>
          <Stack
            direction="row"
            sx={{
              justifyContent: 'space-between',
              alignItems: 'baseline',
              gap: 2,
              flexWrap: 'wrap',
            }}
          >
            <Typography variant="body2" color="text.secondary">
              Score experimental
            </Typography>
            <Typography
              sx={{
                fontSize: data.metrics.visual_score === null ? 16 : 28,
                fontWeight: 650,
                overflowWrap: 'anywhere',
              }}
            >
              {data.metrics.visual_score === null
                ? 'Não informado'
                : formatNumber(data.metrics.visual_score)}{' '}
              {data.metrics.visual_score !== null && (
                <Box
                  component="span"
                  sx={{
                    fontSize: 12,
                    fontWeight: 400,
                    color: 'text.secondary',
                  }}
                >
                  / 100
                </Box>
              )}
            </Typography>
          </Stack>
          {data.metrics.visual_score !== null && (
            <LinearProgress
              variant="determinate"
              value={data.metrics.visual_score}
              aria-label="Score experimental de zero a cem"
              sx={{
                height: 6,
                borderRadius: 2,
                mt: 1,
                mb: 3,
                bgcolor: '#F0F3F6',
                '& .MuiLinearProgress-bar': { bgcolor: style.color },
              }}
            />
          )}
          <Box
            component="dl"
            sx={{
              m: 0,
              display: 'grid',
              gridTemplateColumns: '1fr 1fr',
              gap: 2,
            }}
          >
            {values.map(([label, value]) => (
              <Box
                key={label}
                sx={{ bgcolor: '#F8FAFB', p: 2, borderRadius: 2, minWidth: 0 }}
              >
                <Typography
                  component="dt"
                  sx={{ color: 'text.secondary', fontSize: 12, mb: 1 }}
                >
                  {label}
                </Typography>
                <Typography
                  component="dd"
                  sx={{
                    m: 0,
                    fontSize: 19,
                    fontWeight: 600,
                    overflowWrap: 'anywhere',
                  }}
                >
                  {value}
                </Typography>
              </Box>
            ))}
          </Box>
        </Paper>
      </Box>
      <Paper
        component="section"
        aria-labelledby="analysis-trace"
        variant="outlined"
        sx={{ p: { xs: 2.5, sm: 3 } }}
      >
        <Typography
          id="analysis-trace"
          component="h2"
          variant="h6"
          sx={{ mb: 2 }}
        >
          Rastreabilidade
        </Typography>
        <Stack spacing={1.5}>
          <Typography variant="body2" sx={{ overflowWrap: 'anywhere' }}>
            ID: {data.id}
          </Typography>
          <Typography variant="body2" sx={{ overflowWrap: 'anywhere' }}>
            Dispositivo: {data.device_id || 'Não informado'}
          </Typography>
          <Typography variant="body2" sx={{ overflowWrap: 'anywhere' }}>
            Calibração: {data.calibration_version || 'Não informada'}
          </Typography>
          {data.inspection_session_id && (
            <Typography variant="body2" sx={{ overflowWrap: 'anywhere' }}>
              Sessão de inspeção: {data.inspection_session_id}
            </Typography>
          )}
        </Stack>
      </Paper>
      <Paper
        component="section"
        aria-labelledby="analysis-reason"
        variant="outlined"
        sx={{ p: { xs: 2.5, sm: 3 } }}
      >
        <Typography
          id="analysis-reason"
          component="h2"
          variant="h6"
          sx={{ mb: 2 }}
        >
          Justificativa da classificação
        </Typography>
        <Typography variant="body2" sx={{ overflowWrap: 'anywhere' }}>
          {data.classification_reason
            ? `Justificativa registrada: ${data.classification_reason}`
            : 'Justificativa não disponibilizada.'}
        </Typography>
      </Paper>
      <Alert severity="info">
        Imagens privadas não estão disponíveis nesta consulta. A classificação
        considera características visuais externas; regiões anormais não
        constituem diagnóstico de doença.
      </Alert>
    </Stack>
  );
}
