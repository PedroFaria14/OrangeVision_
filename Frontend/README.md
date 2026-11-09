# OrangeVision — frontend

React + TypeScript estrito + Vite, Yarn, MUI, TanStack Query, Zod e Recharts.
Implementação baseada em `../Docs/OrangeVision.md` e `../Docs/Especificacao.md`.

## Prisma no mesmo projeto Vercel

A rota **`/admin/prisma`** abre o painel administrativo com login GitHub exclusivo
e conexão de leitura no servidor. Ela não depende da autenticação de usuários no
Render. Configuração e publicação no domínio atual:
[Docs/Prisma_No_Site.md](../Docs/Prisma_No_Site.md).

As funções `api/admin/` e os arquivos `server/admin/` são backend Node da Vercel;
suas variáveis privadas nunca usam prefixo `VITE_`. O Studio tem entrada HTML/CSS
isolada em `admin-prisma.html` e só carrega na página após validar a sessão.

## Executar

Requer Node >=22.12 e Yarn 1.22.22. Executar nesta pasta, sem copiar o projeto para outro destino.

```powershell
yarn install --frozen-lockfile
yarn dev
```

`yarn build`, `yarn typecheck`, `yarn lint`, `yarn format:check` e `yarn test:e2e` validam a base.
O build inclui `yarn test:functions`: emite as funções como JavaScript Node/ESM e
carrega seus entrypoints sem Vite/tsx, para detectar imports incompatíveis com o deployment.
Para testes de navegador, executar antes `yarn playwright install chromium`.
Publicação na Vercel usa fallback das rotas React para `index.html`. As funções
locais `/api/admin/*` são resolvidas antes do proxy `/api/*` para o Render;
o roteamento está definido em `vercel.json`.

## Organização

```text
src/
  app/                    # composição, configuração, providers, router, navegação e cache
    layouts/              # autenticação e estrutura lateral comum pública/privada
    components/           # sidebar reutilizável, menus contextuais, header e footer
  features/
    auth/
      api/                # login, cadastro, consulta/revogação da sessão
      model/              # contexto tipado de sessão
      hooks/              # sessão, logout e envio de formulários
      components/         # campos, formulário, painel visual, provider e guard
      pages/              # login/cadastro e perfil em consulta
    institutional/
      model/              # informações editoriais, etapas, referências e fluxos
      components/         # apresentação dos fluxos no padrão MUI
      pages/              # início e páginas institucionais
    dashboard/
      api/                # contratos validados em runtime e consultas
      hooks/              # estado remoto e query keys
      components/         # filtros, cards, gráficos, tabelas, detalhe e feedback
      model/              # limites de datas em America/Sao_Paulo
      pages/              # dashboard, histórico e detalhe
  shared/
    api/                  # transporte HTTP sem domínio
    theme/                # tokens e tema MUI
    ui/                   # composição reutilizável de página
    lib/                  # formatação de números e datas
```

Features dependem de shared; shared não importa features/app. Estado remoto fica no Query, estado local nos componentes. Criar novas features conforme necessidades reais; não há camadas vazias por antecipação. Alias `@/` aponta para `src/` no TypeScript e Vite.

Validação de formulários fica em `auth/model/form_validation.ts` e
`dashboard/model/filter_validation.ts`. Os hooks `useAuthForm` e `useFilterForm` cuidam
do envio, feedback e prevenção de duplicidade; os componentes apenas apresentam os
campos. Essas verificações do cliente não substituem autenticação/autorização e validação
de entrada na API online. Nenhuma responsabilidade do site foi transferida ao Raspberry.

Login/cadastro aguardam a consulta da sessão e oferecem nova tentativa em caso de
falha. Durante o envio, os campos e a alternância de visibilidade ficam bloqueados;
senha e confirmação têm limite de 128 caracteres também no HTML.

## Design e conteúdo

Laranja #F97316, verde #15803D, grafite #111827 e branco; Montserrat/Roboto locais por
Fontsource. Botões laranja usam texto grafite. Revisar usa a extensão semântica vermelha
#B91C1C do tema; erros de execução não entram nessa classe. Gráficos têm alternativa tabular
e animação reduzida conforme preferências do usuário. Sem fotografias ou medições inventadas.

