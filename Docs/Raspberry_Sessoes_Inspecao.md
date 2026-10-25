# OrangeVision — sessões por usuário e preparação do Raspberry

## 1. Objetivo e estado da entrega

Um Raspberry pode ser compartilhado, mas cada inspeção pertence à conta que a iniciou.
O equipamento não recebe senha/cookie de usuário e não identifica o operador pelo login
que existir na hora de sincronizar. A API associa **usuário + dispositivo + sessão**;
o Pi congela o identificador dessa sessão ao aceitar a captura.

| Parte          | Implementação                                                                                      | Validação/pendência                                                                                       |
| -------------- | -------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------- |
| API online     | Pareamento, credencial própria, sessão, encerramento e ingestão                                    | SQL/HTTP validado em namespaces transitórios com rollback; carga/concorrência em banco dedicado pendentes |
| Frontend       | Página `/dashboard/inspecoes`, equipamentos autorizados, código temporário e estado real da sessão | Testes de navegador; não há botão de câmera remota                                                        |
| Pipeline local | Câmera USB/CSI configurável, OpenCV, SQLite/outbox e sincronizador HTTPS                           | SQLite, falhas, exclusão e imagens sintéticas testados no computador; bancada real pendente               |
| Banco          | `002_inspection_sessions.sql` preparada                                                            | **Não aplicada aos schemas reais; ensaio transitório revertido**                                          |
| Hardware       | Adaptadores implementados, sem GPIO obrigatório                                                    | Modelo do Pi, sistema, câmera, iluminação e resolução ainda precisam ser confirmados                      |
| Calibração     | Motor experimental configurável                                                                    | Exemplo propositalmente inválido; faltam medições/fotos rotuladas reais                                   |

O recurso é **opcional e desligado por padrão**. Login, site e consultas existentes não
dependem de câmera, LEDs, buzzer, servo ou sensor. Não foi executado deploy no Render.

## 2. Onde fica cada responsabilidade

```text
Frontend/src/features/inspection/  # UI, schemas de resposta e hooks; sem segredo do Pi
web_api/                          # sessão, autorização, credencial e persistência remota
backend/device/                   # executor local; sem FastAPI/contas/Neon/GPIO obrigatório
backend/app/                      # legado preservado; não usar seu sincronizador no novo fluxo
```

```text
Conta autenticada → iniciar inspeção → código temporário para aquele equipamento
                                             ↓
Pi com credencial própria → confirmar código → autorização local com prazo
                                             ↓
capturar → segmentar → medir/classificar → transação SQLite: análise + outbox
                                             ↓
sincronizador HTTPS → API valida dispositivo/sessão/conteúdo → commit → ACK
                                             ↓
dashboard/histórico/comparação do proprietário da sessão
```

Iniciar uma inspeção no site NÃO envia um comando público para abrir a câmera do Pi.
O acionamento físico continua na bancada. Não é necessário criar servidor HTTP local
para o modo mínimo: o executor fornecido usa comandos locais/interativos.

`backend/app` é legado preservado: não publicar esse módulo no Render nem usá-lo como API
do site. Suas consultas diretas não implementam o novo isolamento por sessão de inspeção.

## 3. Política de dados e histórico antigo

- `device_access` autoriza iniciar uma inspeção no equipamento; o dono do resultado é
  `inspection_sessions.user_id`, não qualquer pessoa que tenha acesso ao mesmo aparelho.
- Com `WEB_INSPECTIONS_ENABLED=true`, todas as leituras pessoais (histórico, detalhe,
  resumo, distribuição, série e comparação) exigem propriedade da sessão da análise.
- Análises antigas ficam com `inspection_session_id=NULL`. Não são apagadas, copiadas
  nem atribuídas automaticamente à pessoa atualmente logada.
- Antes de ativar, definir o tratamento administrativo desse histórico. No modo pessoal
  por inspeção, registros antigos sem sessão ficam fora desses indicadores.
- Com o recurso desligado, mantém-se a consulta legada por equipamento **somente para
  registros sem sessão**. Desligar o recurso não pode tornar registros pessoais de
  inspeção compartilhados novamente.
- Depois de capturado, o vínculo não muda ao trocar operador, sair do site ou sincronizar.
- O proprietário continua podendo consultar seu histórico de inspeção mesmo quando não
  recebe mais autorização para iniciar novas capturas naquele equipamento.

