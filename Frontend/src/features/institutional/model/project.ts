export const projectNarrative = [
  {
    id: 'contexto',
    label: '01 · Contexto',
    title: 'Tecnologia aplicada à citricultura',
    accent: 'secondary.main',
    text: 'A citricultura envolve processos de seleção e avaliação visual dos frutos. Coloração, manchas, deformações e irregularidades externas podem ser observadas nesse processo. Técnicas de Visão Computacional podem contribuir para uma inspeção mais padronizada, rastreável e orientada por dados.',
  },
  {
    id: 'problema',
    label: '02 · Problema',
    title: 'Inspeção visual subjetiva e repetitiva',
    accent: 'primary.main',
    text: 'A avaliação visual manual pode apresentar diferenças entre operadores, além de exigir repetição e atenção constante. Isso dificulta a padronização dos critérios utilizados para identificar alterações externas nas frutas.',
  },
] as const;

export const projectSolution = {
  title: 'Sistemas embarcados, visão e dados',
  description:
    'A proposta integra uma câmera a um Raspberry Pi para capturar imagens e executar localmente algoritmos de Visão Computacional com Python e OpenCV. Em condições controladas e com calibração validada, as características externas são transformadas em métricas para apoiar a triagem experimental.',
  record:
    'Cada análise oficial é registrada com UUID, permitindo rastreabilidade e reenvio idempotente. A arquitetura prevê SQLite e outbox no equipamento, sincronização HTTPS com a API autorizada e consulta pessoal dos dados armazenados no PostgreSQL.',
  steps: [
    'Laranja',
    'Câmera',
    'Raspberry Pi + OpenCV',
    'Métricas',
    'Triagem',
    'Registro autorizado',
    'Dashboard',
  ],
  classifications: [
    [
      'Aprovada',
      'Características compatíveis com os critérios visuais calibrados.',
    ],
    [
      'Atenção',
      'Características externas que exigem atenção segundo os critérios experimentais.',
    ],
    ['Revisar', 'Características visuais que merecem uma avaliação adicional.'],
  ],
} as const;

export const projectStudy = {
  title: 'Laranja Pêra-Rio',
  description:
    'A laranja Pêra-Rio, da espécie Citrus sinensis, é a referência para contextualizar o objeto de estudo do OrangeVision. Na fase experimental, as frutas devem ser fotografadas em condições controladas de iluminação e posicionamento para permitir a comparação entre características visuais.',
  availability:
    'A confirmação da variedade utilizada depende da disponibilidade e da identificação das frutas nos testes de bancada.',
} as const;

export const projectMetrics = [
  {
    name: 'Coloração',
    description:
      'Distribuição das tonalidades visíveis, com quantificação da região alaranjada conforme a calibração.',
    symbol: '🎨',
    accent: 'primary.main',
  },
  {
    name: 'Regiões anormais',
    description:
      'Áreas visualmente diferentes da superfície, como manchas, que podem ser quantificadas no processamento da imagem.',
    symbol: '🔍',
    accent: 'secondary.main',
  },
  {
    name: 'Forma e circularidade',
    description:
      'Contorno e regularidade geométrica da região visível da fruta, incluindo possíveis deformações externas.',
    symbol: '⭕',
    accent: 'primary.main',
  },
  {
    name: 'Assimetria',
    description:
      'Diferenças geométricas entre regiões visíveis da fruta, medidas segundo o método de análise adotado.',
    symbol: '↔️',
    accent: 'secondary.main',
  },
] as const;

export const informationSteps = [
  'Características da fruta',
  'Imagem',
  'Processamento',
  'Métricas',
  'Triagem',
  'Dados',
] as const;

export const projectSustainability = {
  title: 'ODS 2 — Fome Zero e Agricultura Sustentável',
  description:
    'O OrangeVision se insere no contexto do setor primário e do agronegócio. Sua relação com o ODS 2 está na aplicação acadêmica de tecnologia para apoiar processos agrícolas e de pós-colheita, explorando o uso de informações estruturadas na triagem visual.',
  target:
    'A meta 2.a destaca investimentos em infraestrutura rural, pesquisa, extensão agrícola e desenvolvimento tecnológico para ampliar a capacidade de produção agrícola nos países em desenvolvimento.',
  application:
    'Nesse contexto, o projeto demonstra a integração de Sistemas Embarcados, Visão Computacional e análise de dados. A relação com o ODS é uma fundamentação da proposta, não uma comprovação de impacto na produção ou na segurança alimentar.',
} as const;

export const projectScope = {
  title: 'Escopo e limitações',
  purpose:
    'O OrangeVision é um protótipo acadêmico de triagem visual de características externas. O objetivo é identificar diferenças observáveis e auxiliar na separação preliminar das frutas.',
  limits:
    'O sistema não realiza diagnóstico fitossanitário, não confirma doenças e não determina integridade interna, sabor, concentração de açúcares, inocuidade ou qualidade sanitária. A categoria Revisar indica a necessidade de avaliação adicional, não um diagnóstico.',
  calibration:
    'Detecção da fruta, score do detector, categoria de qualidade e acurácia são conceitos distintos. Classificação e comparação de resultados exigem calibração; acurácia exige referência rotulada e metodologia validada.',
} as const;

export const projectExpected = {
  title: 'Uma inspeção mais padronizada e rastreável',
  description:
    'Ao final do desenvolvimento e da validação, espera-se obter um protótipo capaz de detectar a presença da fruta, capturar sua imagem, executar a análise visual localmente, gerar uma triagem e registrar os resultados para consulta em dashboard.',
  hardware:
    'O acionamento de sensor, LEDs, buzzer ou servo integra o resultado esperado apenas quando esses periféricos estiverem presentes e forem validados. A operação física completa ainda depende dos testes de bancada.',
} as const;

export const projectTopics = [
  'Agronegócio',
  'Laranja',
  'Visão Computacional',
  'Sistemas Embarcados',
  'Edge Computing',
  'Dados',
  'ODS 2',
] as const;

export const contextReferences = [
  {
    name: 'Embrapa',
    description:
      'Comportamento de citros no Amazonas (Embrapa Amazônia Ocidental, 2007). O documento inclui a laranja Pera-rio e apoia a contextualização da cultivar; não valida o classificador do OrangeVision.',
    url: 'https://www.infoteca.cnptia.embrapa.br/bitstream/doc/681766/1/Doc55.pdf',
    linkLabel: 'Consultar documento da Embrapa (PDF)',
    note: 'SILVA, S. E. L. da et al. Comportamento de citros no Amazonas. Manaus: Embrapa Amazônia Ocidental, 2007. 31 p. (Documentos, 55).',
  },
  {
    name: 'Fundecitrus',
    description:
      'Material sobre greening e psilídeo, incluindo características visíveis dos frutos. Apoia o contexto do estudo; o OrangeVision não utiliza a aparência para confirmar a presença de doenças.',
    url: 'https://www.fundecitrus.com.br/pragas-e-doencas/greening-e-psilideo/',
    linkLabel: 'Consultar Fundecitrus — greening e psilídeo',
    note: null,
  },
  {
    name: 'Nações Unidas',
    description:
      'Apresentação oficial do ODS 2 — Fome Zero e Agricultura Sustentável — e de suas metas, incluindo a meta 2.a sobre infraestrutura, pesquisa e desenvolvimento tecnológico.',
    url: 'https://brasil.un.org/pt-br/sdgs/2',
    linkLabel: 'Consultar ODS 2 e suas metas na ONU Brasil',
    note: null,
  },
] as const;