O visual de autenticação e dashboard foi adaptado à referência aprovada: sidebar grafite,
ações laranja, superfícies claras, três indicadores de classificação e análises recentes.
A marca tem símbolo vetorial original; o painel de login usa uma ilustração decorativa
identificada como tal, nunca apresentada como fotografia ou resultado de análise.
Planejamento, resultados, referências e revisão da equipe mantêm pendências editoriais explícitas.
As informações institucionais ficam separadas da apresentação, aproveitando a
organização da cópia `OrangeVision_`. A página de desenvolvimento distingue as
análises oficiais das amostras experimentais, sem unir seus indicadores.
Escopo da consolidação: [Docs/Consolidacao_OrangeVision.md](../Docs/Consolidacao_OrangeVision.md).

### O Projeto e divisores

A rota `/projeto` consolida contexto, problema, solução, objeto de estudo, métricas,
ODS 2, escopo, resultado esperado e referências, sem repetir os blocos de ODS e limites.
O cabeçalho é centralizado e os blocos são separados pelo componente decorativo
`src/shared/ui/OrangeVisionDivider.tsx`, que adapta linhas, pontos e texto em telas
pequenas e não é anunciado repetidamente por leitores de tela.

Os textos ficam em `src/features/institutional/model/project.ts`. A referência da
Embrapa foi identificada no [catálogo Infoteca-e](https://www.infoteca.cnptia.embrapa.br/infoteca/handle/doc/681766)
como *Comportamento de citros no Amazonas* (2007, Documentos 55). As fontes fundamentam
o contexto; não comprovam acurácia do classificador. O agronegócio é contextualizado
como setor primário, e os periféricos continuam opcionais. `tests/project.spec.ts`
cobre a consolidação, os divisores e a acessibilidade em mobile e desktop.

### Planejamento do projeto

A rota pública `/planejamento` apresenta introdução, 5W2H, sete etapas, cronograma
previsto de setembro a novembro de 2026 e entregas esperadas. O conteúdo fica em
`src/features/institutional/model/planning.ts`, separado da apresentação em
`components/PlanningOverview.tsx`. Períodos previstos não indicam conclusão; orçamento,
calibração e evidências de bancada continuam identificados como pendentes. Sensores e
atuadores são opcionais no fluxo com câmera.

O cronograma tem tabela semântica, indicação textual dos períodos e rolagem horizontal
local acessível por teclado no mobile. O rodapé institucional é compartilhado pelo
layout público. `tests/planning.spec.ts` cobre conteúdo, períodos, ausência de consultas
a métricas privadas, responsividade e acessibilidade automática.

### Equipe e fotos

A rota pública `/equipe` reúne os seis perfis fornecidos pela equipe, com formação,
experiência profissional e atuação no projeto. Os dados ficam em
`src/features/institutional/model/team.ts`, e os cards em
`src/features/institutional/components/TeamOverview.tsx`.

Para adicionar fotos, coloque retratos autorizados em `src/assets/team/`, usando os
nomes documentados em [src/assets/team/README.md](src/assets/team/README.md). Os assets
são reconhecidos pelo Vite e entram no build. Fotos não fornecidas recebem iniciais;
não há imagens fictícias ou requisições a arquivos ausentes. `tests/team.spec.ts`
verifica perfis, responsividade, acessibilidade e apresentação sem foto.

### Referencial teórico

A rota `/referencias` apresenta a fundamentação em citricultura, características
visuais, processamento de imagens, aplicação das quatro métricas, score experimental,
ODS 2 e limitações. Os dados ficam em `src/features/institutional/model/theory.ts`,
com apresentação em `components/ReferencesOverview.tsx` e divisores compartilhados.

A descrição da Pêra-Rio foi conferida na página 23 de *Comportamento de citros no
Amazonas*. As explicações de HSV, máscaras e contornos seguem a documentação OpenCV,
e a descrição do score segue o executor atual. A bibliografia reúne 11 fontes, com
links e utilização no projeto, incluindo React, FastAPI, PostgreSQL e Neon; Streamlit
não faz parte do dashboard atual. Artigos científicos ainda dependem de seleção e
fichamento, e referências não comprovam calibração, acurácia ou diagnóstico.

`tests/references.spec.ts` verifica conteúdo, links, navegação por teclado das citações,
responsividade e acessibilidade. O endereço `/referencias` e o menu existente foram
preservados.

### Recursos opcionais

O fluxo `/dashboard/inspecoes` usa configuração da API para aparecer no menu somente quando
habilitado. Permite iniciar/confirmar pedido idempotente, exibir código temporário e solicitar
encerramento real, sem disparar câmera remota. Código só fica em memória; não há credencial de
equipamento no frontend. Guia: `../Docs/Raspberry_Sessoes_Inspecao.md`.

- Foto no login é opcional. Se houver um arquivo público autorizado em `public/images/`,
  configurar, por exemplo, `VITE_AUTH_IMAGE_URL=/images/laranjas.webp`. Somente caminhos locais
  são aceitos; ausência ou falha da imagem mantém a ilustração. Reiniciar Vite após alterar env.
- Câmera ao vivo, captura, dispositivos e periféricos não são requisitos para navegar no site.
  Sem contrato/capacidades reais, não são exibidos menus ou comandos que simulem esses recursos.
- `/dashboard/perfil` exibe nome e e-mail da sessão em modo de consulta. Não há botão de salvar,
  recuperação ou alteração de senha sem endpoint correspondente.
- O dashboard exibe até cinco registros recentes; o histórico completo mantém paginação do
  servidor. Imagens de análise ausentes têm indicação textual/ícone, sem fotos inventadas.
- Layouts público, autenticação e dashboard são separados; no mobile, a sidebar vira um drawer.
- A página inicial e as páginas institucionais também usam menu lateral. Conteúdo público não
  exige cadastro nem consultas de métricas; sessão validada personaliza o cabeçalho e os acessos.

### Dashboard pessoal e comparação

- A saudação usa o nome real da sessão. No modo legado, o conjunto é autorizado por dispositivo
  e inclui somente registros sem sessão. No modo de inspeções, todas as leituras pessoais
  exigem o proprietário da sessão da análise. Não há filtro pelo nome nem atribuição automática
  do histórico à pessoa atualmente logada.
- Os cards recebem a comparação de `GET /api/metrics/comparison`, com os mesmos filtros nos
  dois períodos. O período anterior termina no início do atual e possui a mesma duração
  nominal, calculada pelo backend em UTC; os limites são exibidos em America/Sao_Paulo.
- Cada classificação exibe sua participação sobre o total do recorte, não sobre as
  linhas visíveis do histórico. O tooltip da distribuição mostra quantidade e percentual;
  total zero mantém a participação indisponível.
- Para um período atual em andamento, somente registros anteriores a `observed_end/as_of`
  entram nos indicadores. A interface avisa que os valores atuais são parciais; não extrapola
  resultados futuros nem apresenta esse recorte como período já encerrado.
- Aprovadas representa APROVADA; Não aprovadas agrupa ATENCAO + REVISAR, preservando o
  detalhamento de cada classe. Atenção não é uma rejeição definitiva ou diagnóstico da fruta.
- Diferença absoluta e percentual vêm da API. Base anterior zero retorna percentual nulo;
  taxa com denominador zero é indisponível. Diferença de taxa é mostrada em pontos percentuais.
- A tabela separa diferença absoluta e variação percentual; os limites temporais e a
  referência de consulta permanecem visíveis mesmo quando os dois períodos estão vazios.
- O histórico informa o intervalo exibido, e suas tabelas/paginação têm identificação
  acessível. O detalhe agrupa métricas, rastreabilidade e justificativa, preservando nulos.
- Os dois recortes da comparação compartilham snapshot. Histórico e série temporal continuam
  sendo consultas independentes, com seus próprios horários de referência.
- Cache e requests de comparação são escopados por usuário/filtros. Logout/troca de conta
  cancelam requests e impedem que uma resposta tardia mostre os dados da pessoa anterior.

## Integração

O `.env` local contém apenas `VITE_API_BASE_URL=/api` e `VITE_API_ENABLED=true`.
O exemplo é versionável; o `.env` é ignorado. Verifique se não existe `.env.local`
antigo sobrescrevendo essas variáveis. Alterações em env exigem reiniciar o Vite.
Todas as variáveis `VITE_*` são públicas: nunca inserir credenciais, cookies ou chaves.
As seis variáveis administrativas sem esse prefixo, documentadas no guia do Prisma,
são consumidas somente pelas funções Vercel ou pelo servidor local em `dev-admin.ts`.

A API online executa em `http://127.0.0.1:8001`, com proxy Vite para `/api`.
Configuração, migration e execução: `../web_api/README.md`.
Sem conexão/migration, os fluxos exibem indisponibilidade; não simulam autenticação.

Rotas públicas: início e seis páginas institucionais, `/login`, `/registrar` e 404.
Privadas: `/dashboard`, `/dashboard/historico`, `/dashboard/analises/:id`, `/dashboard/perfil`
e a rota opcional `/dashboard/inspecoes`. Guards aguardam consulta de sessão; a API online
aplica a política de autorização correspondente ao modo habilitado.
Cadastro não autentica automaticamente nem concede dispositivos. Senhas não entram em
Query mutations, cache, storage ou URLs. Logout confirma revogação no servidor e remove
cache privado; falha é explicitada e dados locais são retirados da área privada.

Contrato implementado no serviço online: autenticação em `/api/auth/*`, lista/detalhe em
`/api/analyses`, resumo/distribuição/evolução/comparação em `/api/metrics/*`. Zod valida respostas em
runtime. Paginação de 20 itens, filtros de classe/período na URL, limite de 366 dias,
datas convertidas a partir de America/Sao_Paulo, fim exclusivo. Lote/dispositivo não são
oferecidos como filtros enquanto as respectivas opções autorizadas não forem integradas.

Polling de 30 segundos, pausado em segundo plano; AbortSignal, timeout e retry limitado
a rede/5xx. Sem retry automático em credenciais, 401/403/validação ou schema inválido.
Cache privado é escopado por usuário/filtro; logout e expiração cancelam requests.
Null não vira zero. Total e gráficos vêm de agregados do servidor, não da página atual.
Horários de consulta são distintos; sincronização real/cobertura de dias não são inventadas.

Testes Playwright usam contratos simulados **apenas nos arquivos de testes**. Isso valida
renderização, responsividade, formulários, guard e cancelamento; não comprova integração
com banco real. Não existem mocks de produção ou dados de demonstração no app.
`yarn test:e2e` gera o build de produção e executa 51 testes Chromium contra `vite preview`,
com movimento reduzido. Screenshots de contrato ficam em `test-results/`, ignorado no Git.
Inclui verificações automáticas de acessibilidade com axe para autenticação, dashboard e
perfil e navegação pública. Isso complementa a inspeção visual/teclado, sem substituir avaliação
humana completa. Inclui períodos vazios, comparação sem base, filtros, troca de conta com
request pendente e larguras de 320/375/390/768/900/1024/1440 px.

A integração HTTP com o Neon foi verificada separadamente na API, após aplicar a migration
autorizada em 20/10/2026. Cadastro, login, sessão, expiração, logout, CSRF e consulta sem vínculo
passaram com registros temporários revertidos. Registro: `../web_api/migrations/APPLIED.md`.

## Próximos incrementos

1. Validar unidades/calibração do processamento com dados de bancada; o schema UUID/timestamptz já foi inspecionado.
2. Liberar vínculos de dispositivo pelo responsável para contas que precisem consultar análises existentes.
3. Completar cronograma/custos, bibliografia e evidências reais; confirmar descrições da equipe.
4. Definir armazenamento privado de imagens e autorização antes de mostrar fotos remotas.
5. Validar estados de API real e permissões em ambiente de integração; definir hospedagem e fallback das rotas.

A API online foi adicionada sem alterar o processo legado do Raspberry. A migration aditiva
de autenticação foi aplicada com autorização explícita; não houve commit Git, deploy ou
alteração nos documentos de requisitos.
