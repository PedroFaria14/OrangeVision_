# Cadastro de equipamentos pela conta do site

## Uso

Entre pelo login normal e abra **Equipamentos** (`/dashboard/dispositivos`).
Cada conta pode cadastrar vários equipamentos próprios; o limite inicial é cinco.
O cadastro gera um novo UUID e o vínculo com a conta autenticada. Não há campo para
assumir um dispositivo existente pelo UUID. O login administrativo GitHub/Prisma
continua separado.

1. Informe um nome de 2 a 100 caracteres e clique em **Cadastrar equipamento**.
2. Guarde a configuração exibida antes de fechar, atualizar ou sair da página.
3. Preencha `device/.env` no Raspberry com os valores emitidos.
4. Execute o fluxo local de inspeções ou amostras já instalado no equipamento.

A página apresenta os campos com nomes legíveis e as respectivas variáveis
técnicas, além da seção **Como conectar seu Raspberry**. O passo a passo continua
disponível depois de fechar a confirmação ou recarregar a página, sem recuperar o
segredo. A ajuda explica falhas de rede, recuperação por rotação e equipamentos
compartilhados. O assistente inicial no executor é uma implementação separada:
nas versões sem ele, a orientação permanece preencher `device/.env`.
O prompt para essa implementação está em
[Prompt_Configuracao_Raspberry.md](Prompt_Configuracao_Raspberry.md).

O cadastro não abre câmera, não inicia inspeção e não comprova que o executor está
online. Com um equipamento autorizado, inspeções e amostras o pré-selecionam; com
vários, exigem escolha. A escolha vazia explícita continua sendo respeitada.
Sem equipamentos, as duas telas orientam o usuário para **Equipamentos**.

## Ativação no Render, banco e Vercel

Esta entrega prepara código e SQL. A aplicação da migration e a publicação são
etapas operacionais separadas.

Na raiz `OrangeVision/`, com Python 3.11+ e dependências de `web_api/` instaladas:

```bash
# Apenas apresenta o plano; não conecta ao banco:
python -m web_api.migrate --migration 006
# Executar somente no ambiente e banco revisados, após autorização:
python -m web_api.migrate --migration 006 --apply
```

A migration `006_device_registration.sql` depende de `001_web_auth.sql`,
`002_inspection_sessions.sql` e da tabela legada `public.dispositivos`.
Ela cria `orangevision_web.managed_devices` (proprietário e quota) e
`orangevision_web.device_commands` (idempotência). Não faz backfill nem atribui
propriedade aos equipamentos antigos. Usa DDL transacional, timeout de lock de
cinco segundos e timeout de execução de trinta segundos.

O papel de runtime da API precisa de leitura/escrita nas novas tabelas, além dos
acessos existentes a `dispositivos`, `device_access`, `device_credentials` e
`auth_attempts`. Se migrations e API usam papéis distintos, conferir os grants no
ambiente de implantação.

Variáveis no ambiente **da Web API/Render**:

```dotenv
WEB_MAX_DEVICES_PER_USER=5
WEB_DEVICE_API_BASE_URL=https://orangevision-rs9g.onrender.com
```

- `WEB_MAX_DEVICES_PER_USER`: opcional, padrão 5, aceita 1–100. Conta apenas cadastros
  próprios desta funcionalidade, inclusive quando um vínculo de acesso é retirado.
- `WEB_DEVICE_API_BASE_URL`: opcional, somente origem HTTPS, sem `/api`, query ou
  credenciais. Preenche o campo de configuração do Raspberry. Sem esse valor,
  a tela sugere a origem HTTPS do site; também aceita preenchimento manual.
- Preservar `WEB_ALLOWED_ORIGINS`, cookies e demais configurações existentes.
- O cadastro independe de `WEB_INSPECTIONS_ENABLED`; operação de inspeções e amostras
  continua dependendo das respectivas configurações e migrations.

Publicar a Web API no Render e o frontend na Vercel após preparar o banco. Se a
migration 006 ainda não existir, a API nova lista vínculos antigos e informa
`registration_enabled=false`; as emissões respondem 503. Se a API ainda for antiga,
a interface explica o 404 e pede atualização do serviço.

## Configuração do Raspberry

O protocolo e o código de `backend/device/` permanecem compatíveis. O novo cadastro
substitui a emissão administrativa da credencial para equipamentos novos.

Se o Pi recebeu somente a pasta `backend/`, execute os comandos de dentro dessa
pasta. O arquivo continua sendo `device/.env`, por exemplo:

