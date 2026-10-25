import { Link } from 'react-router-dom';
import { Page, QueryFeedback } from '@/shared/ui/Page';
import { formatDate, formatRatio } from '@/shared/lib/format';
import { useInspectionConfig } from '@/features/inspection/hooks/useInspectionConfig';
import { apiEnabled, useDashboard } from '../hooks/useAnalyses';
import {
  useDashboardFilters,
  useValidHistoryPage,
} from '../hooks/useDashboardFilters';
import { FilterBar } from '../components/FilterBar';
import { AnalysesTable } from '../components/AnalysesTable';
import { ComparisonTable } from '../components/ComparisonTable';
import { TableRegion } from '@/shared/ui/TableRegion';
import styles from '@/shared/ui/dashboard.module.css';

export default function DashboardPage({
  historyOnly = false,
}: {
  historyOnly?: boolean;
}) {
  const view = useDashboardFilters(historyOnly);
  const { filters, offset } = view;
  const { analyses, summary, series, comparison } = useDashboard(
    offset,
    filters,
    !historyOnly,
  );
  const inspection = useInspectionConfig();
  useValidHistoryPage(analyses.data?.total, offset);
  const refresh = () => {
    void analyses.refetch();
    if (!historyOnly) {
      void comparison.refetch();
      void series.refetch();
    }
  };
  return (
    <Page
      title={historyOnly ? 'Histórico de análises' : 'Dashboard'}
      description="Dados autorizados da sua conta."
    >
      <button
        onClick={refresh}
        disabled={
          !apiEnabled ||
          analyses.isFetching ||
          (!historyOnly && (comparison.isFetching || series.isFetching))
        }
      >
        Atualizar consultas
      </button>
      {!view.valid && (
        <p role="alert">
          Período da URL inválido. Exibindo os últimos 30 dias; aplique os
          filtros para corrigir.
        </p>
      )}
      <FilterBar
        key={`${filters.start}|${filters.end}|${filters.classification}`}
        filters={filters}
        apply={view.apply}
      />
      {historyOnly && inspection.data && (
        <p>
          {inspection.data.ownership === 'inspection-session'
            ? 'Modo por sessão: somente análises das suas sessões. Registros antigos sem sessão não recebem proprietário automaticamente.'
            : 'Modo legado: registros sem sessão de equipamentos autorizados. Registros pessoais não são expostos neste modo.'}
        </p>
      )}
      {!apiEnabled ? (
        <p role="alert">Integração desativada. Nenhuma simulação é exibida.</p>
      ) : (
        <>
          {!historyOnly && (
            <>
              <QueryFeedback
                pending={summary.isPending}
                error={summary.error}
                retry={() => void comparison.refetch()}
              />
              {summary.data && (
                <section>
                  <h2>Indicadores do período</h2>
                  <dl className={styles.metrics}>
                    <div className={styles.metric}>
                      <dt>Total analisado</dt>
                      <dd>{summary.data.total}</dd>
                    </div>
                    <div className={`${styles.metric} ${styles.approved}`}>
                      <dt>Aprovadas</dt>
                      <dd>{summary.data.approved}</dd>
                    </div>
                    <div className={`${styles.metric} ${styles.attention}`}>
                      <dt>Atenção</dt>
                      <dd>{summary.data.attention}</dd>
                    </div>
                    <div className={`${styles.metric} ${styles.review}`}>
                      <dt>Revisar</dt>
                      <dd>{summary.data.review}</dd>
                    </div>
                  </dl>
                  <dl className={styles.metadata}>
                    <div>
                      <dt>Taxa de aprovação</dt>
                      <dd>{formatRatio(summary.data.approval_rate)}</dd>
                    </div>
                    <div>
                      <dt>Última análise</dt>
                      <dd>{formatDate(summary.data.latest_analysis_at)}</dd>
                    </div>
                  </dl>
                </section>
              )}
              {comparison.data && <ComparisonTable data={comparison.data} />}
              <QueryFeedback
                pending={series.isPending}
                error={series.error}
                retry={() => void series.refetch()}
              />
              {series.data && (
                <section>
                  <h2>Evolução diária das análises</h2>
                  <p>
                    Horário de Brasília. Apenas dias observados; dia ausente não
                    significa zero confirmado.
                  </p>
                  {series.data.items.length === 0 ? (
                    <p>Nenhuma análise observada no período.</p>
                  ) : (
                    <TableRegion label="Rolagem da evolução diária">
                      <table>
                        <caption>Evolução diária das análises</caption>
                        <thead>
                          <tr>
                            {['Data', 'Aprovada', 'Atenção', 'Revisar'].map(
                              (label) => (
                                <th scope="col" key={label}>
                                  {label}
                                </th>
                              ),
                            )}
                          </tr>
                        </thead>
                        <tbody>
                          {series.data.items.map((item) => (
                            <tr key={item.start}>
                              <td>{formatDate(item.start).split(',')[0]}</td>
                              <td>{item.approved}</td>
                              <td>{item.attention}</td>
                              <td>{item.review}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </TableRegion>
                  )}
                </section>
              )}
            </>
          )}
          <QueryFeedback
            pending={analyses.isPending}
            error={analyses.error}
            retry={() => void analyses.refetch()}
          />
          {analyses.data && (
            <>
              <AnalysesTable
                items={analyses.data.items}
                total={analyses.data.total}
                offset={offset}
                busy={analyses.isFetching}
                changePage={view.changePage}
                compact={!historyOnly}
              />
              <p>Histórico consultado: {formatDate(analyses.data.as_of)}.</p>
            </>
          )}
          {!historyOnly && (
            <p>
              <Link to={`/dashboard/historico${window.location.search}`}>
                Ver histórico completo
              </Link>
            </p>
          )}
          {!historyOnly && summary.data && (
            <p>Resumo consultado: {formatDate(summary.data.as_of)}.</p>
          )}
        </>
      )}
      <p>
        Horário de consulta não é horário de sincronização. Inspeção
        experimental: falhas de aquisição não são classificadas como Revisar.
      </p>
    </Page>
  );
}
