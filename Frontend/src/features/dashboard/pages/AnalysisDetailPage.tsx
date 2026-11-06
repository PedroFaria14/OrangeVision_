import { Link, useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { z } from 'zod';
import { Page, QueryFeedback } from '@/shared/ui/Page';
import { formatDate, formatNumber, formatRatio } from '@/shared/lib/format';
import { useSession } from '@/features/auth/hooks/useSession';
import { readAnalysis } from '../api/analyses';
import { classifications } from '../model/classification';
import styles from '@/shared/ui/dashboard.module.css';

export default function AnalysisDetailPage() {
  const { id = '' } = useParams();
  const { session } = useSession();
  const valid = z.string().uuid().safeParse(id).success;
  const query = useQuery({
    queryKey: ['private', session?.user.id, 'detail', id],
    queryFn: ({ signal }) => readAnalysis(id, signal),
    enabled: !!session && valid,
  });
  const data = query.data;
  return (
    <Page title="Detalhe da análise">
      <p>
        <Link to="/dashboard/historico">Voltar ao histórico</Link>
      </p>
      {!valid ? (
        <p role="alert">Identificador inválido.</p>
      ) : (
        <QueryFeedback
          pending={query.isPending}
          error={query.error}
          retry={() => void query.refetch()}
        />
      )}
      {data && (
        <>
          <section>
            <h2>Resultado da análise</h2>

            <span
              className={styles.classificationBadge}
              data-classification={data.classification}
            >
              {classifications[data.classification].label}
            </span>

            <dl className={styles.analysisDetails}>
              {[
                ['Identificador', data.id],
                ['Data/hora da análise', formatDate(data.timestamp)],
                ['Dispositivo', data.device_id || 'Não informado'],
                [
                  'Versão da calibração',
                  data.calibration_version || 'Não informada',
                ],
                ...(data.inspection_session_id
                  ? [['Sessão de inspeção', data.inspection_session_id]]
                  : []),
              ].map(([label, value]) => (
                <div key={label}>
                  <dt>{label}</dt>
                  <dd>{value}</dd>
                </div>
              ))}
            </dl>
          </section>

          <section>
            <h2>Métricas visuais</h2>
            <p>Valores calculados pelo processamento e recebidos pela API.</p>

            <dl className={styles.analysisDetails}>
              {[
                [
                  'Proporção de cor laranja',
                  formatRatio(data.metrics.orange_color_ratio),
                ],
                [
                  'Proporção de regiões anormais',
                  formatRatio(data.metrics.abnormal_region_ratio),
                ],
                ['Circularidade', formatNumber(data.metrics.circularity, 3)],
                ['Assimetria', formatRatio(data.metrics.asymmetry)],
                [
                  'Score visual experimental',
                  data.metrics.visual_score === null
                    ? 'Não informado'
                    : `${formatNumber(data.metrics.visual_score)} / 100`,
                ],
              ].map(([label, value]) => (
                <div key={label}>
                  <dt>{label}</dt>
                  <dd>{value}</dd>
                </div>
              ))}
            </dl>

            <p>O traço (—) indica uma métrica não informada.</p>
          </section>

          <section>
            <h2>Justificativa da classificação</h2>
            <p>
              {data.classification_reason ||
                'Justificativa não disponibilizada.'}
            </p>
          </section>

          <p>
            Imagem privada de inspeção e horário real de sincronização não
            disponibilizados nesta API. A classificação considera
            características visuais externas; regiões anormais não constituem
            diagnóstico de doença.
          </p>
        </>
      )}
    </Page>
  );
}
