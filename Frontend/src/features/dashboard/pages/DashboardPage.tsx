import { Alert, Box, Button, Stack, Typography } from '@mui/material';
import { Page } from '@/shared/ui/Page';
import { formatDate } from '@/shared/lib/format';
import { apiEnabled, useDashboard } from '../hooks/useAnalyses';
import { FilterBar } from '../components/FilterBar';
import { MetricCards } from '../components/MetricCards';
import { DistributionChart, TimelineChart } from '../components/AnalysisCharts';
import { AnalysesTable } from '../components/AnalysesTable';
import { QueryFeedback } from '../components/QueryFeedback';
import {
  useDashboardFilters,
  useValidHistoryPage,
} from '../hooks/useDashboardFilters';
import { Icon } from '@/shared/ui/Icon';
import { PeriodComparison } from '../components/PeriodComparison';
import { useSession } from '@/features/auth/hooks/useSession';
import { previousCalendarDay } from '../model/period';
import { useInspectionConfig } from '@/features/inspection/hooks/useInspectionConfig';
export default function DashboardPage({
  historyOnly = false,
}: {
  historyOnly?: boolean;
}) {
  const view = useDashboardFilters(historyOnly);
  const { session } = useSession();
  const inspectionConfig = useInspectionConfig();
  const firstName = session?.user.name.trim().split(/\s+/)[0];
  const { filters, offset } = view;
  const { analyses, summary, series, comparison } = useDashboard(
    offset,
    filters,
    !historyOnly,
  );
  useValidHistoryPage(analyses.data?.total, offset);
  const refresh = (
    <Button
      variant="outlined"
      startIcon={<Icon name="refresh" sx={{ fontSize: 17 }} />}
      disabled={
        !apiEnabled ||
        analyses.isFetching ||
        summary.isFetching ||
        series.isFetching ||
        comparison.isFetching
      }
      onClick={() => {
        void analyses.refetch();
        if (!historyOnly) {
          void summary.refetch();
          void series.refetch();
        }
      }}
    >
      Atualizar consultas
    </Button>
  );
  return (
    <Page
      title={
        historyOnly
          ? 'Análises'
          : firstName
            ? `Bem-vindo, ${firstName}!`
            : 'Bem-vindo!'
      }
      description={
        historyOnly
          ? 'Consulte e explore os registros de triagem autorizados.'
          : 'Acompanhe suas análises e os resultados da triagem.'
      }
      eyebrow={historyOnly ? 'REGISTROS DE TRIAGEM' : 'VISÃO GERAL'}
      action={refresh}
    >
      {!view.valid && (
        <Alert severity="warning">
          Período da URL inválido. Exibindo os últimos 30 dias; aplique os
          filtros para corrigir a URL.
        </Alert>
      )}
      <FilterBar
        key={`${filters.start}|${filters.end}|${filters.classification}`}
        filters={filters}
        apply={view.apply}
      />
      {historyOnly && inspectionConfig.data && (
        <Alert severity="info">
          {inspectionConfig.data.ownership === 'inspection-session'
            ? 'Modo por sessão: este histórico mostra análises pertencentes às suas sessões de inspeção. Registros antigos sem sessão não são atribuídos automaticamente à sua conta.'
            : 'Modo legado: este histórico mostra registros sem sessão dos equipamentos autorizados para sua conta. Análises pessoais vinculadas a sessões não são expostas por esse modo.'}
        </Alert>
      )}
      <Typography
        sx={{ color: 'text.secondary', fontSize: 12, mt: '8px !important' }}
      >
        Período: {formatDate(filters.start).split(',')[0]} até{' '}
        {previousCalendarDay(filters.end).split('-').reverse().join('/')} ·
        horário de Brasília.{' '}
        {filters.classification
          ? `Classe: ${filters.classification}.`
          : 'Todas as classes.'}
      </Typography>
      {!apiEnabled ? (
        <Alert severity="warning">
          Integração desativada na configuração pública. Nenhuma simulação é
          exibida.
        </Alert>
      ) : (
        <>
          {!historyOnly && (
            <>
              <QueryFeedback
                pending={summary.isPending}
                error={summary.error}
                stale={!!summary.data}
                retry={() => void summary.refetch()}
              />
              {summary.data && (
                <>
                  {comparison.data?.current.in_progress && (
                    <Typography variant="caption" color="text.secondary">
                      Período atual em andamento · valores parciais até{' '}
                      {formatDate(comparison.data.current.observed_end)}.
                    </Typography>
                  )}
                  <MetricCards
                    data={summary.data}
                    comparison={comparison.data}
                  />
                </>
              )}
            </>
          )}
          {!historyOnly && (
            <Stack spacing={2}>
              <Box sx={{ pt: 1 }}>
                <Typography
                  component="h2"
                  sx={{ fontSize: 18, fontWeight: 650, mb: 0.5 }}
                >
                  Estatísticas do período
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Distribuição e evolução das análises no mesmo recorte.
                </Typography>
              </Box>
              <QueryFeedback
                pending={series.isPending}
                error={series.error}
                stale={!!series.data}
                retry={() => void series.refetch()}
              />
              <Box
                sx={{
                  display: 'grid',
                  gridTemplateColumns: {
                    xs: 'minmax(0,1fr)',
                    lg: 'minmax(0,1fr) minmax(0,1.3fr)',
                  },
                  gap: 2.5,
                  alignItems: 'start',
                }}
              >
                {summary.data && <DistributionChart data={summary.data} />}{' '}
                {series.data && <TimelineChart data={series.data} />}
              </Box>
            </Stack>
          )}
          {!historyOnly && comparison.data && (
            <PeriodComparison data={comparison.data} />
          )}
          <Box>
            <QueryFeedback
              pending={analyses.isPending}
              error={analyses.error}
              stale={!!analyses.data}
              retry={() => void analyses.refetch()}
            />
            {analyses.data && (
              <Stack spacing={2}>
                <AnalysesTable
                  items={analyses.data.items}
                  total={analyses.data.total}
                  offset={offset}
                  busy={analyses.isFetching}
                  changePage={view.changePage}
                  compact={!historyOnly}
                />
              </Stack>
            )}
          </Box>
          {(analyses.data || (!historyOnly && summary.data)) && (
            <Box component="aside" aria-label="Atualização das consultas">
              {analyses.data && (
                <Typography
                  variant="caption"
                  component="p"
                  color="text.secondary"
                >
                  Histórico consultado: {formatDate(analyses.data.as_of)}.
                </Typography>
              )}
              {!historyOnly && summary.data && (
                <Typography
                  variant="caption"
                  component="p"
                  color="text.secondary"
                >
                  Resumo consultado: {formatDate(summary.data.as_of)}.
                </Typography>
              )}
              <Typography variant="caption" color="text.secondary">
                Consultas independentes podem ter horários diferentes. Esses
                horários não indicam a última sincronização do equipamento.
              </Typography>
            </Box>
          )}
        </>
      )}
      <Stack
        direction="row"
        sx={{
          gap: 1,
          alignItems: 'flex-start',
          pt: 1,
          borderTop: 1,
          borderColor: 'divider',
        }}
      >
        <Icon
          name="info"
          sx={{ fontSize: 15, color: 'text.secondary', mt: 0.2 }}
        />
        <Typography variant="caption" color="text.secondary">
          Inspeção visual experimental. Taxa de aprovação não é acurácia; falhas
          de aquisição não são classificadas como Revisar. Informações remotas
          não indicam câmera ao vivo.
        </Typography>
      </Stack>
    </Page>
  );
}
