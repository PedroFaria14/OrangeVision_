# OrangeVision — Especificação profissional do frontend

Versão 2.0 — 19/10/2026. Especificação completa de telas, gráficos e integração. Complementa especificação geral v3.0. Requisitos para implementação; não comprova código pronto.

## STACK

React, TypeScript estrito, Vite, Yarn, MUI Material com Emotion e TanStack Query (React Query). React Router se compatível com a base. ESLint/Prettier e versões compatíveis, instalação reproduzível com um único lockfile. Validar respostas em runtime com Zod ou padrão existente. Inspecionar código e preservar convenções úteis antes de alterar.

## ESTRUTURA

```text
Frontend/
  public/
  src/
    app/
      providers/          # tema, Query e composição
      router/             # rotas, layouts, guards e 404
      config/             # configuração pública
    features/
      auth/
        api/
        model/
        hooks/
        components/
        pages/            # LoginPage e RegisterPage
      dashboard/
        api/
        model/
        hooks/
        components/
        pages/
      device/
        api/
        model/            # capacidades e status por dispositivo
        components/
      institutional/
        pages/
        components/
    shared/
      api/                # HTTP e erros normalizados
      theme/              # tokens e overrides MUI
      ui/                 # composição reutilizável
      lib/                # utilitários realmente compartilhados
    main.tsx
  .env.example
  package.json
  yarn.lock
  tsconfig.json
  vite.config.ts
  eslint.config.js
  README.md
```

Criar pastas apenas conforme uso. Shared não depende de features/app; composição em app; evitar importar detalhes internos entre features. Extrair feature analyses se detalhe justificar domínio separado. Não duplicar componentes MUI nem criar abstrações genéricas sem necessidade. Alias @/ para src/ coerente no TypeScript, bundler e testes.

## TEMA E INTERFACE

Laranja #F97316, verde #15803D, grafite #111827 e branco #FFFFFF. Montserrat/Roboto locais com fallback. ThemeProvider, CssBaseline e estilos globais centralizados. Contraste, foco visível, teclado, labels e reduced motion. Texto grafite sobre botão laranja e verde para links são base técnica; dimensões ajustáveis.

Header, navegação responsiva, footer e layouts público/privado consistentes. Mobile em uma coluna, duas/três quando adequado. Tabelas adaptáveis ou rolagem contida, nunca overflow da página. Sem imagens ou medições inventadas.

## LOGIN, CADASTRO E LOGOUT

- /login: identificador conforme backend existente, senha, mostrar/ocultar senha e link para cadastro.
- /registrar: campos mínimos do contrato; proposta nome, e-mail, senha e confirmação. E-mail ainda depende do schema.
- Sem recuperação, redefinição ou esqueci a senha nesta fase.
- Labels permanentes, erros por campo e global, feedback de envio e prevenção de envio duplicado.
- Autocomplete username/email, current-password e new-password; permitir colagem e gerenciadores.
- Política de senha coerente com servidor, sem truncamento silencioso; confirmação no cliente e validação real no backend.
- Não repetir mutations de credenciais automaticamente; respeitar limites e apresentar erro de login genérico.
- Consultar sessão ao iniciar; aguardar resolução antes de mostrar dados privados ou redirecionar.
- Pós-login vai ao dashboard ou destino interno validado, sem open redirect externo.
- 401 expira estado e direciona ao login; 403 mostra acesso negado sem loop.
- Logout POST invalida sessão no servidor; cancelar requests e remover caches privados. Se falhar, informar sem afirmar invalidação concluída.
- Cadastro não concede administrador nem todos os dispositivos. Confirmar política de autorização.

## SEGURANÇA E BANCO EXISTENTE

Hash de senha acontece no backend, preferencialmente Argon2id com salt por senha e biblioteca mantida. SHA-224/256/512 puro não armazena senha com segurança. Nada de algoritmo criptográfico próprio; hash no navegador não substitui servidor/HTTPS.

Sessão preferencial em cookie HttpOnly, Secure em produção, SameSite apropriado; servidor implementa CSRF, CORS allowlist, expiração, rotação e revogação. Nunca persistir senha ou token de sessão em localStorage/sessionStorage. Não colocar credenciais em query keys, cache Query, URLs, logs ou telemetria. Não persistir mutations de autenticação; limpar referências sensíveis após uso e não expor payloads em devtools/logs de produção.

