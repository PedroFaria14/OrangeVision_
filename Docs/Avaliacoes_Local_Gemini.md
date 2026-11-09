# OrangeVision — avaliação local e segunda opinião Gemini

## 1. O que esta entrega implementa

Uma captura mantém sua imagem e identidade originais. A avaliação local do
Raspberry e a avaliação visual Gemini são independentes e aparecem no mesmo
cartão em **Amostras**. O Gemini usa a foto já normalizada na Web API; não recebe
senha, cookie de usuário ou URL pública para buscar a imagem.

- A avaliação local continua funcionando sem Gemini.
- O Gemini roda em um worker servidor e pode terminar antes ou depois do local.
- Os critérios Gemini são experimentais (`orange-surface-v1`): triagem da
  superfície visível, não diagnóstico de doença, comestibilidade ou interior.
- Concordância significa categorias iguais, não validação de acurácia. Falta de
  categoria em um dos métodos torna a comparação inconclusiva.
- Uma sugestão Gemini não publica nem corrige automaticamente a classificação.
  O operador pode **Adotar sugestão Gemini**, adotar a avaliação local ou
  **Confirmar ou corrigir resultado**, registrando justificativa.
- A decisão mantém uma única análise por captura. Revisões são append-only; o
  histórico original não é sobrescrito. Os gráficos leem a decisão vigente.
- Métricas OpenCV são locais ou `null`. Um resultado qualitativo não inventa
  circularidade, proporções ou score. Uma avaliação local tardia pode fornecer
  medições reais sem substituir a decisão já adotada.

Os comandos de confirmação verificam conta, sessão de origem, equipamento,
horário de captura, CSRF, Origin e revisão esperada. Repetir o mesmo comando não
duplica decisões nem contadores.

## 2. Primeiro: diagnosticar a integração com gráficos

Na raiz que contém `web_api/`, no **ambiente da Web API no Render**, execute:

```bash
python -m web_api.diagnose_dashboard
```

O comando é somente leitura. Usa o mesmo carregamento de configuração da API e
não imprime URL do banco, chave Gemini, senhas ou dados das amostras. Não reutilize
a conexão de leitura do Prisma Studio para diagnosticar o papel da API.

O JSON inclui:

| Campo/status | Significado |
| --- | --- |
| `enabled` | Condições estruturais e acessos verificados para publicação |
| `inspections_disabled` | O processo não carregou `WEB_INSPECTIONS_ENABLED=true` |
| `schema_unavailable` | Falta coluna, FK ou índice único do vínculo da migration 007 |
| `permissions_missing` | Estrutura existe, mas o papel não tem os acessos necessários |
| `diagnostic_failed` | Não foi possível concluir; só o tipo de erro é exibido |

Os checks distinguem coluna física de coluna visível ao papel da API e verificam
leitura/escrita necessárias, schemas, sessão e acesso à projeção de decisões.
`analysis_id: null` em uma resposta antiga não prova que a 007 existe: a API possui
fallback para instalações anteriores.

## 3. Migrations e permissões

A aplicação operacional das migrations é separada da publicação do código.
Confirmar ambiente, revisar SQL e autorizar antes de executar `--apply`.

```bash
# Somente planos; não conectam ao banco:
python -m web_api.migrate --migration 007
python -m web_api.migrate --migration 008

# Após revisão/autorização, com a conexão do ambiente correto:
python -m web_api.migrate --migration 007 --apply
python -m web_api.migrate --migration 008 --apply
python -m web_api.diagnose_dashboard
```

Pré-requisitos: estrutura legada `public.analises` e migrations 001–005. A 006
continua sendo a etapa independente do cadastro de equipamentos.

- **007:** adiciona `image_samples.analysis_id`, FK e índice único.
- **008:** cria `sample_evaluations`, `gemini_jobs`, `gemini_attempts`,
  `sample_decisions` e a view `effective_analyses`.
- A 008 permite `NULL` nas cinco colunas de métricas de `public.analises` para
  decisões qualitativas. Não altera os valores de linhas existentes. O contrato
  de resultados locais completos continua exigindo métricas e calibração válidas.
- Nenhuma migration agenda chamadas pagas, publica fotos antigas ou assume dono.
- Ambas usam transação, timeout de lock de 5 s e de execução de 30 s. Se uma
  estrutura parcial já existir, conferir seu estado antes de reaplicar: `IF NOT
  EXISTS` não repara uma coluna antiga que esteja sem a FK correta.

