// Conteúdo separado da apresentação, como na cópia OrangeVision_, preservando a stack principal.
export const institutionalContent = {
  projeto: {
    title: 'O Projeto',
    description:
      'O OrangeVision é um projeto de Engenharia da Computação que integra Sistemas Embarcados, Visão Computacional e Engenharia de Dados para auxiliar na triagem visual de laranjas no contexto do agronegócio.',
    pending:
      'Validar variedade, hardware e critérios de calibração na bancada.',
  },
  planejamento: {
    title: 'Planejamento',
    description:
      'Etapas, recursos e entregas previstos para o desenvolvimento do OrangeVision.',
  },
  desenvolvimento: {
    title: 'Desenvolvimento',
    description:
      'Como o OrangeVision foi construído: equipamento, visão computacional, classificação, Web API, banco de dados e site.',
  },
  resultados: {
    title: 'Resultados',
    description: 'As medições e evidências ainda precisam ser obtidas.',
    sections: [
      [
        'Plano de avaliação',
        'Testar câmera, segmentação, métricas, classificação, persistência, sincronização, dashboard e ciclo completo. Testes de sensor, LEDs, buzzer e servo são aplicáveis somente quando esses periféricos estiverem presentes.',
      ],
      [
        'Sincronização',
        'Avaliar operação sem internet, reconexão, reenvio idempotente e proteção das credenciais.',
      ],
      [
        'Indicadores',
        'Taxa de aprovação de frutas, sucesso dos testes e acurácia são medidas distintas. Acurácia exige referência rotulada e metodologia validada.',
      ],
    ],
    pending:
      'Evidências em preparação: fotos, vídeos, medições e resultados de bancada. Testes de interface não comprovam desempenho físico nem acurácia.',
  },
  equipe: {
    title: 'Equipe',
    description:
      'Estudantes de Engenharia da Computação da USF e suas atuações no OrangeVision.',
  },
  referencias: {
    title: 'Referencial Teórico',
    description:
      'O desenvolvimento do OrangeVision é fundamentado em referências relacionadas à citricultura, características visuais dos frutos, processamento digital de imagens e agricultura sustentável. Essas fontes auxiliam na definição dos critérios utilizados durante a construção e avaliação do sistema.',
  },
} as const;

export type ContentSlug = keyof typeof institutionalContent;
