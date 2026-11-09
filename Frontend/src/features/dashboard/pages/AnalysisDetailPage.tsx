import { Button } from '@mui/material';
import { Link, useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { z } from 'zod';
import { Page } from '@/shared/ui/Page';
import { useSession } from '@/features/auth/hooks/useSession';
import { readAnalysis } from '../api/analyses';
import { AnalysisDetails } from '../components/AnalysisDetails';
import { QueryFeedback } from '../components/QueryFeedback';

export default function AnalysisDetailPage() {
  const { id = '' } = useParams();
  const { session } = useSession();
  const valid = z.string().uuid().safeParse(id).success;
  const query = useQuery({
    queryKey: ['private', session?.user.id, 'detail', id],
    queryFn: ({ signal }) => readAnalysis(id, signal),
    enabled: !!session && valid,
  });
  return (
    <Page
      title="Detalhe da análise"
      description="Métricas experimentais e rastreabilidade do registro."
    >
      <Button component={Link} to="/dashboard/historico">
        Voltar ao histórico
      </Button>
      <QueryFeedback
        pending={valid && query.isPending}
        error={valid ? query.error : new Error('Identificador inválido')}
        retry={() => void query.refetch()}
      />
      {query.data && <AnalysisDetails data={query.data} />}
    </Page>
  );
}