Se o papel que aplica migrations for diferente do papel de runtime, revisar
grants antes de liberar a funcionalidade. O exemplo abaixo **não deve ser
executado com o nome de exemplo**; um administrador deve substituir
`PAPEL_DA_API` pelo papel efetivo e preservar os grants existentes:

```sql
GRANT USAGE ON SCHEMA public, orangevision_web TO "PAPEL_DA_API";
GRANT SELECT, INSERT ON public.analises TO "PAPEL_DA_API";
GRANT INSERT ON orangevision_web.ingestion_receipts TO "PAPEL_DA_API";
GRANT SELECT ON orangevision_web.inspection_sessions TO "PAPEL_DA_API";
GRANT SELECT (analysis_id), UPDATE (analysis_id)
  ON orangevision_web.image_samples TO "PAPEL_DA_API";
GRANT SELECT, INSERT ON orangevision_web.sample_evaluations,
  orangevision_web.sample_decisions TO "PAPEL_DA_API";
GRANT SELECT, INSERT, UPDATE ON orangevision_web.gemini_jobs,
  orangevision_web.gemini_attempts TO "PAPEL_DA_API";
GRANT SELECT ON orangevision_web.effective_analyses TO "PAPEL_DA_API";
```

Esses são complementos aos acessos já exigidos pela API. O worker precisa ler
imagens/jobs, inserir avaliações/tentativas e atualizar jobs/tentativas. Se usar
um papel exclusivo, conceder esses acessos específicos; não torná-lo superusuário.
Não adicionar `UPDATE`/`DELETE` às tabelas de avaliações ou decisões para operar
esta funcionalidade.

## 4. Onde configurar a chave e as variáveis

