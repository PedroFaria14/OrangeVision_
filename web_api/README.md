# OrangeVision — API online

Backend do site, localizado em **`OrangeVision/web_api/`**, fora da pasta `backend/` do
Raspberry. Serviço FastAPI separado de `backend/app` (processo legado/local). Não inicializa câmera,
GPIO, SQLite nem sincronizador. Não é necessário instalar suas dependências no Raspberry.

## Divisão de responsabilidades

Sessões de inspeção por usuário, provisionamento e novo pipeline local estão documentados
em [Docs/Raspberry_Sessoes_Inspecao.md](../Docs/Raspberry_Sessoes_Inspecao.md).
`WEB_INSPECTIONS_ENABLED=false` é o padrão. A migration 002 foi preparada, **não aplicada**
ao Neon nesta entrega. Quando ativada, a propriedade da sessão restringe todas as consultas
pessoais; registros antigos sem sessão não recebem dono automaticamente. Ao desativar,
registros que já tenham sessão não voltam a ser expostos pela regra legada por dispositivo.

```text
Frontend/src/features/
  */model/           # schemas e validação de formulário para feedback imediato
  */hooks/           # envio, estado, bloqueio de duplicidade e consultas
  */components/      # campos, filtros, tabelas, gráficos e feedback visual
  */api/             # chamadas HTTP e validação das respostas

web_api/
  main.py            # composição da API e ciclo de vida
  api/               # rotas, dependências, cookies, CSRF e tradução de erros
  application/       # casos de uso e interfaces de persistência/segurança
  infrastructure/    # SQL PostgreSQL, Argon2id e mapeamento do schema legado
  contracts.py       # contratos HTTP/Pydantic usados pelo OpenAPI
  config.py          # configuração exclusiva da API online
  migrations/        # scripts revisáveis; nunca aplicados automaticamente
  tests/             # contratos, segurança, serviços e fronteiras arquiteturais
```

Fluxo: **componente → hook/validação do cliente → HTTP → rota → serviço → repositório**.
O frontend valida para UX; a API continua revalidando entrada, credenciais e permissões,
pois requests podem ser enviadas sem o site. Rotas não executam SQL nem hashing; serviços
dependem de interfaces, sem importar FastAPI, psycopg, Argon2 ou código do Raspberry.
Argon2 e PostgreSQL são adaptadores de infraestrutura injetados na composição HTTP.

Os módulos `auth.py` e `queries.py` mantêm fachadas de imports/consultas anteriores, sem
duplicar as implementações. Endpoints, payloads, OpenAPI, `.env` e comando de inicialização
foram preservados. Não foi feita nenhuma alteração no processo legado `app/` do Pi.

## Configuração local

Na raiz **`OrangeVision`**, com Python 3.12+:

```powershell
python -m venv .venv-web
.\.venv-web\Scripts\Activate.ps1
python -m pip install -r web_api/requirements-dev.txt
python -m web_api.inspect_schema
```

O `.env` da API foi movido junto para `web_api/.env`, sem alterar seus valores.
`WEB_DATABASE_URL` tem prioridade; `DATABASE_URL` do ambiente também é aceita. Somente em
development, se ambas estiverem vazias, pode reutilizar a conexão existente em `backend/.env`.
Essa compatibilidade é opcional: no Render/production, a API não consulta a pasta do Pi.
Nenhum valor da conexão é impresso ou enviado ao navegador. Configure uma conexão real no
servidor; placeholders/ausência bloqueiam o startup com mensagem segura.

| Variável              | Uso                                                                                 |
| --------------------- | ----------------------------------------------------------------------------------- |
| `WEB_DATABASE_URL`    | Conexão PostgreSQL online, opcional se `DATABASE_URL` existente estiver configurada |
| `WEB_ENV`             | `development` local; **`production` obrigatório no deploy**                         |
| `WEB_ALLOWED_ORIGINS` | Origens exatas, separadas por vírgula, sem caminhos, wildcard ou barra final        |
| `WEB_SESSION_SECONDS` | 300–86400; padrão 28800 (8 horas)                                                   |

Em produção, HTTPS obrigatório: cookie `Secure`, `HttpOnly`, `SameSite=Lax`, restrito a
`/api`. O navegador usa o mesmo domínio via reverse proxy; não exige cookies cross-site.
Não publicar PostgreSQL, API key ou credenciais de dispositivo em `VITE_*`.

