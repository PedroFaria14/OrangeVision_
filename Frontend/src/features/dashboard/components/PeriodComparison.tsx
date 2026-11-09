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
  useMediaQuery,
} from '@mui/material';
import {
  Bar,
  BarChart,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import type { Comparison } from '../api/comparison';
import { formatDate, formatNumber, formatRatio } from '@/shared/lib/format';
import { signedNumber } from '../model/comparison_format';

export function PeriodComparison({ data }: { data: Comparison }) {
  const reduced = useMediaQuery('(prefers-reduced-motion: reduce)');
  const hasData = data.current.total > 0 || data.previous.total > 0;
  const chart = [
    {
      name: 'Aprovadas',
      current: data.current.approved,
      previous: data.previous.approved,
    },
    {
      name: 'Não aprovadas',
      current: data.current.not_approved,
      previous: data.previous.not_approved,
    },
  ];
  const rows = [
    ['Total analisado', 'total'],
    ['Aprovadas', 'approved'],
    ['Atenção', 'attention'],
    ['Revisar', 'review'],
    ['Não aprovadas', 'not_approved'],
  ] as const;
  return (
    <Paper
      component="section"
      variant="outlined"
      sx={{ p: { xs: 2, sm: 3 }, minWidth: 0 }}
    >
      <Stack spacing={2.5}>
        <Box>
          <Typography component="h2" variant="h6">
            Período atual × anterior
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
            Compare a quantidade analisada e o estado das laranjas da sua conta.
          </Typography>
        </Box>
        <Box
          sx={{
            display: 'grid',
            gridTemplateColumns: { xs: '1fr', sm: '1fr 1fr' },
            gap: 2,
          }}
        >
          {[
            { label: 'Período atual', period: data.current },
            { label: 'Período anterior', period: data.previous },
          ].map(({ label, period }) => (
            <Box key={label} sx={{ p: 2, bgcolor: '#F7F9FB', borderRadius: 2 }}>
              <Typography variant="subtitle2">
                {label}
                {period.in_progress ? ' · em andamento' : ''}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {formatDate(period.start)} até {formatDate(period.end)}
                <br />
                Fim exclusivo · America/Sao_Paulo
              </Typography>
            </Box>
          ))}
        </Box>
        {data.current.in_progress && (
          <Alert severity="info">
            Período atual em andamento: os valores são parciais, observados até{' '}
            {formatDate(data.current.observed_end)}. O período anterior já foi
            encerrado.
          </Alert>
        )}
        {!hasData ? (
          <Typography color="text.secondary">
            Ainda não há dados para comparar nos dois períodos selecionados.
          </Typography>
        ) : (
          <Box
            sx={{
              display: 'grid',
              gridTemplateColumns: { xs: 'minmax(0,1fr)', xl: '1fr 1.15fr' },
              gap: 3,
              alignItems: 'center',
            }}
          >
            <Box sx={{ height: 245, minWidth: 0 }}>
              <ResponsiveContainer>
                <BarChart data={chart} layout="vertical" accessibilityLayer>
                  <XAxis type="number" allowDecimals={false} />
                  <YAxis
                    type="category"
                    dataKey="name"
                    width={100}
                    tick={{ fontSize: 12 }}
                  />
                  <Tooltip />
                  <Legend
                    formatter={(value) => (
                      <span style={{ color: '#46576A', fontSize: 12 }}>
                        {value}
                      </span>
                    )}
                  />
                  <Bar
                    name="Atual"
                    dataKey="current"
                    fill="#F97316"
                    stroke="#B7470B"
                    isAnimationActive={!reduced}
                  />
                  <Bar
                    name="Anterior"
                    dataKey="previous"
                    fill="#8396AA"
                    isAnimationActive={!reduced}
                  />
                </BarChart>
              </ResponsiveContainer>
            </Box>
            <TableContainer
              role="region"
              tabIndex={0}
              aria-label="Comparação dos períodos com rolagem horizontal"
            >
              <Table size="small" aria-label="Comparação entre períodos">
                <TableHead>
                  <TableRow>
                    <TableCell>Estado</TableCell>
                    <TableCell>Atual</TableCell>
                    <TableCell>Anterior</TableCell>
                    <TableCell>Diferença absoluta</TableCell>
                    <TableCell>Variação percentual</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {rows.map(([label, key]) => (
                    <TableRow key={key}>
                      <TableCell component="th" scope="row">
                        {label}
                      </TableCell>
                      <TableCell>
                        {formatNumber(data.current[key], 0)}
                      </TableCell>
                      <TableCell>
                        {formatNumber(data.previous[key], 0)}
                      </TableCell>
                      <TableCell>
                        {signedNumber(data.changes[key].absolute, 0)}
                      </TableCell>
                      <TableCell>
                        {data.changes[key].percent === null
                          ? 'Sem base anterior'
                          : `${signedNumber(data.changes[key].percent)}%`}
                      </TableCell>
                    </TableRow>
                  ))}
                  <TableRow>
                    <TableCell component="th" scope="row">
                      Aprovação (%)
                    </TableCell>
                    <TableCell>
                      {formatRatio(data.current.approval_rate)}
                    </TableCell>
                    <TableCell>
                      {formatRatio(data.previous.approval_rate)}
                    </TableCell>
                    <TableCell>
                      {data.changes.approval_rate_pp === null
                        ? '—'
                        : `${signedNumber(data.changes.approval_rate_pp)} p.p.`}
                    </TableCell>
                    <TableCell>Não se aplica</TableCell>
                  </TableRow>
                </TableBody>
              </Table>
            </TableContainer>
          </Box>
        )}
        <Typography variant="caption" color="text.secondary">
          Não aprovadas = Atenção + Revisar. Atenção não significa rejeição
          definitiva. Base anterior zero não gera variação percentual; sem
          análises válidas não há taxa de aprovação. Mesmos filtros e permissões
          nos dois períodos.
        </Typography>
        <Typography variant="caption" color="text.secondary">
          Comparação calculada em {formatDate(data.as_of)}, com a mesma
          referência de consulta para os dois períodos.
        </Typography>
      </Stack>
    </Paper>
  );
}
