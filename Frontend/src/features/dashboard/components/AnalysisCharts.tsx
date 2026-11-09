import {
  Alert,
  Box,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  useMediaQuery,
} from '@mui/material';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import type { Summary, Series } from '../api/analyses';
import { formatDate, formatNumber, formatRatio } from '@/shared/lib/format';
import { ChartPanel } from './ChartPanel';

export function DistributionChart({ data }: { data: Summary }) {
  const reduced = useMediaQuery('(prefers-reduced-motion: reduce)');
  if (data.total === 0) {
    return (
      <ChartPanel
        title="Distribuição por classificação"
        description="Participação das classes no período selecionado."
      >
        <Alert severity="info">
          Nenhuma análise neste período. A distribuição aparecerá quando houver
          registros.
        </Alert>
      </ChartPanel>
    );
  }
  const values = [
    { name: 'Aprovada', count: data.approved, color: '#15803D' },
    { name: 'Atenção', count: data.attention, color: '#F97316' },
    { name: 'Revisar', count: data.review, color: '#B91C1C' },
  ];
  return (
    <ChartPanel
      title="Distribuição por classificação"
      description="Quantidade e participação no recorte filtrado. A distribuição também respeita o filtro de classe."
    >
      <Box sx={{ height: 220, width: '100%', minWidth: 0 }}>
        <ResponsiveContainer>
          <BarChart data={values} layout="vertical" accessibilityLayer>
            <XAxis type="number" allowDecimals={false} />
            <YAxis type="category" dataKey="name" width={75} />
            <Tooltip
              formatter={(value) =>
                typeof value === 'number'
                  ? `${formatNumber(value, 0)} · ${formatRatio(value / data.total)}`
                  : value
              }
            />
            <Bar name="Análises" dataKey="count" isAnimationActive={!reduced}>
              {values.map((item) => (
                <Cell
                  key={item.name}
                  fill={item.color}
                  stroke={item.name === 'Atenção' ? '#B7470B' : item.color}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </Box>
      <TableContainer
        role="region"
        tabIndex={0}
        aria-label="Distribuição por classificação com rolagem horizontal"
      >
        <Table size="small" aria-label="Distribuição por classificação">
          <TableHead>
            <TableRow>
              <TableCell>Classe</TableCell>
              <TableCell>Quantidade</TableCell>
              <TableCell>Percentual</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {values.map((item) => (
              <TableRow key={item.name}>
                <TableCell component="th" scope="row">
                  {item.name}
                </TableCell>
                <TableCell>{item.count}</TableCell>
                <TableCell>
                  {formatRatio(data.total ? item.count / data.total : null)}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </ChartPanel>
  );
}
export function TimelineChart({ data }: { data: Series }) {
  const reduced = useMediaQuery('(prefers-reduced-motion: reduce)');
  const values = data.items.map((item) => ({
    ...item,
    label: formatDate(item.start).slice(0, 10),
  }));
  return (
    <ChartPanel
      title="Evolução das análises"
      description="Contagens diárias em America/Sao_Paulo. Apenas dias observados; dias ausentes não representam zero confirmado."
    >
      {!values.length ? (
        <Alert severity="info">Nenhuma análise observada no período.</Alert>
      ) : (
        <>
          <Box sx={{ height: 300, width: '100%', minWidth: 0 }}>
            <ResponsiveContainer>
              <BarChart data={values} accessibilityLayer>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="label" minTickGap={35} />
                <YAxis allowDecimals={false} />
                <Tooltip />
                <Legend
                  formatter={(value) => (
                    <span style={{ color: '#46576A', fontSize: 12 }}>
                      {value}
                    </span>
                  )}
                />
                <Bar
                  dataKey="approved"
                  name="Aprovada"
                  stackId="classes"
                  fill="#15803D"
                  isAnimationActive={!reduced}
                />
                <Bar
                  dataKey="attention"
                  name="Atenção"
                  stackId="classes"
                  fill="#F97316"
                  stroke="#B7470B"
                  isAnimationActive={!reduced}
                />
                <Bar
                  dataKey="review"
                  name="Revisar"
                  stackId="classes"
                  fill="#B91C1C"
                  isAnimationActive={!reduced}
                />
              </BarChart>
            </ResponsiveContainer>
          </Box>
          <Box component="details">
            <Box component="summary" sx={{ cursor: 'pointer', py: 1 }}>
              Consultar dados em tabela
            </Box>
            <TableContainer
              role="region"
              tabIndex={0}
              aria-label="Evolução diária com rolagem"
              sx={{ maxHeight: 320 }}
            >
              <Table size="small" aria-label="Evolução diária das análises">
                <TableHead>
                  <TableRow>
                    {['Data', 'Aprovada', 'Atenção', 'Revisar'].map((label) => (
                      <TableCell key={label} scope="col">
                        {label}
                      </TableCell>
                    ))}
                  </TableRow>
                </TableHead>
                <TableBody>
                  {values.map((item) => (
                    <TableRow key={item.start}>
                      <TableCell component="th" scope="row">
                        {item.label}
                      </TableCell>
                      <TableCell>{item.approved}</TableCell>
                      <TableCell>{item.attention}</TableCell>
                      <TableCell>{item.review}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </Box>
        </>
      )}
    </ChartPanel>
  );
}
