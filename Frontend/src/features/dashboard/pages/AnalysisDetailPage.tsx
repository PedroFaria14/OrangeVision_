import { Link, useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { z } from 'zod';
import { Page, QueryFeedback } from '@/shared/ui/Page';
import { formatDate, formatNumber, formatRatio } from '@/shared/lib/format';
import { useSession } from '@/features/auth/hooks/useSession';
import { readAnalysis } from '../api/analyses';
import { classifications } from '../model/classification';

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
          <h2>{classifications[data.classification].label}</h2>
          <dl>
            {[
              ['ID', data.id],
              ['Data/hora', formatDate(data.timestamp)],
              ['Dispositivo', data.device_id || 'Não informado'],
              ['Calibração', data.calibration_version || 'Não informada'],
              [
                'Proporção de cor',
                formatRatio(data.metrics.orange_color_ratio),
              ],
              [
                'Regiões anormais',
                formatRatio(data.metrics.abnormal_region_ratio),
              ],
              ['Circularidade', formatNumber(data.metrics.circularity, 3)],
              ['Assimetria', formatRatio(data.metrics.asymmetry)],
              ['Score experimental', formatNumber(data.metrics.visual_score)],
            ].map(([label, value]) => (
              <div key={label}>
                <dt>{label}</dt>
                <dd>{value}</dd>
              </div>
            ))}
          </dl>
          {data.inspection_session_id && (
            <p>Sessão de inspeção: {data.inspection_session_id}</p>
          )}
          <p>
            {data.classification_reason
              ? `Justificativa registrada: ${data.classification_reason}`
              : 'Justificativa não disponibilizada.'}
          </p>
          <p>
            Imagem privada de inspeção e horário real de sincronização não
            disponibilizados nesta API. Regiões anormais não constituem
            diagnóstico de doença.
          </p>
        </>
      )}
    </Page>
  );
}