```dotenv
DEVICE_ID=<UUID emitido pelo cadastro>
WEB_API_BASE_URL=https://orangevision-rs9g.onrender.com
DEVICE_INGEST_CREDENTIAL=<segredo exibido uma única vez>
```

Preserve as outras configurações existentes desse arquivo. Não coloque URL do
Neon, cookie da conta ou senha do site no executor. `WEB_API_BASE_URL` não leva
`/api` nem `/docs`. O executor usa `Authorization: Bearer` como antes.

```bash
python -m device pair
python -m device.inspect --camera 0
```

O pareamento usa o código temporário da inspeção iniciada no site, distinto da
credencial permanente. Para instalação e câmera, consulte
[Raspberry_Sessoes_Inspecao.md](Raspberry_Sessoes_Inspecao.md); para amostras,
[IA_Captura_Integrada.md](IA_Captura_Integrada.md).

## Segredo, repetição e rotação

- O segredo é aleatório e só aparece na primeira resposta confirmada. O banco
  guarda SHA-256, nunca o texto original. A API aplica `Cache-Control: no-store`.
- A interface mantém o segredo apenas em estado transitório, fora de cache de
  consultas, URL, localStorage e sessionStorage. Ao sair ou trocar de conta, o
  estado é descartado. A cópia para clipboard é uma ação explícita do usuário.
- Em resposta perdida, **Tentar confirmar operação** reutiliza o mesmo `request_id`.
  O replay retorna metadados sem segredo e não cria outro equipamento.
- Se perdeu a primeira resposta, feche a confirmação e use **Gerar nova credencial**.
  A confirmação revoga todas as anteriores daquele equipamento. O UUID e o
  histórico são preservados; o Pi deve receber a credencial nova em `device/.env`
  e ter seu processo reiniciado para carregá-la.
- Só o proprietário com vínculo de acesso atual pode rotacionar. Equipamentos
  antigos/compartilhados não ganham proprietário automaticamente. O fluxo
  administrativo `web_api.provision_device` continua disponível para seus vínculos.
- O limite de emissão é de dez operações novas por conta em quinze minutos;
  repetições idempotentes não consomem outra emissão. Um bloqueio responde 429
  com `Retry-After: 900`.

## Contrato e implementação

| Método e rota | Autorização | Resultado |
| --- | --- | --- |
| GET `/api/devices` | Sessão normal | Itens autorizados, quota, prontidão e origem sugerida |
| POST `/api/devices` | Sessão + Origin + CSRF | `name`, `request_id`; 201 novo ou 200 replay |
| POST `/api/devices/{device_id}/credentials` | Proprietário + sessão + Origin + CSRF | `request_id`; credencial nova ou replay sem segredo |

As respostas de emissão contêm `device`, `credential` (nula em replay) e `replayed`.
Não recebem `user_id`, proprietário ou UUID de dispositivo arbitrário no cadastro.
Payloads têm limite de 16 KiB e campos extras são rejeitados. Falta de autorização
ao dispositivo retorna 404; quota/conflito, 409; input inválido, 422.
O contrato versionado completo está em `contracts/web-openapi.yaml`.

```text
DevicesPage → useDevices → features/devices/api
  → api/device_routes.py (sessão, Origin, CSRF)
  → application/device_service.py (segredo e fingerprint)
  → infrastructure/device_repository.py (transação, quota, ownership, replay)
  → PostgreSQL
```

O advisory lock por conta serializa quota e comandos concorrentes. A criação do
dispositivo, vínculo, propriedade, credencial e registro do comando é atômica.
A autenticação do executor continua em `InspectionRepository.authenticate_device`.

## Validação local

```bash
python -m pytest web_api/tests -q
# Docker: PostgreSQL 16 descartável, porta loopback aleatória e cleanup automático:
python -m web_api.tests.run_device_postgres
RENDER_API_ORIGIN=https://orangevision-rs9g.onrender.com corepack yarn --cwd Frontend build
RENDER_API_ORIGIN=https://orangevision-rs9g.onrender.com corepack yarn --cwd Frontend playwright test --workers=4
```

O runner PostgreSQL usa apenas o banco sintético `orangevision_devices_test` em
container próprio. Os testes cobrem isolamento, replay, concorrência, quota,
rollback, revogação e compatibilidade Bearer do Pi. Os testes de navegador da nova
feature interceptam as chamadas com fixtures e não cadastram hardware real.