## 4. Preparação da API online — na raiz OrangeVision

### 4.1 Revisar e aplicar o banco em etapa explícita

A migration 002 adiciona `device_credentials`, `inspection_sessions`, `ingestion_receipts`
e campos opcionais de sessão/calibração/justificativa em `public.analises`. Não altera
unidades silenciosamente nem executa backfill de proprietário.

Primeiro, em PostgreSQL **isolado de integração**, com o schema legado compatível e a
migration 001 já aplicada, testar a 002 e os cenários da seção 10. O Docker estava
instalado, mas o daemon não estava disponível durante esta entrega. Como verificação
adicional, foi usado `web_api.verify_inspection_sql`: ele copia apenas a estrutura das
duas tabelas legadas para namespaces de teste separados, redireciona o SQL da API para
eles e reverte todas as contas, resultados e DDL por rollback obrigatório. Isso validou
o fluxo SQL/HTTP de dois operadores sem aplicar a 002 nos schemas reais.

Esse ensaio usa uma transação de fixtures compartilhada e não mede locks entre conexões
independentes, carga ou disponibilidade durante deploy. Antes da ativação definitiva,
continuam necessárias as verificações em banco dedicado e a revisão do histórico.

```powershell
# Mostra somente o plano, sem executar SQL:
python -m web_api.migrate --migration 002
# Somente depois de revisar, confirmar o ambiente e autorizar a aplicação:
python -m web_api.migrate --migration 002 --apply
```

DDL é aditiva e transacional, com limites de espera/execução. Não executar durante uma
captura nem ativar o recurso antes de confirmar a estrutura. Não remover campos/tabelas
para fazer rollback: para interromper a operação, desativar a flag e preservar os dados.

### 4.2 Provisionar o equipamento e o usuário autorizado

Usar `web_api.provision_device`, ferramenta administrativa local — não existe cadastro
público de hardware. Sem `--apply` ela apenas mostra o plano. É possível provisionar
com o recurso ainda desligado, desde que a migration 002 já esteja aplicada.

```powershell
python -m web_api.provision_device
```

Na execução aprovada, informar `--name`, `--user` com o UUID real da conta e `--apply`.
O UUID da própria conta está no campo `user.id` da resposta autenticada de `/api/auth/session`.
O comando emite `DEVICE_ID`, `CREDENTIAL_ID` e o segredo `DEVICE_INGEST_CREDENTIAL` uma
única vez, após commit. Guardar o segredo somente no ambiente privado do equipamento.

Para liberar outra pessoa no mesmo equipamento, usar os UUIDs reais com
`--device`, `--user`, `--grant-only`, `--apply`. Isso cria apenas o vínculo explícito,
sem outra credencial. `--revoke` com o ID de uma credencial e `--apply` a revoga.
Não executar comandos com textos de exemplo no lugar de UUIDs reais.

### 4.3 Ativar somente depois da revisão do histórico e provisionamento

No ambiente da API/Render, nunca no frontend:

```dotenv
WEB_INSPECTIONS_ENABLED=true
WEB_INSPECTION_LEASE_SECONDS=28800
```

A autorização local é de oito horas nesse exemplo; o servidor aceita configuração de
15 minutos a 24 horas. O código de pareamento expira em cinco minutos. Reiniciar a API
depois de alterar o ambiente. O frontend descobre a disponibilidade pelo endpoint de
configuração e só então mostra o item **Inspeções**.

## 5. Contratos implementados

| Método/rota                               | Quem chama                            | Finalidade                                                            |
| ----------------------------------------- | ------------------------------------- | --------------------------------------------------------------------- |
| GET `/api/inspections/config`             | Sessão web                            | Disponibilidade opcional e política de leitura                        |
| GET `/api/inspections/devices`            | Sessão web                            | Equipamentos autorizados para a conta                                 |
| GET `/api/inspections/current`            | Sessão web                            | Sessões abertas da própria pessoa                                     |
| POST `/api/inspections`                   | Sessão web + CSRF + origem            | Início idempotente por request_id, com código gerado no cliente       |
| POST `/api/inspections/:id/close`         | Proprietário + CSRF + origem          | Cancelar pendente ou solicitar encerramento local                     |
| POST `/api/device/inspections/pair`       | Credencial do equipamento             | Ativar código do equipamento com activation_id e lease_token estáveis |
| GET `/api/device/inspections/:id`         | Equipamento + autorização de inspeção | Estado observado da autorização, não da câmera                        |
| POST `/api/device/inspections/:id/closed` | Equipamento + autorização             | Confirmar encerramento após captura em andamento                      |
| POST `/api/ingest/analyses`               | Equipamento + autorização             | Enviar lote e receber ACKs depois do commit                           |

