export const contents = {
  projeto: {
    title: 'O Projeto',
    description:
      'Triagem visual externa de laranjas em ambiente de iluminação controlada.',
    sections: [
      [
        'Problema',
        'A inspeção manual pode ser repetitiva e subjetiva, com registros pouco padronizados.',
      ],
      [
        'Proposta',
        'Capturar imagens, extrair quatro métricas visuais no Raspberry Pi, classificar experimentalmente e registrar cada análise com UUID.',
      ],
      [
        'Escopo e limites',
        'Protótipo acadêmico. Não realiza diagnóstico fitossanitário nem inspeção interna. A variedade Pêra-Rio depende de disponibilidade nos testes.',
      ],
    ],
    pending:
      'Validar variedade, hardware e critérios de calibração na bancada.',
  },
  planejamento: {
    title: 'Planejamento',
    description: 'Etapas previstas na especificação do projeto.',
    sections: [
      [
        'Etapas',
        'Pesquisa → arquitetura → hardware → visão computacional → dados/API/React → integração → testes → apresentação.',
      ],
      [
        'Entregáveis',
        'Interface React, serviços locais, pipeline de visão, persistência e sincronização, integração física e evidências.',
      ],
    ],
    pending:
      'Em preparação: cronograma, responsáveis por etapa e estimativa de custos. Datas e valores serão publicados após confirmação.',
  },
  desenvolvimento: {
    title: 'Desenvolvimento',
    description: 'Arquitetura híbrida: processamento local e consulta remota.',
    sections: [
      [
        'No dispositivo',
        'Câmera e OpenCV → SQLite e outbox → sincronizador HTTPS com reenvio por UUID. Sensor, LEDs, buzzer e servo são opcionais; GPIO não é dependência do modo câmera.',
      ],
      [
        'Na nuvem',
        'API online de autenticação, autorização, ingestão e consultas → PostgreSQL existente → React. Contas de usuários e agregação do dashboard não pertencem ao Raspberry.',
      ],
      [
        'Stack',
        'React, TypeScript, TanStack Query e HTML básico no frontend; FastAPI na API online; Python e OpenCV previstos no Raspberry.',
      ],
    ],
    pending:
      'Validação de bancada pendente: modelo do Raspberry, montagem da câmera e calibração. A operação física e a disponibilidade da hospedagem exigem verificação no ambiente de uso.',
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
      'Áreas de atuação registradas na especificação; revisão editorial pendente.',
    sections: [
      ['Felipe Kenzo', 'Software · Documentação'],
      ['Kauan Fernandes', 'Redes · Infraestrutura · Integração'],
      ['Marcelo Capeletto', 'Qualidade · Testes · Documentação'],
      ['Pedro Faria', 'Software · Backend · Integração'],
      [
        'Glauber Sandi Martins',
        'Desenvolvimento de Produto · Industrialização · Gestão de Projetos · Integração',
      ],
      ['João Assis', 'IoT · Sistemas Embarcados · Conectividade · Integração'],
    ],
    pending: 'Informações complementares da equipe estão em revisão editorial.',
  },
  referencias: {
    title: 'Referências',
    description:
      'Fontes indicadas pelo briefing; bibliografia completa ainda pendente.',
    sections: [
      [
        'Tecnologia',
        'Documentação oficial de Raspberry Pi, OpenCV, Python, SQLite, Neon PostgreSQL, FastAPI e React.',
      ],
      [
        'Contexto acadêmico',
        'Embrapa e Fundecitrus para citricultura; ONU para ODS 2. Referências devem sustentar somente as afirmações efetivamente usadas.',
      ],
    ],
    pending:
      'Bibliografia acadêmica em preparação. Os links abaixo são documentação técnica de apoio, não uma bibliografia concluída.',
  },
} as const;
export type ContentSlug = keyof typeof contents;
