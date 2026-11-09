import { contextReferences } from './project';

export const theorySections = [
  {
    id: 'citricultura',
    label: '01 • Citricultura',
    title: 'Laranja Pêra-Rio',
    symbol: '🍊',
    accent: 'primary.main',
    paragraphs: [
      'A laranja Pêra-Rio pertence ao grupo das laranjas doces, da espécie Citrus sinensis. Na caracterização publicada pela Embrapa, o fruto apresenta forma ovalada, casca amarelada e polpa de cor laranja, nas condições descritas no documento (2007, p. 23).',
      'Essas informações fornecem uma referência inicial para o estudo da forma, coloração e regularidade geométrica. A descrição da polpa é bibliográfica: o OrangeVision observa somente a superfície visível. Variedade, iluminação, posicionamento e critérios de calibração devem ser conferidos na bancada.',
    ],
    sourceId: 'embrapa',
    sourceLabel: 'Embrapa — Comportamento de citros no Amazonas, p. 23',
  },
  {
    id: 'caracteristicas',
    label: '02 • Características visuais',
    title: 'Alterações observáveis em frutos cítricos',
    symbol: '🌱',
    accent: 'secondary.main',
    paragraphs: [
      'O Fundecitrus descreve que frutos provenientes de ramos com sintomas de greening podem apresentar maturação irregular, coloração verde-clara manchada, tamanho reduzido, deformação e assimetria.',
      'No OrangeVision, essas informações ajudam a selecionar características externas mensuráveis. Alterações de aparência não confirmam uma doença; a triagem visual preliminar pode indicar a necessidade de uma avaliação adicional.',
    ],
    sourceId: 'fundecitrus',
    sourceLabel: 'Fundecitrus — Greening e psilídeo',
  },
  {
    id: 'processamento',
    label: '03 • Visão computacional',
    title: 'Processamento Digital de Imagens',
    symbol: '👁️',
    accent: 'text.primary',
    paragraphs: [
      'A visão computacional transforma imagens em informações quantitativas. O OrangeVision utiliza OpenCV para segmentar a fruta, analisar coloração, quantificar regiões de interesse e extrair informações geométricas do contorno.',
      'O espaço HSV separa matiz (H), saturação (S) e valor ou brilho (V). Máscaras definidas por faixas calibradas selecionam pixels de interesse; área e perímetro dos contornos permitem calcular a circularidade.',
      'Há um caminho de segmentação por HSV e um caminho experimental de amostras com detector ONNX e GrabCut. Identificar uma laranja não equivale a classificar sua qualidade: cada método exige calibração compatível.',
    ],
    sourceId: 'opencv',
    sourceLabel: 'OpenCV — documentação de processamento de imagens',
  },
] as const;

export const theoryApplications = [
  {
    title: 'Coloração',
    symbol: '🎨',
    description:
      'Proporção dos pixels dentro das faixas HSV calibradas, medida somente na máscara da fruta. A métrica de cor do executor quantifica a região alaranjada configurada.',
    technique: 'HSV + máscaras de cor',
    detail: 'Pixels da faixa / pixels da fruta',
  },
  {
    title: 'Regiões Anormais',
    symbol: '🔍',
    description:
      'Proporção de pixels nas faixas calibradas de regiões de interesse, como manchas. Não é uma identificação automática da causa de uma alteração.',
    technique: 'Segmentação + cálculo de área',
    detail: 'Pixels da região / pixels da fruta',
  },
  {
    title: 'Forma',
    symbol: '⭕',
    description:
      'Análise do contorno da região visível. A circularidade relaciona a área A ao perímetro P; é uma medida geométrica da imagem, não uma avaliação interna da fruta.',
    technique: 'Contorno + circularidade',
    detail: 'Circularidade = 4πA / P²',
  },
  {
    title: 'Assimetria',
    symbol: '↔️',
    description:
      'No método atual, compara-se a silhueta recortada com seu espelho horizontal. Conta-se a diferença entre as máscaras e normaliza-se por duas vezes o número de pixels da fruta.',
    technique: 'Análise geométrica',
    detail: 'Diferença entre máscara e espelho / (2N)',
  },
] as const;

export const theoryFlow = [
  'Referências',
  'Cor, regiões anormais, forma e assimetria',
  'Normalização e pesos',
  'Score visual',
  'Triagem',
] as const;

export const opencvTopics = [
  {
    label: 'Conversão para HSV e máscaras de cor',
    url: 'https://docs.opencv.org/4.x/df/d9d/tutorial_py_colorspaces.html',
  },
  {
    label: 'Contornos, área e perímetro',
    url: 'https://docs.opencv.org/4.x/dd/d49/tutorial_py_contour_features.html',
  },
  {
    label: 'Segmentação com GrabCut',
    url: 'https://docs.opencv.org/4.x/d8/d83/tutorial_py_grabcut.html',
  },
] as const;

