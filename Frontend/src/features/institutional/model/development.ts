// Conteúdo da página Desenvolvimento, conferido com o código do Raspberry (backend/device),
// da Web API (web_api) e com a calibração laranja-cor-v3. Sem sensor, GPIO ou atuadores.

export type Tone = 'orange' | 'green' | 'dark';

export type FlowStep = {
  icon: string;
  title: string;
  text: string;
  tone: Tone;
};

export type InfoCard = {
  icon?: string;
  label?: string;
  title: string;
  text: string;
  tone: Tone;
  tags?: readonly string[];
};

export type CategoryKey = 'APROVADA' | 'ATENCAO' | 'REVISAR';

export type DevelopmentBlock =
  | {
      kind: 'cards';
      title?: string;
      accent: 'top' | 'left';
      columns?: 2 | 3 | 4;
      items: readonly InfoCard[];
    }
  | { kind: 'code'; title: string; text: string }
  | {
      kind: 'table';
      title: string;
      columns: readonly [string, string, string];
      rows: readonly (readonly [string, string, string])[];
    }
  | { kind: 'chain'; title: string; steps: readonly string[]; note?: string }
  | {
      kind: 'categories';
      title: string;
      intro: string;
      items: readonly {
        key: CategoryKey;
        title: string;
        text: string;
        rule: string;
      }[];
      note: string;
    }
  | { kind: 'callout'; title: string; text: string }
  | { kind: 'note'; strong: string; text: string }
  | {
      kind: 'sources';
      title: string;
      items: readonly {
        name: string;
        text: string;
        url: string;
        label: string;
      }[];
    };

export type DevelopmentSection = {
  id: string;
  nav: string;
  eyebrow: string;
  title: string;
  intro: string;
  flow?: readonly FlowStep[];
  blocks: readonly DevelopmentBlock[];
};

