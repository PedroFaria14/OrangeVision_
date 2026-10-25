import { Link } from 'react-router-dom';
import { Page } from '@/shared/ui/Page';

export default function HomePage() {
  return (
    <Page
      title="OrangeVision"
      description="Triagem visual externa de laranjas e acompanhamento de resultados."
    >
      <p>
        Processamento local no equipamento, armazenamento autorizado na API e
        consulta pessoal neste site.
      </p>
      <p>
        Resultados experimentais dependem da calibração. A análise não comprova
        condições internas ou comestibilidade.
      </p>
      <Link to="/dashboard">Acessar dashboard</Link>
    </Page>
  );
}
