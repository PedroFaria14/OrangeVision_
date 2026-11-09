import {
  Alert,
  Button,
  Box,
  Paper,
  LinearProgress,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
} from '@mui/material';
import { Link, useLocation } from 'react-router-dom';
import type { Analysis } from '../api/analyses';
import { formatDate, formatNumber } from '@/shared/lib/format';
import { ClassificationBadge } from './ClassificationBadge';
import { Icon } from '@/shared/ui/Icon';

export function AnalysesTable({
  items,
  total,
  offset,
  busy,
  changePage,
  compact = false,
}: {
  items: Analysis[];
  total: number;
  offset: number;
  busy: boolean;
  changePage: (offset: number) => void;
  compact?: boolean;
}) {
  const { search } = useLocation();
  const visibleItems = compact ? items.slice(0, 5) : items;
  const firstRecord = visibleItems.length ? offset + 1 : 0;
  const lastRecord = offset + visibleItems.length;
  return (
    <Paper
      component="section"
      variant="outlined"
      sx={{ overflow: 'hidden', minWidth: 0 }}
    >
      <Stack
        direction="row"
        sx={{
          px: { xs: 2, sm: 3 },
          py: 2,
          justifyContent: 'space-between',
          alignItems: 'center',
          gap: 1,
        }}
      >
        <Box>
          <Typography variant="h6" component="h2">
            {compact ? 'Últimas análises' : 'Histórico de análises'}
          </Typography>
          <Typography variant="caption" color="text.secondary">
            {visibleItems.length
              ? `Exibindo ${formatNumber(firstRecord, 0)}–${formatNumber(lastRecord, 0)} de ${formatNumber(total, 0)} ${total === 1 ? 'análise' : 'análises'}.`
              : `${total} ${total === 1 ? 'registro no recorte' : 'registros no recorte'}`}
          </Typography>
        </Box>
        {compact && (
          <Button
            component={Link}
            to={`/dashboard/historico${search}`}
            endIcon={<Icon name="arrow" sx={{ fontSize: 16 }} />}
            size="small"
          >
            Ver todas
          </Button>
        )}
      </Stack>
      {!items.length ? (
        <Alert severity="info" sx={{ mx: 2, mb: 2 }}>
          Nenhuma análise nesta página. Confira o período e se há registros
          autorizados para sua conta.
        </Alert>
      ) : (
        <TableContainer
          role="region"
          tabIndex={0}
          aria-label="Tabela de análises com rolagem horizontal quando necessário"
          sx={{
            px: { xs: 1, sm: 2 },
            '& .MuiTableCell-root': { px: { xs: 1, sm: 2 }, py: 1.5 },
          }}
        >
          <Table aria-label="Histórico de análises" size="small">
            <TableHead>
              <TableRow>
                <TableCell
                  sx={{ display: { xs: 'none', sm: 'table-cell' }, width: 76 }}
                >
                  Imagem
                </TableCell>
                <TableCell>Data/hora</TableCell>
                <TableCell>Classificação</TableCell>
                <TableCell>Score experimental</TableCell>
                {!compact && (
                  <TableCell sx={{ display: { xs: 'none', lg: 'table-cell' } }}>
                    Dispositivo
                  </TableCell>
                )}
                <TableCell>Consulta</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {visibleItems.map((item) => (
                <TableRow
                  key={item.id}
                  sx={{
                    '&:last-child td': { borderBottom: 0 },
                    '&:hover': { bgcolor: '#FAFCFD' },
                  }}
                >
                  <TableCell sx={{ display: { xs: 'none', sm: 'table-cell' } }}>
                    <Box
                      role="img"
                      aria-label="Imagem não disponibilizada"
                      sx={{
                        width: 42,
                        height: 42,
                        bgcolor: '#F2F5F7',
                        border: '1px solid #E7ECF0',
                        borderRadius: 1.5,
                        display: 'grid',
                        placeItems: 'center',
                        color: '#8A98A7',
                      }}
                    >
                      <Icon name="image" sx={{ fontSize: 21 }} />
                    </Box>
                  </TableCell>
                  <TableCell>
                    <Typography sx={{ fontSize: 12, lineHeight: 1.6 }}>
                      {formatDate(item.timestamp)}
                    </Typography>
                    <Typography
                      variant="caption"
                      component="p"
                      title={item.id}
                      sx={{
                        color: 'text.secondary',
                        fontSize: 12,
                        mt: 0.3,
                        letterSpacing: 0.3,
                      }}
                    >
                      {item.id.slice(0, 8)}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <ClassificationBadge value={item.classification} />
                  </TableCell>
                  <TableCell>
                    <Typography
                      sx={{
                        fontSize: 13,
                        fontWeight: 550,
                        fontVariantNumeric: 'tabular-nums',
                      }}
                    >
                      {formatNumber(item.metrics.visual_score)}{' '}
                      <Box
                        component="span"
                        sx={{
                          color: 'text.secondary',
                          fontWeight: 400,
                          fontSize: 12,
                        }}
                      >
                        / 100
                      </Box>
                    </Typography>
                    {item.metrics.visual_score !== null && (
                      <LinearProgress
                        variant="determinate"
                        value={item.metrics.visual_score}
                        aria-label={`Score experimental ${formatNumber(item.metrics.visual_score)} de 100`}
                        sx={{
                          mt: 0.7,
                          height: 3,
                          borderRadius: 1,
                          bgcolor: '#F0F2F5',
                          maxWidth: 80,
                          '& .MuiLinearProgress-bar': { bgcolor: '#899BA9' },
                        }}
                      />
                    )}
                  </TableCell>
                  {!compact && (
                    <TableCell
                      sx={{
                        display: { xs: 'none', lg: 'table-cell' },
                        maxWidth: 150,
                      }}
                    >
                      <Typography
                        sx={{
                          fontSize: 12,
                          color: 'text.secondary',
                          overflowWrap: 'anywhere',
                        }}
                      >
                        {item.device_id || 'Não informado'}
                      </Typography>
                    </TableCell>
                  )}
                  <TableCell>
                    <Button
                      component={Link}
                      to={`/dashboard/analises/${item.id}`}
                      aria-label={`Ver detalhes da análise ${item.id}`}
                      sx={{ minWidth: 44, p: 1 }}
                    >
                      <Icon name="eye" sx={{ fontSize: 18 }} />
                      <Box
                        component="span"
                        sx={{
                          display: { xs: 'none', lg: 'inline' },
                          ml: 1,
                          fontSize: 12,
                        }}
                      >
                        Detalhes
                      </Box>
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}
      {!compact && total > 0 && (
        <Stack
          component="nav"
          aria-label="Paginação do histórico"
          direction="row"
          sx={{
            p: 2,
            gap: 1,
            alignItems: 'center',
            justifyContent: 'flex-end',
            flexWrap: 'wrap',
            borderTop: '1px solid #EDF0F4',
          }}
        >
          <Button
            disabled={!offset || busy}
            onClick={() => changePage(Math.max(0, offset - 20))}
          >
            Anterior
          </Button>
          <Typography variant="body2">
            Página {Math.floor(offset / 20) + 1}
          </Typography>
          <Button
            disabled={offset + 20 >= total || busy}
            onClick={() => changePage(offset + 20)}
          >
            Próxima
          </Button>
        </Stack>
      )}
    </Paper>
  );
}