## Banco e migration — etapa manual

`migrations/001_web_auth.sql` **não é executada pelo startup ou pelas requests**. Antes de
aplicar, inspecionar schema real, comparar tipos/unidades, revisar com o responsável e
preparar backup. A migration adiciona o schema `orangevision_web`; não altera `analises`,
`dispositivos` ou dados existentes. Se já houver autenticação no banco, adaptar antes de
criar um segundo cadastro. A migration foi aplicada no Neon configurado com autorização
explícita em 20/10/2026; ver `migrations/APPLIED.md`.

Para outros ambientes, revisar primeiro. O comando abaixo sem flags apenas mostra o plano:

```powershell
python -m web_api.migrate
# Somente após aprovação para o ambiente correto:
python -m web_api.migrate --apply
```

A leitura pressupõe `analises` no search_path com colunas do código legado:
`id`, `dispositivo_id`, `data_hora`, `classificacao`, `cor_media`, `regioes_anormais`,
`circularidade`, `assimetria`, `score_visual`, `versao_algoritmo`.
IDs devem ser UUID, e `data_hora` deve ter timezone. `cor_media`, `regioes_anormais` e
`assimetria` legadas são interpretadas como percentuais 0–100 conforme `app/schemas.py`;
o adaptador converte para razões 0–1 no contrato externo. **Confirmar contra o banco real**
antes de liberar o dashboard; os nomes não provam a unidade medida pelo processamento.

Novos usuários não recebem administrador ou acesso automático a equipamentos. Após
confirmar legitimidade e consentimento, o operador do banco concede vínculo específico
em `orangevision_web.device_access(user_id, device_id)`. Não existe tela pública para isso.
Sem vínculo, listagens/agregados ficam vazios; detalhe inacessível retorna 404 para não
revelar a existência de análises de outro usuário.

## Execução local — a partir da raiz OrangeVision

Após configuração e revisão/aplicação da migration:

```powershell
python -m uvicorn web_api.main:app --host 127.0.0.1 --port 8001
```

Em outro terminal, na pasta `Frontend`: `yarn dev`. O proxy Vite encaminha `/api` para
`127.0.0.1:8001`. Não usar `app.main` na porta 8001: seu contrato/autenticação são diferentes.

Se o virtualenv anterior já estiver em `backend/.venv-web`, ele não foi movido: ambientes
virtuais podem ter caminhos absolutos. Ative-o pela raiz com
`.\backend\.venv-web\Scripts\Activate.ps1`, ou crie `.venv-web` na raiz pelos comandos acima.

OpenAPI 3.1: `/openapi.json`, documentação `/docs`, artefato `../contracts/web-openapi.yaml`.
Regenerar sem acessar o banco: `python -m web_api.export_contract`.

## Preparação para o Render — sem deploy automático

Criar um **Web Service Python**, usando a raiz do repositório OrangeVision (Root Directory
vazio/raiz, **não** `backend` e **não** `web_api`). Como `web_api` é um pacote Python,
o comando deve ser executado a partir do diretório que contém essa pasta.

| Campo             | Valor                                                            |
| ----------------- | ---------------------------------------------------------------- |
| Build Command     | `pip install -r web_api/requirements.txt`                        |
| Start Command     | `python -m uvicorn web_api.main:app --host 0.0.0.0 --port $PORT` |
| Health Check Path | `/health`                                                        |
| Python            | Selecionar versão compatível, Python 3.12+                       |

Configurar nas **Environment Variables** do Render:

```dotenv
WEB_ENV=production
WEB_DATABASE_URL=CONEXAO_POSTGRESQL_REAL_CONFIGURADA_SOMENTE_NO_RENDER
WEB_ALLOWED_ORIGINS=https://DOMINIO_REAL_DO_FRONTEND
WEB_SESSION_SECONDS=28800
```

Os valores em maiúsculas são placeholders, não credenciais funcionais. Não enviar `.env`
ao Git ou copiar secrets para o frontend. O processo online instala somente as dependências
de `web_api`, sem iniciar ou importar o backend do Raspberry. Não usar `--reload` em produção.

