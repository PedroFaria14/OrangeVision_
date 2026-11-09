import { Box, Paper, Stack, Typography } from '@mui/material';
import type { Summary } from '../api/analyses';
import { formatDate, formatNumber, formatRatio } from '@/shared/lib/format';
import { Icon } from '@/shared/ui/Icon';
import { classifications } from '../model/classification';
import type { Comparison } from '../api/comparison';
import { CountDelta } from './CountDelta';
import { signedNumber } from '../model/comparison_format';
export function MetricCards({
  data,
  comparison,
}: {
  data: Summary;
  comparison?: Comparison;
}) {
  return (
    <Stack spacing={2}>
      <Box
        sx={{
          display: 'grid',
          gridTemplateColumns: { xs: '1fr', sm: 'repeat(3,minmax(0,1fr))' },
          gap: 2,
        }}
      >
        {(
          [
            { kind: 'APROVADA', value: data.approved, field: 'approved' },
            { kind: 'ATENCAO', value: data.attention, field: 'attention' },
            { kind: 'REVISAR', value: data.review, field: 'review' },
          ] as const
        ).map(({ kind, value, field }) => {
          const style = classifications[kind];
          return (
            <Paper
              key={kind}
              component="section"
              aria-label={`Indicador: ${style.plural}`}
              variant="outlined"
              sx={{
                p: { xs: 2, sm: 3 },
                bgcolor: style.background,
                borderColor: style.border,
                display: 'flex',
                alignItems: 'center',
                gap: 2.5,
                minHeight: 124,
              }}
            >
              <Box
                sx={{
                  display: 'grid',
                  placeItems: 'center',
                  width: 48,
                  height: 48,
                  borderRadius: '50%',
                  bgcolor: style.border,
                  color: style.color,
                  flexShrink: 0,
                }}
              >
                <Icon name={style.icon} sx={{ fontSize: 25, strokeWidth: 2 }} />
              </Box>
              <Box sx={{ minWidth: 0 }}>
                <Typography
                  sx={{
                    color: style.color,
                    fontSize: { xs: 32, sm: 36 },
                    fontWeight: 700,
                    lineHeight: 1.15,
                    letterSpacing: '-1px',
                    fontVariantNumeric: 'tabular-nums',
                  }}
                >
                  {formatNumber(value, 0)}
                </Typography>
                <Typography
                  sx={{
                    color: style.color,
                    fontSize: 13,
                    mt: 0.6,
                    fontWeight: 500,
                  }}
                >
                  {style.plural}
                </Typography>
                <Typography
                  variant="caption"
                  component="p"
                  sx={{ color: style.color, mt: 0.5, lineHeight: 1.6 }}
                >
                  {data.total > 0
                    ? `${formatRatio(value / data.total)} do total`
                    : 'Participação indisponível'}
                </Typography>
                {comparison && (
                  <CountDelta
                    change={comparison.changes[field]}
                    previous={comparison.previous[field]}
                  />
                )}
              </Box>
            </Paper>
          );
        })}
      </Box>
      <Box
        sx={{
          display: 'grid',
          gridTemplateColumns: { xs: '1fr', sm: '1fr 1fr 1.4fr' },
          border: '1px solid #E4E9EE',
          bgcolor: 'white',
          borderRadius: 2.5,
          overflow: 'hidden',
        }}
      >
        {[
          ['Total analisado', formatNumber(data.total, 0)],
          ['Taxa de aprovação', formatRatio(data.approval_rate)],
          ['Última análise', formatDate(data.latest_analysis_at)],
        ].map(([label, value], index) => (
          <Box
            key={label}
            sx={{
              px: 2.5,
              py: 2,
              borderLeft: { sm: index ? '1px solid #EDF0F4' : undefined },
              borderTop: {
                xs: index ? '1px solid #EDF0F4' : undefined,
                sm: 'none',
              },
            }}
          >
            <Typography sx={{ color: 'text.secondary', fontSize: 12, mb: 0.6 }}>
              {label}
            </Typography>
            <Typography
              sx={{
                fontSize: index === 2 ? 14 : 19,
                fontWeight: 600,
                fontVariantNumeric: 'tabular-nums',
              }}
            >
              {value}
            </Typography>
            {comparison && index === 0 && (
              <CountDelta
                change={comparison.changes.total}
                previous={comparison.previous.total}
              />
            )}
            {comparison &&
              index === 1 &&
              (data.total > 0 || comparison.previous.total > 0) && (
                <Typography
                  variant="caption"
                  component="p"
                  color="text.secondary"
                  sx={{ mt: 1 }}
                >
                  Anterior: {formatRatio(comparison.previous.approval_rate)}
                  <br />
                  {comparison.changes.approval_rate_pp === null
                    ? 'Sem base para variação da taxa'
                    : `${signedNumber(comparison.changes.approval_rate_pp)} p.p.`}
                </Typography>
              )}
          </Box>
        ))}
      </Box>
    </Stack>
  );
}