Crie/gerencie a chave no [Google AI Studio](https://aistudio.google.com/apikey).
No Render, abra **Environment** do serviço servidor que executará o worker e
adicione `GEMINI_API_KEY`. Não coloque no React, Vercel client-side, Raspberry,
Git ou mensagens de diagnóstico. O adapter lê explicitamente `GEMINI_API_KEY`.

| Variável | Web API | Worker | Padrão |
| --- | --- | --- | --- |
| `WEB_GEMINI_ENABLED` | `true` para agendar/solicitar | `true` para executar | `false` |
| `GEMINI_API_KEY` | Não é usada para chamadas pela API HTTP | Obrigatória | vazia |
| `GEMINI_MODEL` | Modelo registrado ao agendar | Usa o modelo registrado no job | `gemini-3.8-flash` |
| `GEMINI_TIMEOUT_SECONDS` | — | Timeout HTTP de cada tentativa | `30` |
| `GEMINI_DAILY_LIMIT` | — | Limite global de tentativas por dia UTC | `50` |
| `GEMINI_USER_DAILY_LIMIT` | — | Limite de tentativas por conta/dia UTC | `10` |
| `WEB_DATABASE_URL` | Conexão da API | Mesmo banco, com papel autorizado | obrigatória |
| `WEB_INSPECTIONS_ENABLED` | `true` para publicar decisões nos gráficos | Preservar configuração do ambiente | `false` |

O worker também usa `Settings.load()`: preservar `WEB_ENV=production` e
`WEB_ALLOWED_ORIGINS` HTTPS, assim como no ambiente da API.

Configuração inicial sugerida, após preparar o banco e o worker:

```dotenv
WEB_GEMINI_ENABLED=true
GEMINI_MODEL=gemini-3.8-flash
GEMINI_TIMEOUT_SECONDS=30
GEMINI_DAILY_LIMIT=50
GEMINI_USER_DAILY_LIMIT=10
```

Conferir disponibilidade e permissões do modelo na conta. Não há troca automática
para um modelo mais caro. Ajustar os limites de chamadas global e por conta juntos:
o limite por conta deve ser menor ou igual ao global. Não foi feita chamada real
com a chave do Render durante a validação local.

## 5. Criar o worker no Render

### 5.0 Opção gratuita: worker dentro da Web API

Sem Background Worker pago, o worker roda como thread na própria Web API. No serviço
HTTP do Render, em **Environment**:

```dotenv
WEB_GEMINI_ENABLED=true
WEB_GEMINI_INPROCESS=true
GEMINI_API_KEY=<sua chave>
```

Salvar reinicia o serviço; o log mostra `gemini_worker_started`. Sem chave, a API sobe
normalmente e registra `gemini_worker_not_started`. Erros de credencial/modelo encerram só
a thread (`gemini_worker_stopped`); corrija a variável e reinicie o serviço.

Limitação do plano gratuito: a instância dorme após ~15 min sem requisições e o worker
dorme junto. Os jobs ficam no banco e são processados quando o site ou o Raspberry
acordarem a API. Para a fila andar sem espera, mantenha o site aberto ou use a opção
paga abaixo. Use uma única instância; a lease evita duplicação, mas a cota é a mesma.

### 5.1 Opção dedicada: Background Worker

A chave já configurada no serviço HTTP não inicia um processo de worker.
Criar um **Background Worker** apontando para o mesmo repositório/versão da API:

1. Root Directory: diretório que contém a pasta `web_api/`.
2. Build Command: `pip install -r web_api/requirements.txt`.
3. Start Command: `python -m web_api.gemini_worker`.
4. Copiar/compartilhar as variáveis servidor indicadas na seção anterior,
   especialmente banco, `WEB_GEMINI_ENABLED` e a chave no próprio worker.
5. Começar com uma instância e publicar a mesma versão na Web API e no worker.

O worker não abre porta HTTP e não substitui o comando Uvicorn da Web API.
Conferir disponibilidade/custo de Background Worker no plano Render utilizado.
Publicar o frontend na Vercel após disponibilizar o contrato novo da API.

É possível executar um ciclo explícito:

```bash
python -m web_api.gemini_worker --once
```

Se houver job elegível, esse comando envia uma foto ao Gemini e pode consumir
cota/cobrança. Não é um health check. Sem job, retorna `idle`. Em produção,
deixe o Background Worker executar o loop normal.

## 6. Primeiro teste funcional em produção

1. Conferir `/api/samples/config`, autenticado:
   `dashboard_enabled=true`, `dashboard_status=enabled`,
   `evaluations_enabled=true` e `gemini_enabled=true`.
2. Em uma captura já existente, clicar **Solicitar Gemini**. Isso não precisa
   reenfileirar nem apagar o resultado local. Se existir resultado local antigo,
   uma cópia de avaliação é preservada ao solicitar a segunda opinião.
3. Acompanhar `queued` → `running` → `completed`/falha e o log
   `gemini_worker_cycle` com `worker_status` no worker.
4. Conferir categoria, justificativa, critérios e modelo solicitado. A sugestão
   Gemini não altera o gráfico sozinha.
5. Em captura com sessão de origem comprovada, adotar a sugestão ou corrigir o
   resultado, preenchendo justificativa. Conferir a revisão e o mesmo `analysis_id`.
6. Verificar contadores e período da captura. A chegada tardia do Gemini não
   desloca o registro para a data da avaliação nem cria outra fruta.

Capturas novas do Raspberry são agendadas automaticamente para Gemini quando a
flag e a estrutura estão ativas e há capacidade na fila. Arquivos enviados pelo
formulário permanecem sob solicitação explícita. Fotos sem sessão comprovada
podem receber uma sugestão visual, mas não são atribuídas artificialmente a uma
inspeção para entrar nos indicadores.

## 7. Estados, recuperação e custo

- Jobs são persistidos no PostgreSQL. Reinício/deploy não elimina a fila.
- Lease de 2 minutos e token de execução impedem que um worker antigo sobrescreva
  uma tentativa nova. Timeout HTTP é configurável de 5 a 90 segundos.
- Até 3 tentativas por job; backoff e `Retry-After` são respeitados em falhas
  transitórias. Limites diários contam tentativas externas, inclusive incertas.
- Ao esgotar a cota diária, o job é preservado para o próximo dia UTC.
- Um timeout pode ocorrer depois de o provedor ter processado a chamada. Por
  isso não há promessa de cobrança exatamente uma vez.
- Há no máximo um job ativo por captura, 20 pendentes por conta e 500 globais.
- `provider_credentials`, `model_unavailable` e `provider_request_invalid`
  encerram o processo para revisão de configuração. Conferir o log e a política
  de reinício do serviço; não aumentar limites para contornar o erro.
- `response_invalid` rejeita saída fora do schema ou que invente campos métricos.
  Textos e cabeçalhos brutos do provedor não vão para logs/cliente.

Os limites são de chamadas e tokens de saída, não um teto exato em dinheiro.
Conferir preço do modelo, cotas, uso e alertas no Google. As fotos saem do servidor
para o provedor; conferir condições de tratamento de dados. O adapter usa imagem
inline, `store=false`, sem ferramentas, URLs do cliente ou histórico de conversa;
isso não substitui as políticas de retenção do provedor.

## 8. Diagnóstico rápido e interrupção

| Sintoma | Conferir |
| --- | --- |
| `dashboard_enabled=false` | Executar o diagnóstico da seção 2 com o papel da API |
| Gemini não habilitado | Flag no processo e migration/permissões da 008 |
| `Aguardando worker Gemini` persistente | Serviço de worker iniciado, banco correto e logs |
| Chave só no serviço HTTP | Configurar também no worker; não copiar para o frontend |
| `daily_limit` | Cota UTC e tentativas já registradas, não apenas resultados concluídos |
| HTTP 400/412 no provedor | `provider_request_invalid`: conferir contrato/revisão/modelo |
| Resultado ainda sem categoria | Ver justificativa de imagem insuficiente ou calibração local; não forçar classe |

Para interromper novas chamadas, desativar `WEB_GEMINI_ENABLED` na API e parar o
worker. Preservar tabelas, decisões e a versão da API que entende a projeção.
Não apagar dados nem voltar a uma leitura que ignore decisões humanas já adotadas.

## 9. O que muda no Raspberry

O protocolo existente de captura/resultado continua válido. Não colocar chave
Gemini no equipamento nem enviar uma segunda análise diretamente ao dashboard.
A segmentação e calibração locais continuam sendo um trabalho específico dessa
cópia; Gemini não torna uma calibração ausente válida.

Para exibir a segunda opinião na janela local, o executor usa a consulta da seção
9.1. As rotas de listagem da conta usam cookie de usuário e não devem ser chamadas
com Bearer do Pi. Consulte também `Capturas_Nos_Graficos.md` para o prompt de
processamento local.

### 9.1 Consulta do equipamento

`GET /api/device/samples/{sample_id}/evaluations`

| Header | Valor |
| --- | --- |
| `Authorization` | `Bearer` + credencial do equipamento |
| `X-Inspection-Lease` | Lease da sessão de origem da captura |

`sample_id` é o `id` devolvido pelo envio da captura. A lease aceita é a da sessão
em `source_inspection_id` ou `review_authorization_id`: em uma foto de revisão,
pode ser a lease original ou a da revisão.

A consulta roda em transação `READ ONLY`: não agenda Gemini, não consome a fila,
não renova a sessão e não altera resultados. Exige a migration 008 e
`WEB_INSPECTIONS_ENABLED=true`, sem grants novos além dos listados na seção 3.

**Janela de acesso:** vale durante a sessão e até **1 hora** depois do que ocorrer
primeiro, encerramento (`closed_at`) ou expiração (`authorization_expires_at`). O
valor é a constante `DEVICE_EVALUATION_ACCESS_WINDOW`. `access_expires_at` informa
o limite atual, que antecipa se a sessão for encerrada. Depois do prazo, o
resultado continua no site.

Resposta 200 (valores sintéticos):

```json
{
  "sample_id": "00000000-0000-4000-8000-000000000001",
  "inspection_id": "00000000-0000-4000-8000-000000000002",
  "state": "completed",
  "captured_at": "2026-11-06T12:00:00Z",
  "evaluations": [
    {
      "id": "00000000-0000-4000-8000-000000000003",
      "origin": "gemini",
      "state": "completed",
      "classification": "ATENCAO",
      "reason": "Justificativa sintética.",
      "criteria_version": "orange-surface-v1",
      "model_version": "gemini-3.8-flash",
      "created_at": "2026-11-06T12:00:20Z"
    }
  ],
  "gemini_job": {
    "id": "00000000-0000-4000-8000-000000000004",
    "state": "completed",
    "attempts": 1,
    "error_code": null,
    "updated_at": "2026-11-06T12:00:20Z"
  },
  "decision": null,
  "comparison": "pending",
  "access_expires_at": "2026-11-06T21:00:00Z",
  "observed_at": "2026-11-06T12:00:30Z"
}
```

- `evaluations`: a avaliação mais recente de cada origem (`local`, `gemini`), sem
  métricas. Pode vir vazia.
- `gemini_job: null`: não há avaliação agendada (Gemini desligado, fila no limite
  ou migration ativada depois da captura). A consulta não cria o job; não insista.
- `gemini_job.state`: `queued`, `running` e `retry_wait` estão em andamento;
  `completed` e `failed` são finais. `error_code: daily_limit` significa adiado
  para o próximo dia UTC, o que pode passar do prazo de consulta.
- `comparison`: `pending`, `agreement`, `divergence` ou `inconclusive`. Compara
  categorias e não valida acurácia.
- `decision`: decisão vigente do operador no site, ou `null`. A sugestão Gemini
  não é decisão.

| Status | Significado | Ação no Pi |
| --- | --- | --- |
| 401 | Credencial ausente, inválida ou revogada | Parar e revisar a configuração |
| 403 | Vínculo da conta com o equipamento removido | Parar para esta captura |
| 404 | Amostra inexistente, de outro equipamento, sem sessão de origem ou lease incorreta (mesma resposta, sem revelar qual) | Parar para esta captura |
| 410 | Prazo de consulta encerrado | Parar e indicar o site |
| 422 | Header ausente ou fora do limite (32–128), ou UUID inválido | Corrigir a chamada |
| 503 | Banco indisponível, migration 008 ausente ou inspeções desativadas | Tentar de novo com backoff |

Erros seguem `{"detail": ...}`. Consultar no máximo a cada 15 segundos e parar
quando o job for final, ou nulo, ou ao chegar em `access_expires_at`.

### 9.2 Prompt para o agente do Raspberry

Usar **somente depois de publicar a Web API**. Antes disso, a rota responde 404
no ambiente publicado.

```text
Adicione ao executor em backend/device a exibição da avaliação Gemini na janela
local, consultando a rota já publicada na Web API. Contrato completo:
Docs/Avaliacoes_Local_Gemini.md, seção 9.1, e contracts/web-openapi.yaml.

Requisição:
GET /api/device/samples/{sample_id}/evaluations
Authorization: Bearer <credencial do equipamento>
X-Inspection-Lease: <lease da sessão de origem>

Regras:
1. Use como sample_id o `id` devolvido por upload_camera_sample ou
   upload_camera_review. Use a lease enviada no upload (grant['lease_token'] ou
   review['lease_token']), a da sessão da captura, e não a da sessão atual: o
   operador pode ter mudado. Nunca use X-Sample-Lease nesta rota.
2. Adicione o método em DeviceApi (backend/device/api.py). Consulte fora da
   thread da câmera; a consulta não pode atrasar nem bloquear captura,
   processamento ou sincronização.
3. Consulte no máximo a cada 15 s. Pare em gemini_job.state completed ou failed,
   em gemini_job null, ao atingir access_expires_at, ou com 401, 403, 404 ou 410.
   Em 503 ou falta de rede, tente de novo com backoff até o prazo; respeite
   Retry-After se vier.
4. Exiba categoria, justificativa e modelo da avaliação com origin "gemini", com
   o rótulo de sugestão experimental, separada da avaliação local. Se
   `decision` existir, identifique-a como a decisão do operador.
5. Não altere a classificação local, os LEDs, o servo, o SQLite/outbox nem o
   conteúdo enviado por causa do Gemini. Não adote sugestões a partir do Pi.
6. Compare horários com observed_at e access_expires_at da resposta, não com o
   relógio local.
7. Não coloque chave Gemini no Pi, não chame o Gemini diretamente e não registre
   credencial nem lease em logs. Não use as rotas /api/samples da conta.
8. Trate gemini_job null como "sem avaliação Gemini" e 410 como "consulte o
   site"; nenhum dos dois é erro da captura.

Teste com API fake: em andamento, concluído, job nulo, falha, 404, 410, 503 e
sem rede, confirmando que o resultado local não muda em nenhum caso. Informe o
que foi validado em bancada e o que foi validado apenas com a API fake.
```

## 10. Validação local e contratos

```bash
python -m pytest web_api/tests -q
python -m web_api.tests.run_sample_publication_postgres
python -m web_api.tests.run_dual_evaluations_postgres
RENDER_API_ORIGIN=https://orangevision-rs9g.onrender.com corepack yarn --cwd Frontend build
RENDER_API_ORIGIN=https://orangevision-rs9g.onrender.com corepack yarn --cwd Frontend playwright test --workers=4
```

Os runners PostgreSQL criam banco sintético em container próprio e removem o
container. O provedor é simulado nos testes; nenhuma foto real nem chave é usada.
O contrato versionado está em `contracts/web-openapi.yaml`. Endpoints novos:

- `POST /api/samples/{id}/evaluations/gemini`: 202, comando estável por `request_id`;
  409 se outra avaliação já estiver ativa, 429 no limite da fila, 503 sem ativação.
- `POST /api/samples/{id}/decisions`: decisão idempotente, com `expected_revision`;
  409 em decisão obsoleta ou origem incompatível.

Ambos exigem conta autorizada, Origin e CSRF. Campos antigos de amostras continuam
representando o fluxo local; `evaluations`, `gemini_job`, `comparison` e `decision`
complementam a resposta sem substituir o resultado do Raspberry.

`GET /api/device/samples/{id}/evaluations` é a consulta somente leitura do
equipamento, sem cookie nem CSRF; veja a seção 9.1.