O frontend ainda usa `/api` na mesma origem: na hospedagem do site, configurar proxy/rewrite
compatível para o endereço HTTPS do Web Service, antes do fallback de rotas React. O proxy
Vite é apenas de desenvolvimento. Não apontar `VITE_API_BASE_URL` diretamente para um domínio
externo com o contrato atual; cookies e transporte estão preparados para mesma origem.

Nenhum deploy ou migration é executado por essas instruções. `/health` indica processo vivo,
não valida schema, permissões ou consultas reais; revisar/aplicar migration e validar banco
separadamente antes de liberar uso em produção.

## Segurança e operação

- Argon2id: 19 MiB, 2 iterações, paralelismo 1; salt por senha. No máximo dois hashes por
  processo simultaneamente; medir custo/RAM no servidor escolhido e limitar workers.
- Login/cadastro: até 10 tentativas por IP e por e-mail em 15 minutos, contadores
  transacionais no PostgreSQL. Não confiar em headers encaminhados sem proxy confiável.
- Sessões aleatórias opacas; apenas SHA-256 do token aleatório é armazenado. Isso não é
  hashing de senha. Login rotaciona a sessão do navegador; expiração verificada no banco.
- Logout exige origem permitida e `X-CSRF-Token`; login/cadastro exigem origem permitida.
- SQL parametrizado, autorização por vínculo de dispositivo em todas as leituras.
- Compatibilidade com pooler Neon: o timeout de queries é aplicado por
  `SET LOCAL statement_timeout = 10000` dentro da transação, não por `options` no startup.
  O limite permanece em 10 segundos e não vaza para outra conexão/transação do pool.
- Logs JSON sem e-mail, senha, cookie, hash, payload ou URL privada; request ID gerado no
  servidor. Respostas privadas têm `Cache-Control: no-store`.
- Agendar limpeza de sessões/contadores expirados, com revisão operacional. Não há loop
  de manutenção permanente dentro do servidor nem alteração de schema por request.
- No proxy de produção, limitar corpo (por exemplo, 8 KiB nas rotas de credenciais),
  conexões e taxa global; ativar TLS e headers de segurança do site. Não expor a API legada.

## Contrato de consulta

Filtros: `start`, `end` com offset; início inclusivo e fim exclusivo; `classification` e
`device_id` autorizado. Paginação `limit=1..100`, `offset=0..100000`; ordenação fixa
`data_hora DESC, id DESC`. UI usa 20 por página. Não há filtro de lote sem coluna/contrato.

Resumo/distribuição são calculados sobre todo o recorte autorizado, apenas classes válidas.
Denominador zero retorna taxa nula. Cada resposta tem horário de consulta, sem alegação
de snapshot comum entre endpoints. Série diária exige período de até 366 dias, agrupa em
`America/Sao_Paulo` e retorna somente dias observados: ausência não é zero confirmado.

### Comparação pessoal — `GET /api/metrics/comparison`

Nova consulta aditiva, sem mudança nos endpoints anteriores e sem nova migration.
Exige sessão e `start`/`end` válidos com offset, duração maior que zero e de até 366 dias;
o início deve ser anterior ao horário da consulta. Aceita os mesmos filtros de classe e
dispositivo, sempre derivados do conjunto autorizado da conta autenticada.

O período anterior é `[start - (end - start), start)`, com cálculo em UTC. Os períodos
nominais têm a mesma duração decorrida, não necessariamente um mês de calendário. Para
intervalos em andamento, `observed_end = min(end, as_of)` evita contar timestamps futuros,
e `in_progress` identifica que o recorte atual ainda é parcial. A comparação com o período
anterior encerrado não é normalizada nem extrapolada para prever o restante do atual.

Resposta: `current`, `previous`, `changes`, `as_of`, `timezone` e `boundary`. Cada período
inclui limites, contagens por classe, total, última análise, taxa e `not_approved` (Atenção +
Revisar). `changes` retorna diferença absoluta, percentual por contagem e `approval_rate_pp`.
Base anterior zero produz percentual nulo; taxa exige denominador positivo em cada período.
Atenção continua distinta de Revisar e não equivale a rejeição definitiva.

