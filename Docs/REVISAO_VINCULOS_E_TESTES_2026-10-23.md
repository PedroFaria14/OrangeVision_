# OrangeVision — revisão de vínculos e testes

Data: 23/10/2026. Revisão sem migrations, provisionamento ou alteração do banco remoto.

> Atualização: as seções iniciais são o registro da revisão original. A rodada de ajustes e seus resultados estão ao final; o número de testes e a verificação do schema foram ampliados.

## Parecer

Concordo com o desenho para bancada compartilhada. Usuário autorizado inicia uma sessão; Pi confirma o código com credencial própria; captura congela a sessão; resultado e outbox são persistidos juntos; upload posterior mantém proprietário original. Login atual do navegador não determina o dono da análise.

## Testes concluídos nesta rodada

- backend/device/tests: 26 aprovados, com SQLite de teste, adaptadores simulados e imagens sintéticas. Cobrem captura idempotente, sessão congelada, offline, rollback de outbox, reinício, exclusão da câmera, pareamento com resposta perdida, encerramento e relógio.
- web_api/tests/test_inspections.py: 8 aprovados e 5 não executados no comando selecionado. Cobrem propriedade, separação do legado, expiração, credencial, pareamento repetido, upload tardio e recibos duplicados.
- Total: 34 testes aprovados. Não comprovam câmera física nem concorrência PostgreSQL real.

Primeira tentativa falhou por acesso negado à pasta temporária padrão. Reexecução em diretório gravável do projeto passou integralmente. Usado backend/.venv-device; o ambiente .venv-device da raiz não tem pytest. Nenhuma instalação foi feita.

## Pontos corretos encontrados

1. device_access autoriza usar equipamento; inspection_sessions.user_id define dono das análises.
2. API usa usuário da sessão autenticada, sem aceitar dono arbitrário enviado pelo frontend.
3. Pi não recebe senha/cookie de usuário; credencial do equipamento é separada.
4. Worker congela sessão e UUID antes da captura; adaptador de visão não pode sobrescrever o vínculo.
5. Resultado e outbox ficam na mesma transação SQLite.
6. Reenvio só é duplicata se ID, conteúdo e sessão coincidirem; não sobrescreve dados conflitantes.
7. Consultas pessoais filtram proprietário. Desligar o modo de inspeções não expõe registros pessoais pelo modo legado.
8. Uma sessão aberta por equipamento é protegida por lock e índice único no código/migration proposta.

## Ressalvas antes da homologação

- Offline: autorização local válida permite continuar sem rede; encerramento remoto não chega instantaneamente. Definir prazo adequado e comunicar essa limitação. Ao observar negativa/closing, o Pi bloqueia novas capturas.
- Relógio: NTP/UTC é parte do contrato. Horário de captura vem do dispositivo confiável; não é prova inviolável contra administrador do próprio Pi.
- Código temporário: frontend guarda código/tentativa em memória; refresh perde sua apresentação. Orientar cancelamento/expiração e novo início sem reatribuição silenciosa.
- Banco: não verifiquei aplicação efetiva da migration 002. Testar concorrência de dois usuários em conexões PostgreSQL independentes, rollback de commit e resposta perdida em ambiente dedicado.
- Legado: histórico sem sessão não pode ser atribuído automaticamente ao operador atual. Explicar quais registros aparecem em cada modo.
- Hardware: câmera, iluminação, calibração e qualidade de classificação continuam pendentes de validação física.

## Próximo ensaio completo

Usuário A inicia e pareia; captura; perde internet; troca operador respeitando encerramento/autorização; usuário B inicia outra sessão; análise pendente de A é enviada depois. Confirmar que só A consulta o resultado e que reenvio do mesmo UUID não duplica. Repetir após reinício do Pi e encerramento remoto durante desconexão.

Desenho aprovado para continuar desenvolvimento; operação completa ainda depende desse ensaio. Nenhuma mudança de código nesta rodada. Arquivos temporários de teste permanecem em test-results-device-review; a tentativa de limpeza foi bloqueada pela revisão automática de permissões e não foi forçada.

## Ajustes após a revisão

### Recuperação e diagnóstico do executor

- Adicionado `pair --resume`: usa exclusivamente a tentativa persistida no SQLite, com o mesmo código, activation_id e lease_token; não precisa recuperar o código no navegador e não cria uma nova identidade de ativação.
- Recuperação sem tentativa salva é recusada com orientação. Um código diferente não substitui silenciosamente a tentativa anterior. Sessão em encerramento orienta `cancel-pairing`; sessão local ativa continua exigindo encerramento antes da troca.
- `status` agora informa `pairing_pending`, `state` e `authorization_expires_at`, sem imprimir código, lease ou credencial.
- Erros HTTP e de conexão recebem mensagens controladas. Corpo remoto, credenciais e códigos não são reproduzidos no terminal. Erros internos desconhecidos continuam genéricos.
- Tolerância UTC/NTP centralizada em **30 segundos** para ambas as verificações. Não houve aumento silencioso para 10 minutos nem desativação da verificação de expiração.