export const bibliographySources = [
  {
    id: 'embrapa',
    category: 'Citricultura',
    name: 'Embrapa',
    citation: contextReferences[0].note,
    usage:
      'Contextualização da cultivar Pêra-Rio e de suas características físicas. A página 23 do documento fundamenta a descrição bibliográfica, não os pesos ou limiares do classificador.',
    url: contextReferences[0].url,
    linkLabel: contextReferences[0].linkLabel,
  },
  {
    id: 'fundecitrus',
    category: 'Características visuais',
    name: 'Fundecitrus',
    citation: 'FUNDO DE DEFESA DA CITRICULTURA. Greening e psilídeo.',
    usage:
      'Compreensão de alterações externas observáveis em frutos cítricos, como maturação irregular, manchas, deformações e assimetria. Não é utilizado para confirmar doenças pela imagem.',
    url: contextReferences[1].url,
    linkLabel: contextReferences[1].linkLabel,
  },
  {
    id: 'opencv',
    category: 'Visão computacional',
    name: 'OpenCV',
    citation:
      'OPENCV. Open Source Computer Vision Library — documentação oficial.',
    usage:
      'Aquisição e processamento de imagens, conversão de espaços de cor, máscaras, segmentação e contornos. Os tutoriais abaixo detalham as técnicas relacionadas ao executor.',
    url: 'https://docs.opencv.org/4.x/',
    linkLabel: 'Consultar documentação do OpenCV',
  },
  {
    id: 'raspberry-pi',
    category: 'Sistemas embarcados',
    name: 'Raspberry Pi',
    citation:
      'RASPBERRY PI. Raspberry Pi Documentation — documentação oficial.',
    usage:
      'Configuração do SBC, câmera e ambiente Linux. GPIOs, sensores e atuadores são estudados somente quando fazem parte da montagem; não são dependências obrigatórias do modo câmera.',
    url: 'https://www.raspberrypi.com/documentation/',
    linkLabel: 'Consultar documentação do Raspberry Pi',
  },
  {
    id: 'python',
    category: 'Desenvolvimento',
    name: 'Python',
    citation: 'PYTHON SOFTWARE FOUNDATION. Python Documentation.',
    usage:
      'Desenvolvimento dos módulos de captura, processamento, classificação, persistência local e sincronização, além da implementação da API online.',
    url: 'https://docs.python.org/3/',
    linkLabel: 'Consultar documentação do Python',
  },
  {
    id: 'sqlite',
    category: 'Persistência local',
    name: 'SQLite',
    citation: 'SQLITE. SQLite Documentation.',
    usage:
      'Registro local de análises e métricas, jobs, autorizações e outbox, preservando o conteúdo e a sessão original durante falhas de rede e reenvios.',
    url: 'https://www.sqlite.org/docs.html',
    linkLabel: 'Consultar documentação do SQLite',
  },
  {
    id: 'react',
    category: 'Interface e visualização de dados',
    name: 'React',
    citation: 'REACT. React Documentation — documentação oficial.',
    usage:
      'Interface institucional, autenticação, galeria de amostras e dashboard. O frontend atual utiliza React e TypeScript, com MUI, TanStack Query e Recharts.',
    url: 'https://react.dev/learn',
    linkLabel: 'Consultar documentação do React',
  },
  {
    id: 'fastapi',
    category: 'API online',
    name: 'FastAPI',
    citation: 'FASTAPI. FastAPI Documentation — documentação oficial.',
    usage:
      'API online de autenticação, autorização, ingestão e consulta dos resultados. A câmera e o processamento local permanecem no executor do dispositivo.',
    url: 'https://fastapi.tiangolo.com/',
    linkLabel: 'Consultar documentação do FastAPI',
  },
  {
    id: 'postgresql',
    category: 'Persistência remota',
    name: 'PostgreSQL',
    citation: 'POSTGRESQL. PostgreSQL Documentation.',
    usage:
      'Armazenamento remoto, transações, integridade e consultas autorizadas para o dashboard. A aplicação web acessa o banco por meio da API.',
    url: 'https://www.postgresql.org/docs/',
    linkLabel: 'Consultar documentação do PostgreSQL',
  },
  {
    id: 'neon',
    category: 'Banco hospedado',
    name: 'Neon',
    citation: 'NEON. Neon Documentation — PostgreSQL hospedado.',
    usage:
      'Hospedagem do PostgreSQL usado pelo projeto. Conexão e credenciais ficam no ambiente privado dos serviços, não no código público do navegador.',
    url: 'https://neon.com/docs/introduction',
    linkLabel: 'Consultar documentação do Neon',
  },
  {
    id: 'onu',
    category: 'Sustentabilidade',
    name: 'Organização das Nações Unidas',
    citation:
      'ORGANIZAÇÃO DAS NAÇÕES UNIDAS. Objetivo de Desenvolvimento Sustentável 2 — Fome Zero e Agricultura Sustentável.',
    usage:
      'Relação conceitual com tecnologia aplicada à agricultura, especialmente a meta 2.a. A proposta acadêmica não constitui comprovação de impacto na produção agrícola ou na segurança alimentar.',
    url: contextReferences[2].url,
    linkLabel: contextReferences[2].linkLabel,
  },
] as const;
