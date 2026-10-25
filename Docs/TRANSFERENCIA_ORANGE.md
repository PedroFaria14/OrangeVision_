# Transferência para Orange/OrangeVision_

> Registro do snapshot inicial. Posteriormente, por solicitação do usuário, a
> área `/dashboard` recebeu personalização visual isolada. Páginas públicas,
> login e cadastro continuam básicos. O estado atual e os comandos de execução
> estão no README da raiz; a API padrão agora é a publicada no Render.

## Origem e destino

- Origem preservada: `D:\Estudo_Pedro\USF\Arquitetura\Projeto\OrangeVision`.
- Destino: `D:\Estudo_Pedro\USF\Arquitetura\Projeto\Orange\OrangeVision_`.
- O destino já continha `.git`, sem commits locais ou arquivos de aplicação.
  Seu Git/remoto foram preservados; não foi copiado o `.git` da origem.

## Dados transferidos

212 arquivos de código/configuração/documentação/dados foram copiados no snapshot
inicial, seguidos pelos arquivos do frontend HTML básico e documentação nova.
O modelo ONNX e as imagens locais foram incluídos no computador.

O SQLite `backend/device/data/device_pipeline.db` foi transferido pela API de backup
do SQLite, com conexão de origem somente leitura, considerando o WAL. O backup
passou em `integrity_check`, e as contagens de todas as tabelas coincidiram com o
snapshot. A foto pendente de revisão foi incluída. IDs, grants, leases e relações
de propriedade não foram reescritos. Não foi usado simples copy do `.db` aberto.

Os quatro arquivos privados de configuração ativos (`backend/.env`,
`backend/device/.env`, `web_api/.env`, `Frontend/.env`) foram comparados sem exibir
seu conteúdo; a cópia ficou idêntica. Não foram encontrados caminhos antigos em
variáveis privadas terminadas em `_PATH`. Banco remoto e suas contas permanecem
os mesmos, sem migration nova nem alteração de dados remotos nesta tarefa.

Não se transferiram instalações/caches: node_modules, dist, venvs antigos,
__pycache__, caches de ferramentas ou resultados temporários de teste. Dependências
foram instaladas novamente no destino. Python usou versões instaladas na origem
(39 distribuições web, 15 do dispositivo), sem misturar GUI/headless do OpenCV.
Registros locais dessa instalação estão em `.transfer-state`, ignorado no Git.

## Frontend cru

- HTML nativo em React: links, formulários, botões, imagens, listas, tabelas e DLs.
- Removidos MUI/Emotion, fontes, tema, estilos inline, ilustrações e camada de charts.
- Mantidos módulos de API, validação, sessão/cache, filtros e pareamento da origem.
- Dados de indicadores/comparação/evolução permanecem em tabelas. A detecção
  permanece em texto/coordenadas, com foto e máscara; sem overlay CSS.
- Campos ausentes continuam indisponíveis, sem gerar números ou imagens fictícias.
- Páginas públicas, autenticação, perfil, dashboard, histórico, detalhe, inspeções
  e amostras mantêm suas rotas.

## Git e execução

O `.gitignore` do destino protege envs, SQLite, fotos locais, pesos e venvs,
sem excluir todo o código de backend. As referências absolutas ativas dos guias
foram atualizadas para o caminho novo. O inicializador usa `$PSScriptRoot` e
recusa reutilizar silenciosamente serviços/executores de outra pasta.

Feche as execuções antigas antes de iniciar a cópia nova. O backup é um snapshot:
alterações posteriores na origem não são automaticamente espelhadas no destino.
A origem não foi apagada, movida ou limpa. Nenhum commit/push foi executado.

## Validação executada no destino

- Frontend: build/TypeScript e ESLint aprovados.
- 15 testes funcionais Playwright aprovados, incluindo cadastro/login, autorização,
  logout/expiração, zero sem taxa inventada, filtros, tabelas/detalhes, pareamento
  com CSRF/nonce, upload/estados/máscara e acessibilidade automática.
- DOM verificado sem folhas CSS, tags style ou atributos style nas rotas testadas;
  build sem assets CSS/fontes. As screenshots de fixtures estão em
  `Frontend/test-results`, não são medições reais.
- 86 testes do dispositivo aprovados; 81 da API aprovados e 3 testes PostgreSQL
  concorrentes skipped (sem banco dedicado). Warning Starlette/httpx já existente.
- Modelo verificado pelo SHA-256 a partir do novo diretório; venv executado com
  `sys.prefix` do destino, sem depender do venv da origem.
- Configurações/dados privados confirmados como ignorados por Git.

## Pendências herdadas

O trabalho anterior de recuperação/envio da foto e validação física foi pausado
por solicitação do usuário. Seu código e dados foram copiados no estado atual;
esta transferência não conclui o ensaio SQL interrompido nem valida webcam,
Raspberry, calibração de qualidade ou testes concorrentes pendentes.