### Comunicação de operação offline e legado

- A página de inspeções explica recuperação após refresh/resposta perdida e avisa que encerramento remoto não é instantâneo durante desconexão.
- O histórico explica o modo confirmado pela API: dono da sessão no modo pessoal; somente registros sem sessão e equipamentos autorizados no modo legado.
- Consulta somente leitura ao ambiente configurado confirmou as tabelas `inspection_sessions`, `device_credentials`, `ingestion_receipts` e o índice único parcial `inspection_one_open_per_device`. Isso confirma a presença de estruturas essenciais da migration 002, não é auditoria completa de todo o schema nem nova aplicação de migration.
- Na configuração consultada, inspeções estão habilitadas e `WEB_INSPECTION_LEASE_SECONDS=28800` (**8 horas**). É o limite configurado de autorização, não garantia de atualização remota imediata. Uma sessão já emitida conserva seu vencimento. Alterar o parâmetro afeta novas autorizações; a duração apropriada para a bancada deve ser aprovada pelo responsável antes da homologação.

### Testes e evidências

- Executor: **34 testes aprovados**. Novos casos verificam recuperação após reinício, tentativa incompatível, recuperação de sessão em encerramento, diagnóstico sem exposição de segredos e envio tardio de A após mudança para B/reabertura do SQLite.
- O envio de A/B é feito em lotes separados por sessão, usando a autorização original de cada uma. O teste usa API/câmera/visão simuladas: não é apresentado como comprovação de PostgreSQL nem de hardware.
- Os **13 testes de `web_api/tests/test_inspections.py`** foram executados integralmente, incluindo os cinco fora da seleção original.
- Suíte completa da API: **67 testes aprovados**; **3 testes PostgreSQL opt-in não executados** sem banco dedicado.
- Novos testes de integração em `web_api/tests/test_postgres_concurrency.py`: dois usuários concorrentes em conexões independentes; rollback após falha antes do commit; repetição após descarte da resposta de pareamento. Usam DDL real redirecionado a namespaces descartáveis e exigem explicitamente um banco com nome terminado em `_test`. Nunca carregam automaticamente a conexão do `.env` da API.
- Não foi possível executar os três ensaios PostgreSQL: o daemon Docker local não estava disponível e não foi fornecida conexão de teste dedicada. A suíte os marca como **skipped**, não aprovados. Não se utilizou o Neon de operação para substituí-los.
- O warning de depreciação Starlette/httpx já existente não impediu a execução dos testes da API.
- Frontend: build/TypeScript, ESLint e **58 testes Playwright aprovados** após as orientações de recuperação/offline e explicação dos modos do histórico. Ruff e formatação dos arquivos Python modificados aprovados.

### Comandos reproduzíveis

Na raiz `OrangeVision`:

```powershell
.\backend\.venv-device\Scripts\python.exe -m backend.device status
.\backend\.venv-device\Scripts\python.exe -m backend.device pair --resume
.\backend\.venv-device\Scripts\python.exe -m pytest backend/device/tests -q
.\web_api\.venv-web\Scripts\python.exe -m pytest web_api/tests -q
```

`pair --resume` faz uma chamada real de recuperação e só deve ser usado no equipamento cuja tentativa será recuperada. `status` é consulta local e não atesta disponibilidade da câmera nem da API.

Para ensaiar PostgreSQL, primeiro inicie o Docker Desktop. Exemplo **somente para banco local descartável**, sem dados reais:

```powershell
docker run --rm --name orangevision-review-postgres -e POSTGRES_DB=orangevision_test -e POSTGRES_PASSWORD=orangevision-test-only -p 127.0.0.1:55432:5432 -d postgres:16
docker exec orangevision-review-postgres pg_isready -U postgres -d orangevision_test
```

Aguarde `accepting connections` e execute:

```powershell
$env:ORANGEVISION_TEST_DATABASE_URL = 'postgresql://postgres:orangevision-test-only@127.0.0.1:55432/orangevision_test'
try {
    .\web_api\.venv-web\Scripts\python.exe -m pytest web_api/tests/test_postgres_concurrency.py -q
} finally {
    Remove-Item Env:ORANGEVISION_TEST_DATABASE_URL
    docker stop orangevision-review-postgres
}
```

A senha do exemplo é exclusiva do container de teste descartável. Não apontar esse ensaio para o banco de operação.

### Pendências de homologação

1. Executar e revisar os três testes PostgreSQL em banco dedicado; a falha antes do commit é injetada e não simula queda física do servidor no instante de commit.
2. Realizar o ensaio A → offline → encerramento/troca → B → envio tardio de A com API/PostgreSQL e equipamentos reais; testar consulta autorizada das duas contas e resposta perdida de ingestão.
3. Aprovar o prazo offline adequado; verificar encerramento remoto durante desconexão e comportamento após vencimento/reinício.
4. Validar câmera, iluminação, segmentação e classificação com referências rotuladas. Testes sintéticos não constituem evidência de qualidade da fruta.