Guard de rota é UX; backend autoriza cada endpoint e recurso. Banco JÁ EXISTE: inspecionar schema/migrations/API, integrar preservando dados e propor só mudanças necessárias. Não conectar React ao banco e não colocar segredos em VITE_*.

## QUERY E SERVIÇOS

QueryClient estável e providers em app. Estado remoto em TanStack Query; estado de formulário/dialog em componente; filtros compartilháveis na URL quando fizer sentido. Query keys por domínio, usuário autorizado/dispositivo e filtros, sem segredos.

Consultas privadas somente após sessão validada. Polling de referência 30 s, pausado sem sessão e em segundo plano. Cancelamento com AbortSignal, timeout e tratamento de erro HTTP, JSON inválido e schema incompatível. Retry limitado a falhas transitórias de leitura; não repetir 401/403/validação ou cadastro/login automaticamente.

Logout/troca de conta cancela requests e remove cache privado; respostas tardias não podem repovoar a interface com dados da conta anterior. Não persistir cache privado offline sem política específica. Confirmação e invalidação de mutations só após sucesso real.

Cliente HTTP compartilhado transporta dados; contratos, schemas e queries ficam no domínio. Endpoints e envelope paginado da especificação geral são propostas a validar contra backend real. Não mascarar erro com mocks.

## DASHBOARD E CÂMERA

Resumo, distribuição, histórico paginado, filtros, detalhe, horário da consulta e última sincronização. Total global vem da API, não da soma da página. Percentual aprovado não é acurácia. Estados de loading, vazio após resposta válida, erro, cache desatualizado, sessão expirada e acesso negado.

Raspberry + câmera é a base. LEDs, buzzer, servo e sensor opcionais: quando presença confirmada, mostrar informação; ausentes, omitir sem card vazio nem erro; desconhecido, não inventar status. Instalado mas indisponível recebe informação contextual sem bloquear câmera. Telemetria remota indica última observação e horário, não estado ao vivo.

Captura somente em ambiente local e autorizado no servidor; estar logado no dashboard remoto não basta. Não renderizar paths locais de imagens. Sem imagens privadas autorizadas, explicar indisponibilidade. Sem dados reais, indicar integração pendente; simulação somente explícita e separada.

## ROTAS

Públicas: /, /projeto, /planejamento, /desenvolvimento, /resultados, /equipe, /referencias, /login, /registrar.

