import { Link } from 'react-router-dom';
import { Page } from '@/shared/ui/Page';
import styles from '@/shared/ui/public.module.css';

export default function HomePage() {
  return (
    <Page
      title="OrangeVision"
      description="Visão computacional aplicada à triagem visual externa de laranjas."
    >
      <section>
        <h2>Da imagem ao acompanhamento dos resultados</h2>
        <p>
          O OrangeVision é um protótipo acadêmico que reúne captura de imagens,
          processamento no equipamento e consulta dos resultados em uma
          interface web.
        </p>
        <div className={styles.homeActions}>
          <Link to="/projeto">Conhecer o projeto</Link>
          <Link to="/dashboard">Acessar dashboard</Link>
        </div>
      </section>

      <section>
        <h2>Como funciona</h2>
        <ol className={styles.homeSteps}>
          <li>
            <strong>Captura da imagem</strong>
            <p>
              A câmera registra a aparência externa da fruta em um ambiente de
              iluminação controlada.
            </p>
          </li>
          <li>
            <strong>Processamento local</strong>
            <p>
              O programa Python extrai métricas de cor, regiões anormais,
              circularidade e assimetria para a classificação experimental.
            </p>
          </li>
          <li>
            <strong>Consulta dos resultados</strong>
            <p>
              Após o envio à API, as análises ficam disponíveis ao usuário
              autorizado no dashboard e no histórico.
            </p>
          </li>
        </ol>
      </section>

      <aside>
        <p>
          Protótipo em desenvolvimento e validação. Os resultados dependem da
          calibração e das condições de captura. A análise externa não comprova
          condições internas, comestibilidade ou diagnóstico de doenças.
        </p>
      </aside>
    </Page>
  );
}