POSTs do site exigem `Origin` permitido e `X-CSRF-Token`. O dispositivo usa
`Authorization: Bearer` e `X-Inspection-Lease`, sem autenticar por cookie de usuário.
Uma credencial de equipamento não autentica rotas de conta e não autoriza outro dispositivo.

Uma sessão aberta por equipamento é garantida por índice único e lock de linha na criação.
Pareamento repetido com o MESMO activation_id e lease_token consulta a ativação anterior;
outro conteúdo não troca o operador. O Pi persiste a tentativa antes da chamada HTTP.

Ingestão v1: até 50 IDs únicos, uma sessão por lote, máximo real de 256 KiB antes do parse.
O cliente envia lotes menores, limitados também por bytes. Métricas são razões 0–1,
score 0–100 e circularidade não negativa; o adaptador converte razões para os percentuais
legados do banco. `algorithm_version` tem até 50 caracteres, conforme o schema existente;
calibração tem até 100 e justificativa até 1000. Campos `user_id`, `device_id`, imagens
arbitrárias e extras não são aceitos no item.

Mesmo UUID/conteúdo/sessão retorna `duplicate`; UUID com conteúdo ou dono diferente retorna
`conflict`, sem overwrite. Erros de validação do JSON rejeitam o lote inteiro; erros de
integridade por item são isolados por savepoint e aparecem como `rejected`. ACKs só saem
depois do commit remoto. Não há garantia falsa de exactly-once no transporte.

## 6. O que configurar no Raspberry

Confirmar ANTES: modelo do Pi, RAM, Raspberry Pi OS/arquitetura, câmera **USB ou CSI**,
driver, permissões de câmera e ambiente Python. O pipeline suporta Python 3.11+; a API
online continua com seu ambiente separado. Não instalar PostgreSQL/Argon2/contas web no Pi.

No Pi, terminal na pasta `OrangeVision/backend`:

```bash
python3 -m venv .venv-device
source .venv-device/bin/activate
python -m pip install -r device/requirements.txt
```

Copiar `device/.env.example` para `device/.env` e preencher os valores reais emitidos
pelo provisionamento: `DEVICE_ID`, `WEB_API_BASE_URL`, `DEVICE_INGEST_CREDENTIAL`.
Os campos do exemplo ficam vazios de propósito; não são valores operacionais.

- API de rede exige HTTPS. HTTP só é aceito para localhost/127.0.0.1 e com
  `ALLOW_INSECURE_LOCAL_API=true`, exclusivamente para testes no mesmo computador.
  `127.0.0.1` no Pi aponta para o próprio Pi, não para seu notebook ou Render.
- SQLite padrão: `backend/device/data/device_pipeline.db`. Caminhos relativos de
  SQLite/calibração são resolvidos a partir de `backend/device`, independentemente do cwd.
- O novo pipeline recusa apontar para o SQLite legado que contém a tabela `analises`.
  Não apaga nem migra esse arquivo automaticamente.
- Configurar `CAMERA_ADAPTER=usb` ou `csi`, índice USB, resolução medida e `CALIBRATION_PATH`.
  Resolução zero/exemplo sem calibração bloqueia captura; não existe câmera fictícia.
- USB usa OpenCV. Instalar `device/requirements-vision.txt` somente após confirmar wheels
  e arquitetura compatíveis. CSI usa Picamera2/libcamera e exige pacotes do SO e venv
  compatível com essas bibliotecas; não presumir que um pip genérico resolve todo modelo.
- O adaptador CSI solicita RGB888/libcamera e usa arrays BGR para OpenCV; confirmar canais
  com carta de cor na bancada. Resolução, aquecimento da câmera, exposição e iluminação
  precisam de avaliação real; não há resolução/FPS ideal inventado.