Privadas: /dashboard e proposta /dashboard/analises/:id. Lazy loading quando útil, error boundary, página 404 e fallback da hospedagem para rotas React sem capturar /api/*.

## VALIDAÇÃO E ENTREGA

- Build, tipagem, lint e formatação aprovados; dependências compatíveis e lockfile.
- Cadastro, login, logout e expiração contra API de integração, sem autenticação fictícia.
- API privada bloqueia acesso não autorizado, inclusive por UUID/dispositivo.
- Troca de sessão/logout com request em andamento não mantém cache anterior.
- Refresh direto de rota, 404 e redirects funcionam.
- Formulários por teclado/leitor de tela; feedback não depende apenas de cor.
- Layout em 320/375/390/768 px e desktop sem overflow da página.
- Câmera-only funciona; opcional ausente não gera erro ou dependência obrigatória.
- Conteúdo acadêmico marca custos, datas, bibliografia e resultados pendentes.

Ao entregar, listar arquivos, árvore principal, verificações e pendências. Não declarar banco/API integrados se não foram exercitados.

## MAPA COMPLETO DE TELAS

### Site institucional

| Tela | Seções previstas | Origem do conteúdo |
|---|---|---|
| Início | Marca textual, apresentação, câmera→processamento→registro, pilares, problema/solução, ODS 2, stack e CTAs | Especificação e conteúdo editorial aprovado |
| O Projeto | Contexto, objetivos, objeto de estudo, escopo externo e limitações | Documentação validada |
| Planejamento | 5W2H, etapas, cronograma, materiais e orçamento | Datas/custos fornecidos; pendências explícitas se ausentes |
| Desenvolvimento | Arquitetura, Raspberry/câmera, OpenCV, quatro métricas, persistência, sincronização e integração | Documentação técnica coerente com implementação |
| Resultados | Evidências reais, plano de testes, avaliações e limitações | Resultados medidos e aprovados; não usar exemplos como resultados |
| Equipe | Nomes e funções revisadas | Briefing e confirmação editorial |
| Referências | Fontes completas e links | Bibliografia verificada |

O site institucional não precisa consultar métricas privadas para renderizar. Não transformar cadastro em requisito para ler o conteúdo público. CTAs para dashboard respeitam a sessão e encaminham ao login quando necessário.

### Autenticação

Login e cadastro possuem composição visual consistente com a marca, campos rotulados, feedback por campo, botão de envio e navegação entre as duas telas. Não criar telas de redefinição, recuperação, pagamentos ou administração sem novo requisito.

Após cadastro, seguir comportamento real da API: se ela estabelecer sessão, abrir dashboard; caso contrário, confirmar criação e encaminhar ao login. Não presumir login automático.

### Área autenticada

| Tela | Conteúdo principal |
|---|---|
| Dashboard | Filtros globais, sincronização, indicadores, gráficos e análises recentes |
| Histórico de análises | Lista paginada completa, filtros e navegação ao detalhe |
| Detalhe da análise | Classificação, métricas, calibração, imagens autorizadas e rastreabilidade |
| Dispositivo | Câmera, capacidades presentes e diagnóstico autorizado; apenas se backend fornecer esses dados |

Rotas complementares propostas: /dashboard/historico e /dashboard/dispositivos/:id. Confirmar necessidade e contrato antes de implementá-las; podem começar como seções da área autenticada. Navegação contém apenas destinos utilizáveis. Não criar menu para funcionalidade inexistente.

## COMPOSIÇÃO DO DASHBOARD

Ordem sugerida:

1. Título, contexto do dispositivo e ação atualizar.
2. Filtros e indicação do período ativo.
3. Última consulta, última sincronização e aviso de atraso quando verificável.
4. Indicadores globais do recorte selecionado.
5. Distribuição de classes e evolução temporal.
6. Métricas visuais agregadas, se suportadas pelo backend.
7. Histórico recente com acesso ao histórico completo.
8. Informação contextual da câmera/dispositivo somente quando disponível e autorizada.

Não ocupar a tela com cards sem função. No mobile, filtros e indicadores empilham; gráficos mantêm rótulos legíveis. Erro isolado em uma consulta não deve apagar toda a área nem bloquear consultas independentes.

## FILTROS E CONSISTÊNCIA DOS DADOS

Filtros previstos: período inicial/final, classificação, lote opcional e dispositivo autorizado quando houver mais de um. Não oferecer filtro que a API não suporta.

- Datas escolhidas no fuso de exibição; converter limites para UTC com regra explícita. Preferir intervalo fechado no início e aberto no fim, confirmado no contrato.
- Ao mudar filtros, reiniciar página do histórico e atualizar queries relacionadas.
- Resumo, gráficos e histórico devem indicar seu recorte; ao filtrar classe, apresentar claramente que a distribuição também está filtrada, ou identificar explicitamente o gráfico como referente a todas as classes.
- Opções de lote/dispositivo vêm de fonte autorizada e completa, não apenas dos registros da página atual.
- Filtros ativos podem ir na URL sem incluir informações secretas. Não disparar consultas a cada tecla sem necessidade; usar Aplicar ou debounce conforme interação.
- Atualização manual solicita apenas queries relevantes; evitar vários timers independentes solicitando a mesma informação.
- Preferir snapshot/as_of comum do backend quando disponível. Sem isso, identificar horários de atualização e não prometer leitura atomicamente consistente entre endpoints.

## INDICADORES — ORIGEM E DEFINIÇÃO

Nomes de campos abaixo são SEMÂNTICOS e PROPOSTOS. Mapear para o contrato real antes de implementar. O backend calcula agregados sobre todo o conjunto autorizado e filtrado; o frontend apenas formata.

| Indicador | Dado necessário do backend | Regra de apresentação |
|---|---|---|
| Total analisado | valid_analyses_count | Contagem de análises válidas concluídas no período; confirmar critério do backend |
| Aprovadas | counts_by_class.APROVADA | Quantidade da classe APROVADA |
| Atenção | counts_by_class.ATENCAO | Quantidade da classe ATENCAO |
| Revisar | counts_by_class.REVISAR | Quantidade da classe REVISAR |
| Taxa de aprovação | approval_rate ou numerator/denominator explícitos | Aprovadas / análises válidas; se denominador zero, mostrar —, nunca NaN |
| Última análise | latest_analysis_at | Data/hora recebida, não status ao vivo da câmera |
| Última sincronização | last_synced_at e device_id | Referência de ingestão/sincronização claramente definida |
| Falhas de execução | execution_errors_count, se existente | Separadas das três classes; falha não equivale a REVISAR |

O nome técnico correto da primeira classe é APROVADA. Nenhuma contagem representa uma medição existente neste documento. O backend deve confirmar quais estados entram no denominador. Não misturar falhas de captura com análises classificadas. Não exibir acurácia, produtividade/hora ou ganho econômico sem dados e metodologia próprios.

Diferença em relação a período anterior só aparece quando backend retorna os dois recortes comparáveis e denominadores definidos. Evitar setas de crescimento fictícias.

## GRÁFICOS OBRIGATÓRIOS DO DASHBOARD

Usar biblioteca compatível com React/TypeScript e MUI: preferência inicial por MUI X Charts Community, confirmando disponibilidade/licença da versão escolhida; Recharts é alternativa técnica. Escolher uma, sem introduzir duas bibliotecas para o mesmo uso. Não depender de funcionalidades pagas sem decisão explícita.

### 1. Distribuição por classificação

- Pergunta respondida: quantas análises foram aprovadas, ficaram em atenção ou precisam de revisão no recorte?
- Visual principal: barras horizontais com as três classes, quantidade e percentual; rosca é alternativa somente se legível e acompanhada de números.
- Fonte proposta: GET /api/metrics/distribution com filtros.
- Dados necessários: classe, contagem, total válido, período aplicado e horário de referência.
- Percentuais calculados sobre total válido da distribuição, usando valores completos, não uma página do histórico.
- Classe conhecida com zero pode aparecer como zero quando o backend confirmar conjunto completo. Classe ausente em resposta parcial não pode ser assumida como zero.
- Tooltip e tabela textual equivalente; legenda não depende exclusivamente da cor.

### 2. Evolução das análises no tempo

- Pergunta: como o volume analisado e as classes se distribuem ao longo do período?
- Visual: colunas empilhadas por hora/dia ou linhas separadas, escolhendo uma composição consistente.
- Fonte adicional proposta: GET /api/metrics/timeseries. Esse endpoint NÃO foi confirmado no projeto.
- Dados necessários: início/fim de cada bucket, contagens por classe, total válido, granularidade e timezone de agrupamento.
- Intervalos sem dados só recebem zero se backend confirmar cobertura completa; falha/ausência de cobertura produz lacuna, não zero inventado.
- Não agregar no browser apenas os 20 registros visíveis para representar todo o período.
- Granularidade depende do período e limites da API; evitar milhares de pontos e eixos ilegíveis.

Se o backend ainda não oferecer agregados, mostrar seção com integração pendente ou adiar o gráfico de forma explícita. Não preencher com valores aleatórios.

## GRÁFICOS COMPLEMENTARES — DEPENDENTES DE DADOS REAIS

### 3. Métricas visuais por período

Mostrar quatro séries em pequenos gráficos separados: proporção de cor, regiões anormais, circularidade e assimetria. Não sobrepor score 0–100 e razões 0–1 no mesmo eixo sem explicação.

Fonte proposta: agregados por bucket com média, tamanho da amostra, unidade e versão de calibração. Backend deve definir tratamento de nulos/outliers. Se misturar calibrações incompatíveis, separar séries ou avisar. Circularidade usa domínio definido pelo processamento, sem assumir teto 1 quando o contrato não confirmar.

### 4. Distribuição do score experimental

Histograma com faixas definidas pelo backend e contagens, score de 0 a 100. Não apresentar score como probabilidade, qualidade interna ou acurácia. Limiares só aparecem se retornados com versão de calibração e identificação experimental.

### 5. Taxa de aprovação no tempo

Série de aprovadas / válidas por bucket, com amostra e denominador no tooltip. Buckets com denominador zero são sem taxa, não 0% medido. Não substituir taxa por média simples de percentuais com amostras diferentes.

Gráficos complementares não bloqueiam a primeira entrega; tornam-se implementáveis quando os contratos existirem. Não criar scatterplot, ranking, previsão de doença ou métricas econômicas sem requisito e dados adequados.

## CORES E ACESSIBILIDADE DOS GRÁFICOS

Usar verde para APROVADA e laranja para ATENCAO. Cor semântica de REVISAR precisa ser definida no tema e validada por contraste, como extensão técnica da paleta, sem alegar aprovação prévia. Erros de execução permanecem categoria distinta.

Todos os gráficos possuem título, descrição curta, unidade, período, tooltip e equivalente textual/tabular. Labels, ícones ou padrões complementam cor. Animações discretas respeitam reduced motion. Não depender de hover para acessar informação essencial no celular ou teclado. Valores aproximados devem indicar arredondamento; não alterar dados de origem para ajustar soma visual a 100%.

## HISTÓRICO COMPLETO

Fonte proposta: GET /api/analyses com paginação, filtros e ordenação confirmados no servidor.

Colunas previstas:

- Data/hora da análise no fuso de exibição.
- ID abreviado visualmente, com acesso ao identificador completo.
- Classificação textual e indicador visual.
- Score experimental.
- Cor, regiões anormais, circularidade e assimetria.
- Lote e dispositivo quando fornecidos/autorizados.
- Versão de calibração quando útil, preferencialmente no detalhe.
- Ação Ver detalhes.

No mobile, priorizar data, classe, score e detalhe; outras informações podem ir em expansão/cartão. Imagem somente se URL autorizada válida existir; sem imagem, não renderizar link quebrado.

Paginação e ordenação são do servidor. Total global vem da API, não do length da página. Validar máximo por página e ordenação estável, incluindo desempate por ID conforme contrato. Se página atual ficar vazia após filtros, retornar para página válida sem loop. Não oferecer busca por ID se backend não suportar.

Não permitir editar/apagar análises concluídas nesta fase. Exportação CSV é opcional, requer endpoint autorizado e filtros completos; não exportar só a página como se fosse todo o histórico. Proteção contra fórmulas em CSV fica no serviço de exportação.

## DETALHE DA ANÁLISE

Cabeçalho com ID completo, classe, horário, dispositivo e lote, quando existentes. Apresentar:

| Informação | Origem |
|---|---|
| Classe e justificativa | Resultado/observações enviados pelo backend |
| Score visual | metrics.visual_score, unidade 0–100 |
| Cor | metrics.orange_color_ratio, razão convertida para percentual |
| Regiões anormais | metrics.abnormal_region_ratio, percentual |
| Circularidade | metrics.circularity, precisão/unidade documentadas |
| Assimetria | metrics.asymmetry, razão com formatação explícita |
| Calibração | calibration_version e critérios disponíveis |
| Imagem original/anotada | URLs privadas autorizadas, se armazenamento implementado |
| Sincronização | synced_at ou campo real equivalente |
| Estado de execução | Estado real enviado pela API, se disponível |

Campos do exemplo anterior são referência ilustrativa, não schema confirmado. Nunca inventar justificativa a partir de thresholds presumidos. Não derivar diagnóstico de doença de uma região anormal.

Se imagem não foi enviada à nuvem, informar “Imagem disponível apenas no dispositivo”, quando essa condição for confirmada; sem essa confirmação, informar apenas indisponibilidade. URLs expiradas precisam de renovação autorizada; não cachear a URL indefinidamente nem expor URL privada em telemetria. Mostrar erro de imagem sem apagar métricas.

Tratar 404, 403, falha de rede e payload incompatível separadamente, sem vazar existência de recurso além da política do backend.

## CÂMERA, CAPTURA E DISPOSITIVO

A área remota comum é de consulta. Não tentar abrir câmera do notebook via getUserMedia para substituir a câmera Raspberry sem novo requisito.

Quando houver modo local autorizado:

1. Consultar sessão, permissão de captura e capacidades atuais do Pi.
2. Exibir estado da câmera e botão Capturar e analisar se permitido.
3. Enviar comando uma única vez; bloquear envio duplicado enquanto pendente.
4. Se API assíncrona retornar job_id, acompanhar endpoint proposto /api/jobs/:id até estado final; confirmar protocolo real antes de implementar.
5. Ao concluir, invalidar histórico/resumo relevantes após confirmação da persistência.
6. Se houver erro ou timeout, informar situação desconhecida e consultar o job antes de reenviar; não assumir falha definitiva nem criar captura duplicada.

Câmera indisponível mostra erro específico. Ausência de LEDs/servo/buzzer/sensor não impede captura. Estados operacionais, nomes dos jobs e permissões vêm do backend; não simular andamento com temporizador.

## MATRIZ FRONTEND → BACKEND

| Interface | Serviço proposto | Dados mínimos | Situação |
|---|---|---|---|
| Login/cadastro/sessão/logout | /api/auth/* | contrato de credenciais, usuário público, sessão e erros | Confirmar existência e schema |
| Cards do resumo | /api/metrics/summary | totais, denominadores, período e as_of | Confirmar schema |
| Classes | /api/metrics/distribution | contagens completas por classe e total | Confirmar schema |
| Evolução | /api/metrics/timeseries | buckets, timezone, contagens e cobertura | Endpoint adicional proposto |
| Métricas/score agregados | endpoint a definir | estatísticas, amostras, faixas e calibração | Complementar, pendente |
| Histórico | /api/analyses | itens, paginação, total ou cursor e filtros | Confirmar envelope |
| Detalhe | /api/analyses/:id | análise autorizada e métricas | Confirmar schema |
| Sincronização | /api/sync/status | dispositivo, last_synced_at e horário de observação | Confirmar schema |
| Capacidades | local /api/system/status ou canal autorizado | presença, disponibilidade, observed_at | Proposta, não assumir existente |
| Captura | local /api/capture e eventual /api/jobs/:id | autorização, comando, job e estado final | Somente modo local autorizado |

Nenhum endpoint desta tabela prova disponibilidade real. Inspecionar backend/OpenAPI/schema do banco existente, criar adaptadores explícitos e registrar campos ausentes. Se necessário implementar endpoint novo, isso é trabalho do servidor, não conexão direta do React ao banco.

## POLÍTICA DE ERROS E DADOS INCOMPLETOS

- null/ausente significa não informado, não zero. Não usar fallback 0 para esconder campo inválido.
- Não exibir alertas de hardware opcional ausente; unknown permanece informação não confirmada.
- API indisponível mostra falha e opção de tentar novamente. Não dizer que o Raspberry está offline só porque a API web falhou.
- Cache anterior pode ficar visível somente com sessão válida e aviso de desatualização; em logout/expiração, remover dados privados.
- Limite de atraso deve ser configurado e coerente com cadência real. Sem cadência/last_synced_at, não calcular “saúde” fictícia.
- Erros de contrato são registrados sem payloads sensíveis e apresentados como incompatibilidade/indisponibilidade, não como vazio.
- Datas inválidas, classes desconhecidas e números não finitos devem ser tratados pela validação, sem quebrar renderização.

## COMPONENTES REUTILIZÁVEIS PREVISTOS

AppLayout, PublicLayout, AuthLayout, ProtectedLayout, PageHeader, FilterBar, MetricCard, QueryFeedback, ClassificationBadge, SyncStatus, ChartPanel, AccessibleChartSummary, AnalysesTable, AnalysisDetails, OptionalCapabilities e formulários de autenticação.

São responsabilidades sugeridas, não obrigação de criar todos antes do uso. Reutilizar componentes MUI e compor por domínio. Mensagens visíveis devem estar em português; detalhes internos de API/schema não aparecem como fluxo de produto.

## CRITÉRIOS ADICIONAIS DOS GRÁFICOS E INTEGRAÇÃO

1. Comparar cards e gráficos com respostas reais do mesmo recorte autorizado.
2. Confirmar denominadores e que falhas de aquisição não entram como REVISAR.
3. Testar total zero, classe zero, nulos, período vazio, dados parciais e granularidades diferentes.
4. Verificar limites de fuso à meia-noite e intervalo de datas.
5. Confirmar que mudar filtro cancela/descarta resposta obsoleta sem sobrescrever recorte novo.
6. Testar paginação com muitos registros sem carregar histórico inteiro no navegador.
7. Validar gráficos por teclado, em mobile, com reduced motion e equivalente textual.
8. Verificar sessão expirada durante polling, logout durante request e troca de conta.
9. Validar captura local sem nenhum periférico opcional, quando esse modo estiver implementado.
10. Registrar quais telas/endpoints estão implementados, pendentes ou bloqueados por contrato. Não declarar integração real por existir apenas layout.

## ORDEM DE IMPLEMENTAÇÃO RECOMENDADA

1. Inventário do repositório, banco e contratos; registrar o que já existe.
2. Base técnica, tema, layouts, navegação e páginas institucionais.
3. Cadastro/login/logout e proteção com sessão e autorização reais.
4. Cliente API, schemas e integração de histórico/detalhe.
5. Resumo e distribuição de classes; depois evolução temporal com agregado no servidor.
6. Filtros consistentes, sincronização e capacidades opcionais.
7. Gráficos complementares e modo local apenas quando dados/contratos estiverem disponíveis.
8. Verificações técnicas, acessibilidade, navegador e aceite com backend real.

Entrega final acompanha árvore principal, lista de alterações, instruções de execução, .env.example sem secrets, contratos confirmados e pendências. Estas instruções não autorizam inventar dados, refazer o banco existente ou publicar comandos do Pi na internet.