Os dois períodos são agregados em uma consulta SQL sobre todo o recorte autorizado, em
transação repeatable read/read only. O escopo é aplicado dentro do join em ambos os períodos:
`device_access` no modo legado sem sessão e proprietário da inspeção no modo pessoal.
O ID de pessoa fornecido por query string não substitui a sessão autenticada.
Não há comparação entre pessoas ou total global exposto a contas sem vínculo. Essa consulta
compartilha snapshot internamente; não promete snapshot comum com histórico/timeseries.

Testes cobrem duração/adjacência, mudança de ano/offset, período em andamento, base zero,
taxa anterior igual a zero com amostra válida, agrupamento das classes, permissões e
compatibilidade dos contratos existentes. A consulta também foi validada no Neon em modo
somente leitura, com um identificador sem vínculos: ambos os períodos retornaram zero sem
expor registros de outra conta. A validação com contagens positivas usa dados controlados
nos testes; não é medição de qualidade ou calibração de frutas reais.

## Testes e limites da entrega

```powershell
python -m pytest web_api/tests -q
ruff check web_api
ruff format --check web_api
```

Testes locais de contrato, validação, hashing, CSRF, limites de capacidade e autorização
na borda não substituem testes com PostgreSQL de integração. A conexão real ao Neon e as
consultas do schema foram validadas. A migration aditiva criou as quatro tabelas de autenticação
sem alterar as três tabelas originais. Cadastro, login, sessão, logout, expiração, duplicidade,
CSRF e leituras sem vínculo passaram pela API com PostgreSQL real.

Verificação explícita, com `requirements-dev.txt`, em um banco já preparado:

```powershell
python -m web_api.verify_database --run
```

Essa ferramenta executa escritas temporárias de autenticação em uma transação com rollback
obrigatório, injeta essa conexão no adaptador de autenticação somente durante o teste e
confirma depois que conta, sessões e contadores de teste não persistiram. As consultas de
análises usam o adaptador real. Não equivale a teste de concorrência/carga, deploy ou hardware.

Verificações executadas: 67 testes Python da API, Ruff e formatação Python;
no frontend, build/tipagem, ESLint, Prettier e 51 testes Playwright sobre build de produção.
O novo pipeline local possui 23 testes em ambiente separado. O fluxo de inspeção foi
verificado em namespaces SQL transitórios com rollback obrigatório; a migration 002 não
foi aplicada aos schemas reais. Concorrência/carga em banco dedicado e bancada continuam
pendentes, conforme o guia em Docs. Pareamento/expiração usam o horário observado no banco.
Os testes de navegador usam respostas controladas apenas no ambiente de testes, incluindo
sessão expirada, logout concorrente, dados nulos/zero, contrato inválido e larguras de
320/375/390/768/900/1024/1440 px. Não são evidência de integração real com PostgreSQL ou hardware.

Após a separação, a suíte Python inclui casos de uso com persistência injetada, fluxo
HTTP de sessão com fake somente de teste e comparação exata com o OpenAPI anterior.
Há também testes de fronteira que impedem SQL/hashing nas rotas e dependências de
framework/banco nos casos de uso. Não se trata de validação com Neon real.

## Se o Vite retornar 502 / ECONNREFUSED

O frontend e a API online continuam sendo dois processos locais. A divisão de módulos
não inicia o backend automaticamente nem remove sua necessidade. Em um terminal na pasta
raiz `OrangeVision`, com o ambiente virtual ativo, execute:

```powershell
python -m uvicorn web_api.main:app --host 127.0.0.1 --port 8001 --reload
```

Aguarde `Application startup complete` e confira `http://127.0.0.1:8001/health`. Em outro
terminal na pasta `Frontend`, mantenha `yarn dev` aberto. Se o startup falhar, analisar
o terminal do Python sem divulgar `.env` ou credenciais. Migration pendente normalmente
aparece como indisponibilidade de dados depois que a API já está acessível; não é a mesma
causa de conexão recusada na porta 8001.

Não implementados neste incremento: ingestão online por credencial individual, migração
do sincronizador legado Pi→Neon para Pi→API, captura/OpenCV/calibração, outbox atômica do
pipeline de câmera, telemetria sincronizada, armazenamento privado de imagens e deploy.
O fluxo legado foi preservado, não migrado silenciosamente. Driver/câmera, calibração,
schema remoto e hospedagem precisam ser confirmados antes desses incrementos.