- Ajustar UTC/NTP. Relógio incompatível com o início da autorização bloqueia captura;
  a API tolera apenas pequena diferença de relógio nos limites (30 segundos), sem mudar dono.
  A expiração de pareamento/inspeção e a validação de captura usam a observação do banco
  (`observed_at`), evitando misturar o relógio do host da API com o do PostgreSQL. O Pi
  verifica a diferença ao receber uma autorização/estado fresco; cached/offline não é
  corrigido artificialmente. Na validação foi identificada divergência de cerca de cinco
  minutos no computador de desenvolvimento. Nenhum relógio do sistema foi alterado.

## 7. Calibração e processamento

`device/calibration.example.json` é **propositalmente inválido**: validated=false,
faixas vazias e pesos/limiares nulos. Não basta mudar a flag para true. É necessário
obter amostras reais e definir/documentar:

1. Versão da calibração e condições da bancada.
2. Faixas HSV da fruta, cor-alvo e regiões anormais.
3. Área mínima da região segmentada.
4. Intervalos, direção e pesos das quatro métricas para o score experimental.
5. Limiares de APROVADA, ATENCAO e REVISAR, com avaliação rotulada e limitações.

O algoritmo usa o maior contorno válido e mede somente dentro da máscara da fruta.
Cor/regiões anormais são proporções de pixels; circularidade usa 4πA/P²; assimetria é a
diferença da silhueta com o espelho horizontal, normalizada por duas vezes a área em pixels.
O score é uma combinação configurada de valores normalizados, não probabilidade/acurácia.
Falha de aquisição/segmentação NÃO gera REVISAR: o job falha sem análise classificada.

Imagens não são persistidas/uploadadas por este incremento. O pipeline trabalha com o
frame em memória e grava métricas/rastreabilidade. Armazenamento de imagem privada,
retenção e reconciliação de arquivos continuam incremento separado; URLs/caminhos locais
não são expostos ao site. LEDs, servo, sensor e buzzer continuam opcionais, sem import GPIO.

## 8. Operação local e troca de pessoa

1. No site, a pessoa inicia a inspeção e obtém o código temporário.
2. Na bancada, no ambiente/pasta do Pi:

```bash
python -m device pair
python -m device run
```

O primeiro comando pede o código sem exibi-lo no terminal. `run` oferece parear, capturar,
encerrar sessão e sair. Mostra o operador; captura é serial e recebe request_id estável.
O lock de processo dura enquanto o executor controla a câmera; outra instância do mesmo
pipeline é recusada. SQLite também impede dois jobs em processamento simultaneamente.

Ao solicitar encerramento no site, o estado vira `closing`, não sucesso físico imediato.
O executor confirma quando está livre; uma captura aceita antes disso mantém sua sessão
original até persistir. Iniciar outra pessoa exige encerrar/expirar a anterior.
Sair do site ou do executor não reatribui nem apaga registros pendentes.

Uma captura avulsa também pode usar `python -m device capture`. O comando imprime o UUID
da solicitação antes de capturar e só confirma resultado depois do commit SQLite. Após
timeout/interrupção, consultar com `python -m device job --request-id` seguido do UUID real.
Reusar um comando concluído não captura de novo. Jobs interrompidos não são repetidos
automaticamente; a decisão de refazer a atuação física é do operador.

Se o pareamento perdeu a resposta, repetir o MESMO código recupera a ativação estável.
Para desistir, `python -m device cancel-pairing` reconcilia a tentativa com a API antes
de descartá-la localmente; não apagar o banco/segredo para contornar uma sessão ocupada.

## 9. Offline, outbox e sincronização

Em outro terminal com o mesmo ambiente e pasta:

```bash
python -m device sync --loop
python -m device status
```

- Continua offline somente uma autorização já salva e ainda válida. Iniciar/trocar pessoa
  exige internet. Autorização expirada ou recusa 401/403 não vira sucesso offline fictício.
- A sessão, UUID, timestamp, métricas e calibração ficam congelados no registro antes de
  sincronizar. Um lote antigo da pessoa A usa a autorização de A, mesmo com B ativa agora.
- Análise, outbox e conclusão do job são gravados em uma transação SQLite; WAL e FULL
  preservam durabilidade. Falha de disco/outbox não retorna análise concluída.