export const developmentSections: readonly DevelopmentSection[] = [
  {
    id: 'arquitetura',
    nav: 'Arquitetura',
    eyebrow: 'Desenvolvimento',
    title: 'Arquitetura do OrangeVision',
    intro:
      'O OrangeVision integra captura de imagens, visão computacional, processamento local e uma plataforma Web para inspeção visual de laranjas. O Raspberry Pi captura e avalia cada foto; a Web API registra os resultados e o site permite acompanhar as capturas, conferir a categoria e consultar o histórico.',
    flow: [
      {
        icon: '🍊',
        title: 'Laranja',
        text: 'Fruta posicionada na bancada, sobre fundo liso.',
        tone: 'orange',
      },
      {
        icon: '📷',
        title: 'Câmera',
        text: 'Captura da superfície visível da fruta.',
        tone: 'green',
      },
      {
        icon: '🧠',
        title: 'Raspberry Pi',
        text: 'Captura, avaliação local e envio dos dados.',
        tone: 'dark',
      },
      {
        icon: '☁️',
        title: 'Web API',
        text: 'Backend no Render: recebe e registra as capturas.',
        tone: 'green',
      },
      {
        icon: '🖥️',
        title: 'Site OrangeVision',
        text: 'Histórico, gráficos, conferência e correção.',
        tone: 'orange',
      },
    ],
    blocks: [
      {
        kind: 'cards',
        title: 'Gerenciamento das inspeções',
        accent: 'left',
        columns: 3,
        items: [
          {
            icon: '🚦',
            title: 'Categoria automática',
            text: 'O Raspberry Pi classifica cada laranja como Aprovada, Atenção ou Revisar, com o motivo em texto. No site, a pessoa confere a foto e pode validar ou corrigir.',
            tone: 'orange',
            tags: ['Aprovada', 'Atenção', 'Revisar'],
          },
          {
            icon: '🗄️',
            title: 'Armazenamento de dados',
            text: 'As capturas, avaliações e decisões ficam no PostgreSQL na nuvem, acessado pela Web API. No Pi, um SQLite guarda a fila de fotos ainda não enviadas.',
            tone: 'green',
          },
          {
            icon: '📊',
            title: 'Dashboard Web',
            text: 'O painel mostra o histórico das inspeções, indicadores e a distribuição das categorias registradas.',
            tone: 'orange',
          },
        ],
      },
      {
        kind: 'note',
        strong: 'Edge Computing + Plataforma Web:',
        text: 'o Raspberry Pi captura e executa a análise visual local com OpenCV, YOLOX-S e GrabCut. A plataforma Web centraliza a conferência, a correção e a apresentação dos resultados, sem LEDs, buzzer ou mecanismos físicos de separação.',
      },
    ],
  },
  {
    id: 'hardware',
    nav: 'Hardware',
    eyebrow: 'Desenvolvimento técnico',
    title: 'Hardware e Componentes',
    intro:
      'O OrangeVision usa o Raspberry Pi como unidade central de processamento e uma câmera para fotografar as laranjas. A solução combina computação embarcada, visão computacional e comunicação com a plataforma Web.',
    blocks: [
      {
        kind: 'cards',
        accent: 'top',
        columns: 2,
        items: [
          {
            icon: '🧠',
            label: 'Unidade de processamento',
            title: 'Raspberry Pi',
            text: 'Núcleo computacional do OrangeVision: executa Linux e a aplicação em Python, gerencia a câmera, roda a visão computacional (detecção, recorte e medidas da casca) e se comunica com a Web API para enviar as capturas e os resultados.',
            tone: 'orange',
            tags: ['Linux', 'Python', 'OpenCV', 'Edge Computing'],
          },
          {
            icon: '📷',
            label: 'Aquisição de imagens',
            title: 'Câmera',
            text: 'Captura as fotos usadas na inspeção. A janela da câmera mostra ao vivo o contorno da fruta e um aviso de enquadramento antes da captura; as fotos são processadas no Raspberry Pi e ficam disponíveis no site para conferência.',
            tone: 'green',
            tags: [
              'Captura de imagens',
              'Aviso de enquadramento',
              'Inspeção visual',
            ],
          },
        ],
      },
      {
        kind: 'chain',
        title: 'Integração dos componentes',
        steps: [
          '📷 Câmera',
          '🧠 Raspberry Pi',
          '☁️ Web API',
          '🖥️ Site OrangeVision',
        ],
        note: 'Fluxo de aquisição e disponibilização das imagens no OrangeVision.',
      },
      {
        kind: 'cards',
        accent: 'left',
        columns: 2,
        items: [
          {
            icon: '☁️',
            title: 'Comunicação com a Web API',
            text: 'O Raspberry Pi transmite as fotos e os resultados para o backend no Render, usando a credencial do equipamento e a sessão de inspeção pareada.',
            tone: 'orange',
          },
          {
            icon: '🖥️',
            title: 'Conferência no site',
            text: 'A plataforma mostra cada foto com a categoria — Aprovada, Atenção ou Revisar — e o motivo, e permite validar ou corrigir o resultado.',
            tone: 'green',
          },
        ],
      },
      {
        kind: 'note',
        strong: 'Computação embarcada e visão computacional:',
        text: 'o Raspberry Pi e a câmera são os componentes físicos do OrangeVision. A inspeção é feita por software, com conferência na plataforma Web, sem sensor de presença, buzzer, LEDs ou separação mecânica.',
      },
    ],
  },
  {
    id: 'visao',
    nav: 'Visão computacional',
    eyebrow: 'Processamento de imagem',
    title: 'Visão Computacional',
    intro:
      'As fotos capturadas pela câmera são processadas no Raspberry Pi com detecção, segmentação e medidas da casca. O resultado, com categoria e motivo, é enviado à Web API e aparece no site para conferência.',
    flow: [
      {
        icon: '📷',
        title: 'Captura',
        text: 'Foto obtida pela câmera.',
        tone: 'orange',
      },
      {
        icon: '🔍',
        title: 'Detecção',
        text: 'Localização da laranja com YOLOX-S.',
        tone: 'green',
      },
      {
        icon: '✂️',
        title: 'Segmentação',
        text: 'Recorte da fruta com GrabCut.',
        tone: 'orange',
      },
      {
        icon: '📐',
        title: 'Métricas',
        text: 'Cor, verde e manchas com OpenCV.',
        tone: 'green',
      },
      {
        icon: '☁️',
        title: 'Web API',
        text: 'Envio da categoria e do motivo.',
        tone: 'orange',
      },
      {
        icon: '🖥️',
        title: 'Site',
        text: 'Conferência e correção.',
        tone: 'dark',
      },
    ],
    blocks: [
      {
        kind: 'cards',
        accent: 'left',
        columns: 3,
        items: [
          {
            label: 'Etapa 01',
            title: '📷 Captura da imagem',
            text: 'A câmera fotografa a laranja na bancada. A pessoa captura e confirma o envio, orientada pelo aviso de enquadramento; não há sensor de presença nem acionamento mecânico.',
            tone: 'orange',
          },
          {
            label: 'Etapa 02',
            title: '🔍 Detecção com YOLOX-S',
            text: 'O modelo YOLOX-S localiza a laranja na foto. Quando ele não confirma a fruta (por exemplo, uma laranja verde), o Pi a localiza pela cor sobre o fundo liso. Foto com duas frutas ou com a fruta na borda é recusada, sem categoria.',
            tone: 'green',
          },
          {
            label: 'Etapa 03',
            title: '✂️ Segmentação com GrabCut',
            text: 'A partir da detecção, o GrabCut separa a fruta do fundo e delimita a superfície visível. Pontes finas com objetos do fundo são cortadas antes de medir.',
            tone: 'orange',
          },
          {
            label: 'Etapa 04',
            title: '🎨 Análise de coloração',
            text: 'No espaço de cores HSV, o OpenCV mede quanto da casca está em tom maduro (laranja a amarelo) e quanto está em tom verde.',
            tone: 'green',
          },
          {
            label: 'Etapa 05',
            title: '📐 Manchas e forma',
            text: 'Manchas são pontos bem mais escuros que a casca ao redor; sombra e reflexo de luz não contam. Também são medidas circularidade e assimetria. Métricas que não podem ser calculadas não são inventadas.',
            tone: 'orange',
          },
          {
            label: 'Etapa 06',
            title: '☁️ Integração com o site',
            text: 'A categoria, as métricas e o motivo vão para a Web API no Render. No site, cada captura aparece com a foto e pode ser validada, corrigida ou comparada com a opinião do Gemini.',
            tone: 'green',
          },
        ],
      },
      {
        kind: 'categories',
        title: 'Categorização visual da laranja',
        intro:
          'O Raspberry Pi atribui uma de três categorias; o site apresenta o resultado e permite à pessoa confirmar ou corrigir.',
        items: [
          {
            key: 'APROVADA',
            title: 'Aprovada',
            text: 'Casca madura e limpa, dentro dos critérios de aprovação.',
            rule: '',
          },
          {
            key: 'ATENCAO',
            title: 'Atenção',
            text: 'Casca verde ou ainda “de vez”: merece atenção na inspeção.',
            rule: '',
          },
          {
            key: 'REVISAR',
            title: 'Revisar',
            text: 'Manchas na casca que justificam uma revisão mais detalhada.',
            rule: '',
          },
        ],
        note: 'Quando a imagem não permite uma avaliação confiável, a captura fica sem categoria e mostra o motivo (por exemplo, fruta encostando na borda), para nova foto ou revisão no site.',
      },
      {
        kind: 'note',
        strong: 'Edge Computing e plataforma Web:',
        text: 'o Raspberry Pi executa a captura e a análise visual local. A Web API recebe os dados e o site permite visualizar, conferir e corrigir as inspeções. O sistema não depende de motor, sensor de presença, buzzer, LEDs ou separação física.',
      },
    ],
  },
  {
    id: 'classificacao',
    nav: 'Classificação',
    eyebrow: 'Tomada de decisão',
    title: 'Lógica de Classificação',
    intro:
      'A classificação usa regras explícitas sobre características externas medidas na foto: quanto da casca está madura, quanto está verde e quanto tem manchas. Cada resultado traz o motivo em texto e a versão da calibração usada.',
    blocks: [
      {
        kind: 'cards',
        accent: 'top',
        columns: 4,
        items: [
          {
            icon: '🎨',
            label: 'Métrica 01',
            title: 'Casca madura',
            text: 'Proporção da casca em tons de laranja a amarelo, medida no espaço HSV.',
            tone: 'orange',
          },
          {
            icon: '🟢',
            label: 'Métrica 02',
            title: 'Verde',
            text: 'Proporção da casca em tom verde de verdade (o amarelo iluminado não conta).',
            tone: 'green',
          },
          {
            icon: '🔍',
            label: 'Métrica 03',
            title: 'Manchas',
            text: 'Pontos pelo menos 25% mais escuros que a casca ao redor; sombras e reflexos são ignorados.',
            tone: 'orange',
          },
          {
            icon: '⭕',
            label: 'Métrica 04',
            title: 'Forma',
            text: 'Circularidade e assimetria do contorno, registradas como informação complementar.',
            tone: 'green',
          },
        ],
      },
      {
        kind: 'chain',
        title: 'Fluxo de decisão (nesta ordem)',
        steps: [
          '🟢 Verde ≥ 35% → Atenção',
          '🔍 Manchas ≥ 12% → Revisar',
          '🍊 Boa → Aprovada',
          'Senão → Atenção',
        ],
        note: 'O score visual (0 a 100) também é calculado e registrado, mas a categoria vem dessas regras, que explicam o porquê de cada resultado.',
      },
      {
        kind: 'categories',
        title: 'As três categorias',
        intro:
          'Limites da calibração laranja-cor-v3, ajustados com fotos reais da bancada.',
        items: [
          {
            key: 'APROVADA',
            title: 'Aprovada',
            text: 'Laranja boa: madura e limpa.',
            rule: 'Até 5% de manchas, até 20% de verde e pelo menos 60% de casca madura.',
          },
          {
            key: 'ATENCAO',
            title: 'Atenção',
            text: 'Verde ou ainda “de vez”.',
            rule: '35% ou mais de casca verde, ou qualquer caso que não seja Aprovada nem Revisar.',
          },
          {
            key: 'REVISAR',
            title: 'Revisar',
            text: 'Passou do ponto ou com manchas.',
            rule: '12% ou mais da casca com manchas.',
          },
        ],
        note: 'No site, a categoria aparece em cada amostra e entra nos gráficos. A pessoa pode validar ou corrigir; a correção vira uma nova revisão, sem apagar o registro original.',
      },
      {
        kind: 'callout',
        title: '🧪 Calibração dos limites',
        text: 'Os limites não são arbitrários: ficam num arquivo de calibração conferido com fotos rotuladas (9 de 9 acertos na versão atual) e são ajustados com fotos reais da bancada. Mais fotos rotuladas da própria bancada tornam a calibração mais confiável.',
      },
      {
        kind: 'note',
        strong: 'Importante:',
        text: 'a classificação do OrangeVision é uma triagem visual de características externas. Não substitui análises laboratoriais nem faz diagnóstico de doenças ou da qualidade interna da fruta.',
      },
    ],
  },
  {
    id: 'software',
    nav: 'Software',
    eyebrow: 'Arquitetura de software',
    title: 'Software do OrangeVision',
    intro:
      'O OrangeVision é dividido em três partes que se comunicam pela internet: o equipamento da bancada (Raspberry Pi com câmera), a Web API e o site. O Pi captura e avalia a laranja, a API guarda e publica os resultados e o site mostra o histórico, os gráficos e permite validar cada amostra.',
    blocks: [
      {
        kind: 'code',
        title: 'Estrutura do projeto',
        text: `OrangeVision/
├── backend/device/          # Raspberry Pi (Python)
│   ├── camera_window.py     # janela da câmera e aviso de enquadramento
│   ├── detector.py          # YOLOX-S (ONNX): localiza a laranja
│   ├── segmentation.py      # recorte da fruta e medida de manchas
│   ├── vision.py            # regras Aprovada / Atenção / Revisar
│   ├── samples.py           # fila: analisa e envia os resultados
│   ├── storage.py           # SQLite local (fotos pendentes, sessão)
│   └── calibracao-laranja.json
├── web_api/                 # Web API (FastAPI, no Render)
│   ├── main.py
│   ├── infrastructure/      # amostras, inspeções, decisões, Gemini
│   └── migrations/          # estrutura do PostgreSQL
├── Frontend/                # Site (React + TypeScript, na Vercel)
│   └── src/features/        # inspeções, amostras, dashboard, equipe
└── contracts/               # contrato OpenAPI da API`,
      },
      {
        kind: 'cards',
        accent: 'top',
        columns: 3,
        items: [
          {
            icon: '📷',
            label: 'Equipamento',
            title: 'Raspberry Pi',
            text: 'Janela da câmera com aviso de enquadramento, pareamento com a sessão aberta no site e fila local: sem internet, as fotos ficam guardadas e são enviadas depois.',
            tone: 'orange',
          },
          {
            icon: '👁️',
            label: 'Visão computacional',
            title: 'Avaliação local',
            text: 'O YOLOX-S localiza a laranja e o OpenCV recorta a fruta e mede casca madura, verde e manchas. Regras calibradas definem a categoria, sempre com o motivo.',
            tone: 'green',
          },
          {
            icon: '🔌',
            label: 'Servidor',
            title: 'Web API',
            text: 'FastAPI no Render: login, sessões de inspeção, fila de amostras, publicação nos gráficos, decisões com histórico de revisões e logs de auditoria.',
            tone: 'orange',
          },
          {
            icon: '🗄️',
            label: 'Persistência',
            title: 'Banco de dados',
            text: 'PostgreSQL (Neon) com usuários, equipamentos, fotos, avaliações e análises. No Pi, um SQLite guarda só a fila de envio e a sessão pareada.',
            tone: 'green',
          },
          {
            icon: '📊',
            label: 'Visualização',
            title: 'Site',
            text: 'React + TypeScript com Material UI, na Vercel: inspeções, amostras com foto e motivo, validação pela pessoa, histórico e dashboard com gráficos.',
            tone: 'orange',
          },
          {
            icon: '🤖',
            label: 'Segunda opinião',
            title: 'Gemini',
            text: 'Opcional: roda só quando alguém clica em “Solicitar Gemini” no site. Se discordar da avaliação local, a amostra é sinalizada e a pessoa decide.',
            tone: 'green',
          },
        ],
      },
      {
        kind: 'chain',
        title: 'Comunicação entre os módulos',
        steps: [
          '📷 Câmera (Pi)',
          '🔌 Web API',
          '👁️ Avaliação local (Pi)',
          '🔌 Web API',
          '🗄️ PostgreSQL',
          '📊 Site e gráficos',
        ],
        note: '🤖 O Gemini é chamado sob demanda, a partir do site.',
      },
      {
        kind: 'note',
        strong: 'Stack de software:',
        text: 'Python • OpenCV • YOLOX-S (ONNX) • FastAPI • PostgreSQL • SQLite • React • TypeScript • Material UI • Gemini • Render • Vercel • Linux',
      },
    ],
  },
  {
    id: 'banco',
    nav: 'Banco de dados',
    eyebrow: 'Persistência de dados',
    title: 'Banco de Dados',
    intro:
      'O OrangeVision usa dois bancos com papéis diferentes: o PostgreSQL na nuvem guarda o histórico oficial (fotos, avaliações, decisões e análises) consultado pelo site, e um SQLite no Raspberry Pi funciona como fila local, para que nenhuma foto se perca quando a internet cai.',
    blocks: [
      {
        kind: 'cards',
        accent: 'top',
        columns: 2,
        items: [
          {
            icon: '☁️',
            label: 'Banco principal',
            title: 'PostgreSQL (Neon)',
            text: 'Banco relacional na nuvem, acessado só pela Web API. Guarda usuários, equipamentos, sessões de inspeção, as fotos, as avaliações local e Gemini, as decisões e as análises que alimentam o histórico e os gráficos.',
            tone: 'orange',
          },
          {
            icon: '📦',
            label: 'Fila local',
            title: 'SQLite no Raspberry Pi',
            text: 'Arquivo local no equipamento: guarda as fotos ainda não enviadas, a sessão pareada e o estado de cada envio. Sem internet, as capturas esperam e são enviadas depois, sem duplicar.',
            tone: 'green',
          },
        ],
      },
      {
        kind: 'table',
        title: 'Tabela de análises (PostgreSQL)',
        columns: ['Campo', 'Tipo', 'Informação armazenada'],
        rows: [
          ['id', 'UUID', 'Identificador único da análise.'],
          ['dispositivo_id', 'UUID', 'Equipamento que fez a captura.'],
          [
            'inspection_session_id',
            'UUID',
            'Sessão de inspeção (e operador) de origem da foto.',
          ],
          ['data_hora', 'TIMESTAMPTZ', 'Momento da captura, com fuso horário.'],
          ['classificacao', 'VARCHAR', 'APROVADA, ATENCAO ou REVISAR.'],
          [
            'cor_media',
            'DOUBLE',
            '% da casca em tom maduro (laranja a amarelo).',
          ],
          ['regioes_anormais', 'DOUBLE', '% da casca com manchas.'],
          [
            'circularidade / assimetria',
            'DOUBLE',
            'Medidas da forma do contorno da fruta.',
          ],
          [
            'score_visual',
            'DOUBLE',
            'Índice de 0 a 100 que combina as métricas.',
          ],
          ['classification_reason', 'TEXT', 'Motivo em texto da categoria.'],
          [
            'versao_algoritmo / calibration_version',
            'VARCHAR',
            'Algoritmo e calibração que geraram o resultado.',
          ],
        ],
      },
      {
        kind: 'cards',
        title: 'Outras tabelas',
        accent: 'top',
        columns: 4,
        items: [
          {
            title: 'image_samples',
            text: 'A foto (BYTEA, dentro do banco), a sessão de origem e o estado do processamento.',
            tone: 'orange',
          },
          {
            title: 'sample_evaluations',
            text: 'Avaliações independentes da mesma foto: local (Raspberry) e Gemini.',
            tone: 'green',
          },
          {
            title: 'sample_decisions',
            text: 'Decisões e correções feitas no site, em revisões numeradas, sem apagar as anteriores.',
            tone: 'orange',
          },
          {
            title: 'inspection_sessions · dispositivos · users',
            text: 'Quem abriu cada inspeção, em qual equipamento e por quanto tempo ela autorizou capturas.',
            tone: 'green',
          },
        ],
      },
      {
        kind: 'code',
        title: 'Exemplo de registro (ilustrativo)',
        text: `id:                 3c2db611-…
data_hora:          09/11/2026 14:57:12 -03
classificacao:      APROVADA
cor_media:          78.0 %
regioes_anormais:   0.0 %
calibration:        laranja-cor-v3-20261109
motivo:             Boa: casca 78% laranja, 6% verde, 0% manchas escuras.`,
      },
      {
        kind: 'chain',
        title: 'Fluxo dos dados',
        steps: [
          '📷 Captura',
          '📦 SQLite (fila no Pi)',
          '🔌 Web API',
          '☁️ PostgreSQL',
          '👁️ Avaliação local',
          '🚦 Análise publicada',
          '📊 Site e gráficos',
        ],
      },
      {
        kind: 'cards',
        accent: 'top',
        columns: 4,
        items: [
          {
            icon: '📚',
            title: 'Histórico',
            text: 'Todas as frutas analisadas, com foto e motivo.',
            tone: 'orange',
          },
          {
            icon: '📈',
            title: 'Indicadores',
            text: 'Distribuição das categorias por período e equipamento.',
            tone: 'green',
          },
          {
            icon: '🔎',
            title: 'Rastreabilidade',
            text: 'Cada resultado ligado à foto, à sessão, ao operador e à calibração usada.',
            tone: 'orange',
          },
          {
            icon: '✍️',
            title: 'Correções auditáveis',
            text: 'Validações humanas viram novas revisões; o original é preservado.',
            tone: 'green',
          },
        ],
      },
      {
        kind: 'note',
        strong: 'Engenharia de dados:',
        text: 'cada inspeção deixa de ser uma classificação momentânea e passa a gerar um registro rastreável (foto, avaliações, decisão e versão da calibração) para acompanhamento, comparação e apoio à tomada de decisão.',
      },
    ],
  },
  {
    id: 'integracao',
    nav: 'Integração',
    eyebrow: 'Funcionamento completo',
    title: 'Integração do Sistema',
    intro:
      'A integração conecta o site, a Web API, o banco de dados e o Raspberry Pi em um único ciclo: da inspeção aberta pelo operador até a categoria da laranja aparecer no histórico e nos gráficos, com a pessoa podendo conferir e corrigir cada resultado.',
    flow: [
      {
        icon: '🖥️',
        title: 'Site',
        text: 'Operador abre a inspeção.',
        tone: 'orange',
      },
      {
        icon: '📷',
        title: 'Câmera',
        text: 'Captura com aviso de enquadramento.',
        tone: 'green',
      },
      {
        icon: '🧠',
        title: 'Raspberry Pi',
        text: 'Fila local e envio seguro.',
        tone: 'dark',
      },
      {
        icon: '🔌',
        title: 'Web API',
        text: 'Recebe a foto e organiza a fila.',
        tone: 'green',
      },
      {
        icon: '👁️',
        title: 'YOLOX + OpenCV',
        text: 'Avaliação local no Pi.',
        tone: 'orange',
      },
      {
        icon: '☁️',
        title: 'PostgreSQL',
        text: 'Registra foto e análise.',
        tone: 'green',
      },
      {
        icon: '📊',
        title: 'Dashboard',
        text: 'Histórico, gráficos e validação.',
        tone: 'orange',
      },
    ],
    blocks: [
      {
        kind: 'cards',
        accent: 'left',
        columns: 3,
        items: [
          {
            label: 'Etapa 01',
            title: '🖥️ Abertura da inspeção',
            text: 'No site, o operador escolhe o equipamento e inicia uma inspeção. O site gera um código temporário, válido por 5 minutos.',
            tone: 'orange',
          },
          {
            label: 'Etapa 02',
            title: '🔗 Pareamento',
            text: 'No Raspberry Pi, o código é digitado na janela da câmera. A partir daí, cada foto fica ligada àquela sessão e ao operador que a abriu.',
            tone: 'green',
          },
          {
            label: 'Etapa 03',
            title: '📷 Captura orientada',
            text: 'A janela mostra ao vivo o contorno da fruta e um aviso de enquadramento (borda, tamanho, fundo, luz). A pessoa captura e confirma o envio.',
            tone: 'orange',
          },
          {
            label: 'Etapa 04',
            title: '📦 Envio com fila local',
            text: 'A foto fica na fila do Pi (SQLite) até a Web API confirmar o recebimento. Sem internet, ela espera e é enviada depois, sem duplicar.',
            tone: 'green',
          },
          {
            label: 'Etapa 05',
            title: '👁️ Análise e classificação',
            text: 'O Pi processa a foto: o YOLOX-S localiza a laranja, o OpenCV mede casca madura, verde e manchas, e as regras definem Aprovada, Atenção ou Revisar, com o motivo.',
            tone: 'orange',
          },
          {
            label: 'Etapa 06',
            title: '🗄️ Registro',
            text: 'A Web API grava no PostgreSQL a análise, com data, sessão, equipamento, métricas, motivo e versão da calibração, ligada à foto original.',
            tone: 'green',
          },
          {
            label: 'Etapa 07',
            title: '📊 Dashboard e validação',
            text: 'O resultado aparece em Amostras e nos gráficos. A pessoa pode validar ou corrigir e pedir uma segunda opinião ao Gemini; cada correção vira uma nova revisão.',
            tone: 'orange',
          },
        ],
      },
      {
        kind: 'chain',
        title: 'Ciclo completo do OrangeVision',
        steps: [
          '🖥️ Inspeção aberta',
          '🔗 Pi pareado',
          '📷 Foto capturada',
          '🔌 Web API recebe',
          '👁️ Pi classifica',
          '🗄️ PostgreSQL registra',
          '📊 Dashboard atualiza',
        ],
      },
      {
        kind: 'note',
        strong: 'Integração completa:',
        text: 'o OrangeVision transforma a foto de uma fruta na bancada em uma classificação explicável, registrada e rastreável, que a equipe acompanha e valida pelo site.',
      },
    ],
  },
  {
    id: 'fundamentacao',
    nav: 'Fundamentação',
    eyebrow: 'Fundamentação do projeto',
    title: 'Referências Técnicas',
    intro:
      'A fundamentação técnica reúne referências sobre citricultura e características externas das laranjas. Elas orientam os critérios de inspeção visual e o uso de visão computacional, sem diagnóstico de doenças.',
    blocks: [
      {
        kind: 'cards',
        accent: 'left',
        columns: 2,
        items: [
          {
            label: 'Objeto de estudo',
            title: '🍊 Laranja Pêra-Rio',
            text: 'A laranja Pêra-Rio (Citrus sinensis) contextualiza o objeto de estudo. Na inspeção são observadas coloração, formato, uniformidade da superfície e regiões visualmente diferentes; as condições reais das frutas e das fotos entram na calibração.',
            tone: 'orange',
          },
          {
            label: 'Referência fitossanitária',
            title: '🌱 Fundecitrus — Greening (HLB)',
            text: 'O material do Fundecitrus descreve características que podem estar associadas ao greening, como maturação irregular, coloração manchada, tamanho reduzido e assimetria. Alterações na imagem não permitem, isoladamente, determinar a presença de greening ou de outra doença.',
            tone: 'green',
          },
        ],
      },
      {
        kind: 'cards',
        title: 'Relação com a visão computacional',
        accent: 'top',
        columns: 4,
        items: [
          {
            icon: '🎨',
            title: 'Coloração',
            text: 'Variações de tom na superfície da laranja.',
            tone: 'orange',
            tags: ['OpenCV · HSV · máscaras de cor'],
          },
          {
            icon: '🔍',
            title: 'Regiões anormais',
            text: 'Pontos mais escuros que a casca ao redor, medidos sobre uma segmentação válida.',
            tone: 'green',
            tags: ['OpenCV · contraste local'],
          },
          {
            icon: '⭕',
            title: 'Forma',
            text: 'Contorno externo e circularidade; dependem da qualidade do recorte.',
            tone: 'orange',
            tags: ['OpenCV · contornos'],
          },
          {
            icon: '↔️',
            title: 'Assimetria',
            text: 'Diferenças geométricas entre os lados da fruta.',
            tone: 'green',
            tags: ['OpenCV · análise geométrica'],
          },
        ],
      },
      {
        kind: 'chain',
        title: 'Fundamentação da inspeção visual',
        steps: [
          '📚 Referências técnicas',
          '🔍 Características visuais',
          '📐 Métricas, quando válidas',
          '🖥️ Conferência no site',
        ],
        note: 'As referências orientam os critérios. As métricas só são usadas quando o processamento fornece informação suficiente.',
      },
      {
        kind: 'note',
        strong: 'Escopo do OrangeVision:',
        text: 'as referências sobre doenças dos citros servem apenas de fundamentação para observar características externas. O OrangeVision faz inspeção visual, não diagnóstico fitossanitário, avaliação da qualidade interna ou determinação de comestibilidade. “Revisar” indica necessidade de avaliação adicional, não a confirmação de uma doença.',
      },
      {
        kind: 'sources',
        title: 'Fontes consultadas',
        items: [
          {
            name: 'Fundecitrus',
            text: 'Fundo de Defesa da Citricultura. Greening e psilídeo: características, sintomas, monitoramento e manejo.',
            url: 'https://www.fundecitrus.com.br/pragas-e-doencas/greening-e-psilideo/',
            label: 'Acessar Fundecitrus',
          },
          {
            name: 'Rebrotar Plantas',
            text: 'Laranja Pêra-Rio (Citrus sinensis): referência complementar sobre a cultivar do objeto de estudo.',
            url: 'https://www.rebrotarplantas.com.br/laranja-pera-rio',
            label: 'Acessar Rebrotar Plantas',
          },
        ],
      },
    ],
  },
];
