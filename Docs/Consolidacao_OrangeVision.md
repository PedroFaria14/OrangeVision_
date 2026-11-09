# Informações da cópia OrangeVision_ no projeto principal

## Escopo confirmado

Aproveitar informações e organização da cópia `OrangeVision_`, preservando o
padrão do `OrangeVision` principal. Não transferir fotos, histórico, SQLite,
filas, credenciais, ambientes virtuais ou pesos de modelos. Não alterar dados
remotos nem aplicar migrations por essa consolidação.

## Comparação realizada

- `web_api/` e `contracts/` são idênticos nas duas árvores examinadas.
- Dashboard, comparação, inspeções e amostras já estão implementados no principal.
- O conteúdo institucional é equivalente, com a descrição de stack adaptada ao
  MUI e Recharts do principal.
- A cópia separa conteúdo institucional de apresentação em
  `Frontend/src/features/institutional/content.ts`.
- O executor de câmera/IA está em `OrangeVision_/backend/device/`. Seu código foi
  referência para descrever os fluxos; não foi importado na consolidação inicial.

## Adaptações no principal

1. Informações institucionais, etapas e referências centralizadas em
   `Frontend/src/features/institutional/model/content.ts`.
2. Renderização continua usando `Page`, MUI, tema, fontes, cores e layouts atuais.
3. `DevelopmentFlows` apresenta separadamente:
   - análises oficiais: inspeção autorizada, captura/calibração, SQLite/outbox,
     ingestão, PostgreSQL/API e dashboard pessoal;
   - amostras experimentais: upload/foto local, galeria privada, fila, executor,
     detecção/revisão local e resultado experimental.
4. Mantidos os limites: amostras não alimentam indicadores oficiais; score do
   detector não é acurácia/qualidade; pareamento não inicia câmera remotamente.
5. Título da rota de amostras corrigido no helper de navegação.

## O que permanece preservado

- Autenticação, autorização, propriedade e isolamento entre usuários.
- Contratos, queries, conversão de unidades, filtros e paginação do servidor.
- Gráficos, dashboard, imagens privadas e comandos já implementados no principal.
- Conteúdo de equipe, planejamento e referências, com pendências editoriais explícitas.
- A cópia de origem, seus dados e sua configuração.

Essa organização não é uma importação de banco nem comprova operação física,
calibração, acurácia ou disponibilidade atual do executor. Os testes de navegador
validam conteúdo, navegação e responsividade com contratos controlados.

## Melhorias recentes de dashboard e interação

Referências da origem: `bdfa2ed` (percentuais/distribuição) e `aeaba92`
(histórico/detalhe), além da comparação dos comportamentos já presentes nas telas.

- `MetricCards`: participação de cada classificação sobre o total autorizado do
  recorte, junto às quantidades e deltas existentes. Total zero indica participação
  indisponível, sem calcular percentual sobre as cinco linhas visíveis.
- `AnalysisCharts`: gráficos Recharts mantidos, tooltip de distribuição com
  quantidade e percentual, regiões tabulares focáveis e cabeçalhos de linha.
- `AnalysesTable`: intervalo exibido para dashboard compacto e histórico paginado;
  navegação de paginação identificada para tecnologias assistivas.
- `PeriodComparison`: contexto dos dois períodos e horário da consulta também no
  estado vazio. Diferença absoluta, variação percentual e pontos percentuais são
  apresentados separadamente, incluindo ausência de base anterior.
- `AnalysisDetails`: explicação de métricas nulas, score ausente sem barra fictícia,
  sessão na rastreabilidade e justificativa em seção própria.
- `SamplesPage`: coordenadas textuais da detecção como complemento do SVG, estado
  informado pelo executor e navegação de paginação identificada.
- `InspectionPage`: encerramento desabilitado para `closing`, `closed` e `expired`.
- Autenticação: espera/erro/retry da consulta de sessão, inputs bloqueados durante
  envio e limite HTML de 128 caracteres na senha e na confirmação.

Os gráficos, o tema MUI e o conteúdo institucional mais completo do principal
continuam sendo a base. Os cálculos de comparação permanecem na API; estas
adaptações não exigem migrations ou transferência de registros reais.

Os cenários adicionados às suítes Playwright verificam percentuais sobre o total
do recorte, tooltip, paginação, nulos, base zero, unidades, estados terminais e
interações de autenticação. As validações usam apenas fixtures de teste.