- Reenvio usa o mesmo conteúdo/UUID, timeout, backoff com jitter e Retry-After. Só accepted
  ou duplicate viram synced. Falta de ACK continua pendente; conflito/rejeição fica em
  quarentena, sem apagar o payload. Corpo inválido pode exigir reprocessamento administrativo
  dos itens válidos retidos; não alterar o dono/conteúdo sob o mesmo UUID para forçar aceitação.
- O sincronizador é separado da câmera. Monitorar pendências/quarentena, idade, logs e
  espaço em disco. Retenção e reenvio de quarentena precisam de decisão explícita.
- Não executar o sincronizador legado `backend/app/sync.py` para o mesmo fluxo: ele escreve
  diretamente no Neon e não implementa este protocolo de sessão/ACK. No novo fluxo, o Pi
  não recebe DATABASE_URL e não envia o arquivo SQLite inteiro.

## 10. O que ainda precisa ser feito / aceite de bancada

- [ ] Confirmar modelo/OS/arquitetura do Raspberry e câmera USB/CSI.
- [ ] Validar a migration 002 em PostgreSQL isolado, inclusive os locks/índices e dois usuários
      concorrentes no mesmo equipamento; depois revisar/autorizá-la para o ambiente definitivo.
- [ ] Decidir o tratamento do histórico antigo sem sessão antes de ativar o modo pessoal.
- [ ] Publicar/configurar a API HTTPS (Render), domínio/proxy do frontend, secrets e origem.
- [ ] Provisionar equipamento/credencial e vínculos explícitos com as contas corretas.
- [ ] Configurar permissões de câmera, UTC/NTP e acesso restrito aos arquivos locais.
- [ ] Medir iluminação/resolução/memória e obter fotos rotuladas para calibração real.
- [ ] Validar segmentação/métricas/limiares e registrar versões e limitações.
- [ ] Rodar captura só com câmera, sem GPIO, e medir RAM/CPU/latências reais.
- [ ] Parear A → capturar → encerrar → parear B → capturar; dashboard A não vê dados de B,
      mesmo que ambos tenham acesso ao mesmo dispositivo.
- [ ] Simular rede fora, reinício no meio da captura, disco cheio e perda de ACK.
- [ ] Confirmar UUID remoto único no reenvio e conflito quando mesmo ID tem outro conteúdo.
- [ ] Validar encerramento durante captura, expiração, credencial revogada e backlog de A
      enviado depois de B entrar. Nenhuma troca automática de proprietário.
- [ ] Validar o lock Linux na bancada e impedir serviços externos de disputar a mesma câmera.
- [ ] Só então configurar supervisão/autostart e retenção/backup compatível com WAL.

Testes do pipeline: `python -m pytest device/tests -q` na pasta backend, após instalar
`device/requirements-dev.txt` em ambiente separado. Testes usam câmera fake e imagens
sintéticas identificadas; não comprovam classificação/calibração em laranjas reais.

## 11. Verificações executadas nesta entrega

- 67 testes Python da API passaram (contratos, CSRF, papéis separados, limites de lote,
  idempotência, expiração, janelas de captura e filtro de propriedade).
- 23 testes do pipeline local passaram em ambiente separado (SQLite real em diretório
  temporário, atomicidade/outbox, falhas, dois workers, lock Windows, resposta perdida,
  dono congelado, retomada offline, ACK e imagens sintéticas OpenCV).
- 51 testes Playwright passaram no build de produção, incluindo recurso desligado,
  pareamento, início sem resposta com retry idempotente, encerramento aguardando o Pi,
  ausência de equipamento, responsividade e acessibilidade.
- Build, TypeScript, ESLint, Prettier e Ruff foram aprovados. OpenAPI foi regenerado.
- O ensaio SQL/HTTP transitório passou: DDL 001/002 nas estruturas isoladas, dois operadores
  autorizados ao mesmo equipamento, início/pareamento idempotentes, deduplicação/conflito,
  envio antigo com dono original, comparação pessoal e desativação sem vazamento. A remoção
  dos namespaces e dados transitórios foi confirmada após rollback.
- Não foram executados captura física, provisionamento de segredo real, deploy ou aplicação
  da migration 002 nos schemas reais. Integração de concorrência/carga em banco dedicado e
  bancada continuam pendentes; os testes de navegador usam respostas controladas só nos testes.
