import {
  Alert,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Button,
  MenuItem,
  Paper,
  Stack,
  TextField,
  Typography,
  useMediaQuery,
} from '@mui/material';
import { useState } from 'react';
import type { Filters } from '../api/analyses';
import { previousCalendarDay, recentPeriod } from '../model/period';
import { useFilterForm } from '../hooks/useFilterForm';
import { Icon } from '@/shared/ui/Icon';

// Datas de calendário sempre em São Paulo. O contrato usa início inclusivo/fim exclusivo.
export function FilterBar({
  filters,
  apply,
}: {
  filters: Filters;
  apply: (filters: Filters) => void;
}) {
  const { error, handleSubmit } = useFilterForm(apply);
  const mobile = useMediaQuery('(max-width:599px)');
  const [customExpanded, setCustomExpanded] = useState(false);
  const endDate = filters.end ? previousCalendarDay(filters.end) : '';
  return (
    <Paper variant="outlined" sx={{ p: { xs: 2, sm: 2.5 } }}>
      <Stack spacing={2} component="form" onSubmit={handleSubmit}>
        <Typography
          sx={{
            fontSize: 12,
            color: 'text.secondary',
            fontWeight: 600,
            letterSpacing: 0.4,
          }}
        >
          Período de análise
        </Typography>
        <Stack direction="row" sx={{ gap: 1, flexWrap: 'wrap' }}>
          {[
            [1, 'Hoje'],
            [7, '7 dias'],
            [30, '30 dias'],
          ].map(([days, label]) => (
            <Button
              key={days}
              type="button"
              variant="outlined"
              size="small"
              onClick={() =>
                apply({ ...filters, ...recentPeriod(Number(days)) })
              }
            >
              {label}
            </Button>
          ))}
          <Button
            type="button"
            size="small"
            onClick={() => apply({ ...recentPeriod(30), classification: '' })}
          >
            Limpar filtros
          </Button>
        </Stack>
        <Accordion
          expanded={!mobile || customExpanded}
          onChange={(_, expanded) => setCustomExpanded(expanded)}
          slots={{ heading: 'h2' }}
          disableGutters
          elevation={0}
          sx={{ '&:before': { display: 'none' } }}
        >
          <AccordionSummary
            sx={{ display: { xs: 'flex', sm: 'none' } }}
            aria-controls="filtros-personalizados"
            id="titulo-filtros-personalizados"
          >
            <Typography variant="body2">
              Personalizar datas e classificação
            </Typography>
          </AccordionSummary>
          <AccordionDetails id="filtros-personalizados" sx={{ p: 0 }}>
            <Stack
              sx={{
                display: 'grid',
                gridTemplateColumns: {
                  xs: 'minmax(0,1fr)',
                  sm: 'repeat(2,minmax(0,1fr))',
                  lg: '1fr 1fr 1fr auto',
                },
                gap: 2,
                alignItems: 'start',
              }}
            >
              <TextField
                label="Data inicial"
                name="start"
                type="date"
                defaultValue={filters.start.slice(0, 10)}
                required
                slotProps={{ inputLabel: { shrink: true } }}
              />
              <TextField
                label="Data final (inclusive)"
                name="end"
                type="date"
                defaultValue={endDate}
                required
                slotProps={{ inputLabel: { shrink: true } }}
              />
              <TextField
                label="Classificação"
                name="classification"
                select
                defaultValue={filters.classification}
                sx={{ minWidth: 160 }}
                slotProps={{
                  inputLabel: { shrink: true },
                  select: { displayEmpty: true },
                }}
              >
                <MenuItem value="">Todas</MenuItem>
                <MenuItem value="APROVADA">Aprovada</MenuItem>
                <MenuItem value="ATENCAO">Atenção</MenuItem>
                <MenuItem value="REVISAR">Revisar</MenuItem>
              </TextField>
              <Button
                type="submit"
                variant="contained"
                startIcon={<Icon name="search" sx={{ fontSize: 18 }} />}
                sx={{ minHeight: 48 }}
              >
                Aplicar filtros
              </Button>
            </Stack>
            {error && <Alert severity="error">{error}</Alert>}
          </AccordionDetails>
        </Accordion>
      </Stack>
    </Paper>
  );
}
