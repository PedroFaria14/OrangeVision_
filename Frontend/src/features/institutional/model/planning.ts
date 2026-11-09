// Planejamento fornecido pela equipe; períodos não representam atividades concluídas.
export const planningOverview = {
  title: 'Da ideia à implementação',
  description:
    'O planejamento do OrangeVision organiza as etapas necessárias para o desenvolvimento de um sistema embarcado de triagem visual de laranjas, desde a definição dos requisitos e seleção dos componentes até a implementação da visão computacional, integração do hardware, armazenamento dos dados e validação do protótipo.',
  objective:
    'Desenvolver o OrangeVision de forma estruturada, integrando hardware, software, visão computacional e análise de dados em um protótipo funcional aplicado ao agronegócio.',
} as const;

export const planningQuestions = [
  {
    key: 'what',
    label: 'WHAT',
    question: 'O quê?',
    text: 'Desenvolver um sistema embarcado de triagem visual de laranjas utilizando visão computacional para analisar características e regiões visualmente anormais na superfície das frutas.',
  },
  {
    key: 'why',
    label: 'WHY',
    question: 'Por quê?',
    text: 'Auxiliar na padronização da inspeção visual de laranjas, buscando reduzir a subjetividade do processo e gerar dados que apoiem o acompanhamento da triagem.',
  },
  {
    key: 'where',
    label: 'WHERE',
    question: 'Onde?',
    text: 'Em um ambiente controlado de testes, simulando uma etapa de seleção e inspeção de frutas presente em processos de pós-colheita do agronegócio.',
  },
  {
    key: 'when',
    label: 'WHEN',
    question: 'Quando?',
    text: 'Durante o semestre letivo de 2026, com cronograma previsto de setembro a novembro para planejamento, desenvolvimento, integração, testes e apresentação dos resultados.',
  },
  {
    key: 'who',
    label: 'WHO',
    question: 'Quem?',
    text: 'A equipe OrangeVision, formada por estudantes de Engenharia da Computação da Universidade São Francisco — USF.',
  },
  {
    key: 'how',
    label: 'HOW',
    question: 'Como?',
    text: 'Utilizando Raspberry Pi, câmera, Python e OpenCV para processamento local, SQLite para armazenamento e uma API online com PostgreSQL e dashboard para consulta dos resultados. Sensores e atuadores são extensões opcionais.',
  },
  {
    key: 'cost',
    label: 'HOW MUCH',
    question: 'Quanto?',
    text: 'O custo será determinado pelo levantamento dos componentes e materiais necessários ao protótipo, priorizando equipamentos disponíveis e soluções de baixo custo. O orçamento ainda não foi definido.',
  },
] as const;

export const planningMonths = [
  { id: 'september', label: 'Setembro' },
  { id: 'october', label: 'Outubro' },
  { id: 'november', label: 'Novembro' },
] as const;

type PlanningMonth = (typeof planningMonths)[number]['id'];
type PlanningStage = {
  id: string;
  category: string;
  title: string;
  icon: string;
  description: string;
  months: readonly PlanningMonth[];
};

export const planningStages = [
  {
    id: 'research',
    category: 'Pesquisa',
    title: 'Pesquisa e Definição',
    icon: '🔎',
    description:
      'Estudo sobre triagem de laranjas, visão computacional e características externas relevantes para definir os critérios que serão analisados pelo sistema.',
    months: ['september'],
  },
  {
    id: 'architecture',
    category: 'Arquitetura',
    title: 'Projeto e Arquitetura',
    icon: '📐',
    description:
      'Definição da arquitetura, fluxo de funcionamento, componentes, alimentação, banco de dados e tecnologias. GPIOs, sensores e atuadores serão considerados quando fizerem parte da montagem.',
    months: ['september'],
  },
  {
    id: 'hardware',
    category: 'Hardware',
    title: 'Montagem do Hardware',
    icon: '🔧',
    description:
      'Montagem e configuração do Raspberry Pi e da câmera, incluindo enquadramento, iluminação e alimentação. Sensor ou botão de acionamento, LEDs, buzzer e servo são opcionais e exigem validação elétrica própria quando utilizados.',
    months: ['september', 'october'],
  },
  {
    id: 'vision',
    category: 'Visão computacional',
    title: 'Desenvolvimento da Visão Computacional',
    icon: '👁️',
    description:
      'Desenvolvimento em Python e OpenCV da captura e do processamento das imagens para analisar características externas, como coloração, manchas e regiões visualmente anormais, com referências e calibração da bancada.',
    months: ['october'],
  },
  {
    id: 'software',
    category: 'Software e dados',
    title: 'Software e Dados',
    icon: '💻',
    description:
      'Implementação da classificação experimental Aprovada, Atenção ou Revisar, condicionada à calibração validada, com registro no SQLite, sincronização com a API online e dashboard para acompanhamento dos resultados.',
    months: ['october'],
  },
  {
    id: 'integration',
    category: 'Integração',
    title: 'Integração e Testes',
    icon: '🔗',
    description:
      'Integração entre câmera, processamento, classificação, persistência, sincronização e dashboard. Testes com diferentes frutas e ajustes dos critérios; GPIOs e atuadores entram nos testes somente se instalados.',
    months: ['october', 'november'],
  },
  {
    id: 'validation',
    category: 'Resultados',
    title: 'Validação e Resultados',
    icon: '📊',
    description:
      'Execução do protótipo, registro e análise dos resultados, avaliação dos indicadores e preparação da documentação, fotos, vídeo e apresentação final, explicitando limitações e evidências obtidas.',
    months: ['november'],
  },
] as const satisfies readonly PlanningStage[];

export const planningDeliverables = [
  {
    title: 'Planejamento',
    icon: '📋',
    description:
      'Definição do problema, proposta da solução, setor econômico, ODS, metodologia 5W2H, etapas, cronograma, recursos e levantamento de custos.',
  },
  {
    title: 'Hardware e Esquemático',
    icon: '🔌',
    description:
      'Especificação dos componentes, montagem e documentação das conexões do Raspberry Pi e da câmera, incluindo sensores e atuadores opcionais quando utilizados.',
  },
  {
    title: 'Visão Computacional',
    icon: '👁️',
    description:
      'Processamento local das imagens com Python e OpenCV para análise das características externas das laranjas, acompanhado das referências de calibração.',
  },
  {
    title: 'Software e Código-Fonte',
    icon: '💻',
    description:
      'Código de visão computacional, classificação, persistência e integração dos módulos. Controle de GPIOs e acionamento dos componentes são entregas condicionadas à montagem desses periféricos.',
  },
  {
    title: 'Banco de Dados e Dashboard',
    icon: '📊',
    description:
      'Registro estruturado das análises, sincronização e apresentação de indicadores e resultados no dashboard, com acesso restrito à conta autorizada.',
  },
  {
    title: 'Testes e Resultados',
    icon: '🧪',
    description:
      'Testes com o protótipo, registro das classificações, análise dos resultados e documentação das limitações. Acurácia depende de amostras rotuladas e metodologia de avaliação.',
  },
] as const;

export const planningFlow = [
  'Laranja',
  'Captura',
  'Processamento',
  'Classificação',
  'Registro',
  'Sincronização',
  'Dashboard',
] as const;
