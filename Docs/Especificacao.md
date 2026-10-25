# OrangeVision — Especificação atualizada do backend

Versão 1.0 — 19/10/2026.

Documento de requisitos para implementação. Não contém código executável e não comprova inspeção do backend, schema, banco ou hardware existentes. Substitui a obrigatoriedade anterior de LEDs, buzzer, servo e sensor. Ler junto às especificações geral e de frontend atualizadas.

## 1. OBJETIVO E ESCOPO

Processar imagens de laranjas no Raspberry Pi, persistir análises com durabilidade local, sincronizar registros para consulta online e fornecer autenticação e dados autorizados ao frontend React.

Obrigatório: Raspberry Pi + câmera, processamento OpenCV, armazenamento local, sincronização e API online para dashboard/login/cadastro. LEDs, buzzer, servo e sensor são opcionais e não bloqueiam o modo câmera.

Não incluir recuperação/redefinição de senha, diagnóstico de doenças, processamento de visão na Vercel, streaming contínuo de vídeo ou controle público do Pi nesta fase.

Banco já existe, conforme informado pelo responsável. Inspecionar schema, migrations, contratos e código antes de alterar. Não recriar banco, apagar tabelas ou executar migração destrutiva. SQLite local e Neon remoto são arquitetura de referência anterior; confirmar aderência ao ambiente real.

## 2. SEPARAÇÃO DE RESPONSABILIDADES

### Backend no Raspberry Pi

- Python + FastAPI para comandos locais autenticados, saúde e consultas locais necessárias.
- Worker serial para câmera e OpenCV; um único dono do equipamento.
- SQLite local e outbox persistente, com análises e eventos gravados atomicamente.
- Sincronizador separado que envia registros por HTTPS para API online.
- Drivers opcionais carregados somente quando configurados e necessários.

### API online

- Receber registros enviados pelo dispositivo, autenticar a origem e impedir duplicação.
- Consultar o banco existente e oferecer agregados, histórico, detalhe e sincronização autorizados.
- Implementar cadastro, login, sessão e logout para usuários.
- Pode ser implantada como funções na Vercel, conforme compatibilidade do código e limites da hospedagem; alternativa é serviço hospedado separado. Confirmar escolha antes de implementar.
- Não manter loop de câmera, worker permanente ou SQLite do Raspberry dentro de função da hospedagem.

### Frontend

React consulta API online. Nunca recebe senha do banco, segredo do dispositivo ou acesso direto ao PostgreSQL. Estar logado no dashboard remoto não concede permissão de captura local.

```text
Câmera → worker local → transação SQLite: análise + outbox
                                    ↓
                        sincronizador HTTPS de saída
                                    ↓
                        API online de ingestão
                                    ↓
                         banco remoto existente
                                    ↑
React autenticado → API de consulta/autenticação
```

Escolha desta proposta: envio via API de ingestão. Não implementar simultaneamente escrita direta Pi→Neon e envio pela API para o mesmo fluxo. Se o projeto já usa outra estratégia, revisar compatibilidade antes de migrar.

## 3. ESTRUTURA PROFISSIONAL DE REFERÊNCIA

```text
backend/
  device/
    app/
      main.py
      api/                 # rotas locais, validação e dependências
      application/         # casos de uso: captura, status e consulta
      domain/              # modelos, regras e erros sem dependência HTTP/GPIO
      infrastructure/
        camera/            # adaptador da câmera real
        vision/            # OpenCV e parâmetros de calibração
        persistence/       # SQLite, transações e outbox
        hardware/          # adaptadores opcionais
      worker/              # execução serial e estados
      sync/                # lotes, reenvio e confirmação
      config/              # configurações e validação
    migrations/
    tests/
  web_api/
    api/                   # adaptadores da hospedagem
    application/           # autenticação, ingestão e consultas
    domain/
    infrastructure/        # banco, sessão e armazenamento privado
    migrations/
    tests/
  contracts/               # OpenAPI/schemas compartilháveis e versionados
  README.md
```

Adaptar a estrutura ao repositório existente. Não duplicar frameworks, criar pastas vazias ou migrar linguagem somente para seguir este desenho. Se API online já for TypeScript, preservar seus padrões profissionais; não exigir backend Node completo adicional apenas por preferência.

Rotas tratam HTTP; casos de uso orquestram; domínio guarda regras; adaptadores acessam banco/câmera. Não colocar SQL, OpenCV e autenticação dentro de uma única função de rota.

## 4. FLUXO LOCAL E CONCORRÊNCIA

Estados de referência: INICIALIZANDO → PRONTO → CAPTURANDO → ANALISANDO → REGISTRANDO → PRONTO, com ERRO quando necessário.

1. Validar autenticação, permissão e disponibilidade da câmera.
2. Aceitar comando com identificador de idempotência para tratar reenvios.
3. Reservar capacidade de execução antes de confirmar aceitação.
4. Executar captura/processamento fora do event loop HTTP.
5. Gerar UUID estável e persistir resultado + outbox em transação.
6. Confirmar conclusão somente após persistência real.

Fila limitada; rejeitar excesso com resposta documentada. Apenas um processamento acessa a câmera por vez. Não aumentar workers HTTP de modo que cada processo inicialize sua própria câmera. Em múltiplos processos, manter dono único em serviço dedicado e transporte de comandos explícito.

Se execução assíncrona, comando retorna 202 + job_id; consulta do job fornece estado real. Persistir estado necessário para não perder rastreabilidade em reinicialização. Após timeout no cliente, consultar comando existente antes de criar outro. Em reinício, marcar jobs interrompidos honestamente; não fingir conclusão nem repetir automaticamente atuação física.

## 5. CÂMERA E PROCESSAMENTO

- Confirmar câmera CSI/USB e driver real; inicializar uma vez quando apropriado e liberar no encerramento.
- Capturar sob demanda; não processar vídeo continuamente sem necessidade comprovada.
- Fixar resolução, iluminação e formato a partir de medições de qualidade/custo; não inventar configuração ideal.
- Limitar tamanho de imagem, buffers e memória; liberar objetos temporários após uso.
- Localizar e segmentar a fruta antes de classificar.
- Extrair proporção de cor, regiões anormais, circularidade e assimetria somente da região válida.
- Registrar score experimental, classe e justificativa com versão de calibração.
- Classes: APROVADA, ATENCAO e REVISAR. Falha de aquisição/segmentação é estado de erro, não REVISAR automático.
- Sem limiares universais inventados. Não afirmar doenças, integridade interna, inocuidade ou acurácia não avaliada.

Persistir imagens fora do banco, com nomes controlados por UUID, retenção e acesso autorizado. Escrita de arquivo e transação de banco não são atomicamente a mesma coisa: usar arquivo temporário + renomeação segura e rotina de reconciliação de órfãos/referências quebradas. Falha de arquivo precisa ter estado explícito.

## 6. HARDWARE OPCIONAL

LEDs, buzzer, servo e sensor de presença são extensões. Ausência é funcionamento normal. Nenhuma importação ou inicialização GPIO obrigatória no modo câmera.

Backend informa capacidades com device_id, observed_at e estado por componente:

- available: presença e disponibilidade confirmadas;
- absent: ausência confirmada por configuração/diagnóstico apropriado;
- unavailable: instalado/configurado, mas não operacional;
- unknown: não foi possível confirmar.

Configuração declarada não equivale a detecção elétrica universal. GPIO não identifica automaticamente todo periférico. Informar a origem da conclusão quando relevante; não alegar descoberta automática de LED/servo sem mecanismo verificável.

Frontend mostra informação de componentes presentes; ausentes são omitidos. Falha opcional é contextual e não interrompe câmera. Se instalado, definir saídas seguras ao iniciar/falhar/encerrar conforme montagem validada. Sensor opcional exige debounce e prevenção de análise repetida da mesma fruta.

Status sincronizado é última observação, não estado ao vivo. Credenciais, pinagem interna sensível e diagnóstico detalhado não são expostos publicamente.

## 7. BANCO EXISTENTE E MODELO DE REFERÊNCIA

Antes de codificar: identificar provedor, schema, tabelas, índices, restrições, migrations, timezone, usuários e conexões existentes. Registrar diferenças sem revelar secrets.

Análise de referência: UUID, device_id, timestamp, classe, quatro métricas, score, calibração, lote opcional, observações e sincronização. Dados inválidos não devem entrar como medição válida. Não alterar silenciosamente unidades/campos existentes; criar mapeamento explícito no contrato.

- Razões de cor/regiões anormais/assimetria: 0–1.
- Score: 0–100, experimental.
- Circularidade: domínio validado pelo processamento; não assumir teto sem contrato.
- Timestamp UTC ou ISO 8601 com offset; frontend exibe America/Sao_Paulo.
- Análises concluídas append-only na base inicial; correções auditadas ou avaliações em modelo separado.
- Usuários/sessões: adaptar ao schema existente e hashes seguros existentes.

Consultas parametrizadas e transações curtas. Índices guiados por consultas reais, como dispositivo+timestamp e filtros de classe/lote, avaliando plano de execução. Não criar índice para toda coluna sem necessidade.

## 8. OUTBOX E SINCRONIZAÇÃO

Transação SQLite grava análise e evento PENDING. Outbox registra ID estável, versão do contrato, payload, tentativas, próxima tentativa, erro resumido e estado. Schema final depende do existente.

- Processo separado do pipeline de câmera, sem bloquear nova inspeção por falta de internet.
- Enviar lotes limitados por quantidade E bytes, com timeout e backoff exponencial com jitter.
- Respeitar rate limit/Retry-After. Rede e falhas transitórias podem repetir; payload inválido precisa de intervenção/quarentena, sem loop agressivo.
- API confirma cada item somente após commit remoto; Pi marca SYNCED após confirmação.
- ID reenviado com mesmo conteúdo retorna confirmação idempotente. Mesmo ID com conteúdo conflitante é conflito, não overwrite silencioso.
- Item inválido não deve prender todos os seguintes indefinidamente; contrato define resultados parciais ou atomicidade do lote.
- Sem garantias falsas de exactly-once de transporte: usar entrega com reenvio e efeito idempotente no banco.
- Monitorar backlog, idade do item mais antigo e disco. Definir retenção sem descartar pendências silenciosamente.
- Não sincronizar o arquivo SQLite inteiro nem incluir credenciais do banco no payload.

## 9. INGESTÃO ONLINE E IDENTIDADE DO DISPOSITIVO

POST /api/ingest/analyses é rota PROPOSTA a validar.

Autenticar dispositivo com credencial própria por equipamento, revogável e limitada a ingestão; não reutilizar senha de usuário, sessão de navegador ou senha administrativa do banco. HTTPS obrigatório. Secrets ficam somente no Pi/servidor, fora do Git/logs.

Backend associa identidade autenticada ao device_id permitido; não confiar no device_id enviado para gravar em nome de outro equipamento. Validar versão, tamanho, campos, enums e limites por lote. UUID garante deduplicação, não autenticação.

Resposta inclui confirmações por item ou erro documentado. Não responder sucesso antes da gravação. Não aceitar comandos de hardware nessa API de ingestão.

## 10. LOGIN, CADASTRO E SESSÕES

Obrigatórios: cadastro, login, consulta de sessão e logout. Sem recuperação/redefinição nesta fase.

Campos seguem banco e contrato existentes; nome/e-mail/senha são proposta mínima. Validar entrada no servidor, unicidade transacional e menor privilégio. Cadastro não concede administrador nem acesso a todos os dispositivos. Definir quem pode consultar cada recurso.

Senhas: Argon2id com salt aleatório por senha e biblioteca mantida. Referência inicial: pelo menos 19 MiB, 2 iterações e paralelismo 1; medir no servidor e ajustar custo. SHA-224/256/512 puro não é armazenamento seguro de senha. Não criar algoritmo próprio nem criptografar reversivelmente a senha. Preservar verificação de hashes seguros existentes ao planejar evolução.

Sessões preferencialmente opacas, com identificadores aleatórios fortes; armazenar representação protegida no servidor, expirar e revogar. Cookie HttpOnly, Secure em produção, SameSite apropriado. Rotacionar ao autenticar. Logout POST invalida no servidor e remove cookie. Proteção CSRF nas operações com cookie e CORS por allowlist.

Rate limit de login/cadastro em armazenamento compartilhado adequado à implantação, não contador em memória de função efêmera. Erro de login genérico; não logar credenciais. Política de senha consistente, sem truncamento silencioso, permitindo frases e gerenciadores. Quantidade de tentativas e política exata devem ser documentadas e testadas.

Autorização no servidor em cada consulta por usuário/dispositivo/UUID. Respostas de sessão nunca retornam hash/senha. Não expor secrets em VITE_* ou bundle. Limitar consumo de recursos da função de hash para prevenir exaustão.

Referência: https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html

## 11. CONTRATOS DE API PROPOSTOS

Reutilizar rotas já existentes quando compatíveis. Esta lista não comprova endpoints implementados.

| Método/rota | Responsabilidade |
|---|---|
| POST /api/auth/register | Cadastro validado |
| POST /api/auth/login | Estabelecer sessão |
| GET /api/auth/session | Sessão e usuário público |
| POST /api/auth/logout | Revogar sessão |
| POST /api/ingest/analyses | Ingestão autenticada por dispositivo |
| GET /api/analyses | Histórico autorizado, paginado e filtrado |
| GET /api/analyses/:id | Detalhe autorizado |
| GET /api/metrics/summary | Totais e denominadores do recorte |
| GET /api/metrics/distribution | Contagens por classe |
| GET /api/metrics/timeseries | Agregados por intervalo para gráficos |
| GET /api/sync/status | Última sincronização por dispositivo autorizado |
| GET local /api/health | Saúde mínima do serviço local |
| GET local /api/system/status | Câmera e capacidades em canal autorizado |
| POST local /api/capture | Captura autenticada e serializada |
| GET local /api/jobs/:id | Estado de comando assíncrono, se adotado |

Paginação bounded: máximo explícito e ordenação estável com desempate. Offset serve ao início; cursor pode ser adotado para volumes grandes com contrato documentado. Validar período, classe, dispositivo, lote, limite e granularidade.

Erros coerentes: 400/422 validação conforme framework/contrato, 401 sessão ausente, 403 sem permissão, 404 conforme política de existência, 409 ocupado/conflito, 429 limite, 503 indisponibilidade. Erros de domínio são traduzidos na borda HTTP, sem stacktrace público.

OpenAPI documenta schemas, exemplos ilustrativos, autenticação, unidades, nullability, limites e paginação. Não confundir nomes internos do banco com contrato externo sem adaptador.

## 12. DADOS PARA INDICADORES E GRÁFICOS

Backend agrega sobre TODO o recorte autorizado, não só página atual.

- Resumo: total de análises válidas, contagens por classe, aprovadas/denominador, último evento e referência temporal.
- Distribuição: APROVADA/ATENCAO/REVISAR, contagens, total e cobertura completa ou parcial explícita.
- Série temporal: início/fim de bucket, timezone, granularidade, contagens por classe e total.
- Opcional: médias das métricas, amostras por bucket, histogramas de score e versões de calibração.
- Erros de aquisição separados das classes; REVISAR não é falha técnica.
- Denominador zero produz taxa nula/indisponível, não NaN ou percentual fictício.
- Intervalo sem cobertura é lacuna; preencher zero apenas quando ausência de eventos foi confirmada.
- Filtros devem aplicar a mesma semântica entre resumo, distribuição, série e histórico.
- Limites de período/buckets evitam consultas ilimitadas. Intervalos e timezone definidos; preferência por início inclusivo e fim exclusivo.

Preferir as_of/snapshot coerente quando possível; se endpoints não compartilham snapshot, retornar horários e não prometer atomicidade entre respostas. Taxa de aprovação não equivale a acurácia.

## 13. IMAGENS E ARMAZENAMENTO

Metadados no banco, imagens em filesystem local. Upload remoto privado é incremento separado, com retenção, tamanho/formato permitido e associação a UUID autorizado.

Não expor path arbitrário, permitir traversal ou aceitar URL externa irrestrita para o servidor buscar. URLs temporárias só após autorização. Imagem não enviada deve ter estado explícito; UI não inventa link. Falha de upload não deve destruir análise durável, mas precisa ser rastreada.

## 14. OTIMIZAÇÃO COM MEDIÇÃO

Objetivo: reduzir CPU, memória, escrita em disco e consultas sem sacrificar durabilidade ou segurança.

- Medir tempo de captura, processamento, persistência, sincronização e consultas; registrar percentis quando houver amostra adequada.
- Definir orçamento de RAM, resolução e latência após confirmar modelo do Pi e testes reais. Não prometer FPS/tempo sem evidência.
- Reutilizar câmera/clientes HTTP e conexões conforme driver seguro; evitar reabrir a cada pequeno passo.
- Manter buffers limitados e evitar cópias redundantes de imagens grandes.
- Processamento pesado fora do event loop; escolher thread/processo conforme biblioteca e medições, sem paralelizar câmera.
- SQLite com transações curtas, parâmetros de durabilidade justificados e WAL quando apropriado. Não desligar fsync/garantias de gravação para ganhar benchmark. Coordenar backup de forma compatível com WAL.
- Separar migração da inicialização concorrente; não executar alteração de schema em cada request.
- No banco remoto, queries agregadas, limites, índices úteis e evitar N+1.
- Usar conexão/pool compatível com funções da hospedagem e orçamento global de conexões; não abrir pool grande por instância. Credenciais ficam no servidor.
- Cache opcional de agregados somente após medir, com TTL/invalidação e escopo de autorização. Não compartilhar dados privados entre usuários por chave incompleta.
- Não instalar Redis, Kafka, Kubernetes ou outro serviço sem problema comprovado. Não remover validação, hashing seguro ou proteção de acesso por desempenho.
- Retenção de logs/imagens e limpeza controlada impedem disco cheio; não apagar análises/outbox pendentes silenciosamente.

## 15. OBSERVABILIDADE E OPERAÇÃO

Logs estruturados com request_id, analysis_id, job_id e device_id quando pertinentes; nunca senha, hash, cookie, segredo ou imagem bruta no log. Registrar erro técnico internamente e mensagem pública segura.

Métricas úteis: duração por etapa, taxa de falha de aquisição/processamento, tamanho/idade da outbox, retries, espaço em disco, latência da API, limites de conexão e falhas de autenticação sem credenciais.

Health checks distinguem processo vivo, pronto para capturar e capacidade de persistir. Internet indisponível não torna câmera local indisponível. API online não alcançar o Pi não comprova hardware offline; mostrar última observação.

Encerramento gracioso: parar aceitação, encerrar trabalho conforme política, manter estado honesto, liberar câmera e fechar conexões. Supervisão no Pi após validação operacional, com usuário de menor privilégio.

## 16. CONFIGURAÇÃO

.env.example contém apenas nomes e placeholders; secrets reais fora do Git. Separar configuração do Pi e servidor online. Exemplos conceituais:

- Pi: DEVICE_ID, SQLITE_PATH, WEB_API_BASE_URL, DEVICE_INGEST_CREDENTIAL, SYNC_INTERVAL_SECONDS, SYNC_BATCH_SIZE, CAMERA_ADAPTER.
- Online: DATABASE_URL, configuração de sessão, origens permitidas e limites.
- Opcionais: habilitação e parâmetros validados de cada periférico, desativados por padrão.

Nomes dependem do código existente. Não transferir secrets para configuração pública do React. Validar obrigatórios no início e falhar com mensagem segura, sem imprimir valores sensíveis.

## 17. TESTES E CRITÉRIOS DE ACEITE

1. Inicializar e completar análise só com câmera, sem GPIO/periféricos extras.
2. Falha opcional não bloqueia fluxo; capacidade desconhecida não vira ausência confirmada.
3. Duas capturas concorrentes não acessam câmera ao mesmo tempo; fila limitada e comando repetido não duplica.
4. Falha de captura/segmentação não produz classe fictícia.
5. Análise + outbox são atômicas; falha de disco não retorna sucesso.
6. Reiniciar com jobs/outbox pendentes preserva rastreabilidade.
7. Sem internet, registrar localmente; reconexão sincroniza.
8. Perda de ACK e reenvio mantêm um UUID remoto; conteúdo conflitante é rejeitado.
9. Lote inválido não trava toda sincronização indefinidamente.
10. Credencial de dispositivo não acessa funções de usuário nem outro dispositivo.
11. Cadastro/login/logout/sessão expirada são exercitados contra banco real de integração.
12. API privada rejeita consulta sem permissão, inclusive detalhe por ID.
13. Hash de senha é seguro; não há segredo em logs, bundle ou respostas.
14. Gráficos/resumo conferem com banco no mesmo recorte; testes de zero/nulos/timezone/paginação.
15. Imagem privada exige autorização; paths e tamanhos são validados.
16. Medir RAM, CPU e latência no Pi antes de declarar otimização concluída.

Testes de LED/buzzer/servo/sensor são N/A quando ausentes. Não considerar ausência como falha do projeto.

## 18. ENTREGA ESPERADA

Código incremental preservando banco/repositório existentes, contratos OpenAPI, migrations revisáveis quando necessárias, .env.example sem secrets, testes pertinentes, instruções de operação e relatório do que foi validado.

Informar diferenças entre implementado, proposto e pendente. Nenhum banco ou backend foi alterado por este documento. Para atualizar código executável, é necessário inspecionar a versão atual do repositório e seu schema.

## 19. AJUSTE DE RESPONSABILIDADES — RASPBERRY MÍNIMO

Esta seção prevalece sobre sugestões anteriores que ampliem o papel do Raspberry. Login, cadastro, sessão de usuários, agregação para gráficos e regras de acesso do site pertencem à API ONLINE, nunca ao processo de visão do Pi.

### Raspberry Pi: responsabilidades essenciais

1. Capturar a imagem da câmera.
2. Confirmar aquisição e segmentação válidas.
3. Avaliar características externas da laranja e produzir classe/métricas experimentais com calibração identificada.
4. Salvar resultado no SQLite e registrar pendência de sincronização atomicamente.
5. Enviar registros ao serviço online com credencial do dispositivo; confirmar envio somente após gravação reconhecida.
6. Repetir pendências quando a conexão voltar, sem duplicar registros.

Não implementar no Pi cadastro de usuários, hash de suas senhas, banco de sessões do site, recuperação de conta, endpoints de gráficos, paginação do dashboard remoto, cache distribuído ou regras de formulários web.

### Validações no frontend

Campos obrigatórios, formato inicial do identificador/e-mail, confirmação de senha, limites de preenchimento coerentes com o contrato, período inicial/final, feedback imediato, prevenção de clique duplicado e disponibilidade visual de ações.

Essas verificações melhoram a experiência. O frontend pode ser contornado; portanto não é fonte de confiança para autorização ou escrita no banco.

### Validações na API online

Credenciais e sessão do usuário, hash seguro de senha, autorização por dispositivo/recurso, entrada dos formulários, unicidade no banco, filtros de consulta, limites de lote, schema dos registros recebidos e deduplicação por UUID. Agregação de métricas/gráficos ocorre aqui ou no banco remoto.

A API online autentica a credencial do Pi e associa o dispositivo permitido. O Pi não precisa conhecer usuários do dashboard. Cadastro de usuário não cadastra automaticamente hardware.

### Validações mínimas que permanecem no Raspberry

Não remover verificações indispensáveis ao resultado e à persistência: câmera disponível, imagem válida, fruta segmentada, métricas calculáveis, espaço/erro de gravação, exclusão mútua da câmera e confirmação de sincronização. Não classificar imagem inválida nem reportar dado salvo/enviado quando houve falha.

Não duplicar no Pi a política completa de validação da API online. A biblioteca de contratos pode fornecer apenas a serialização mínima necessária, sem trazer autenticação de usuários ou dependências web extras ao worker.

### Simplificação da API local

FastAPI local NÃO é requisito obrigatório para o modo mínimo. Se câmera e worker são acionados por comando local/controlador já existente, manter esse fluxo sem criar servidor HTTP adicional.

Adicionar API local apenas se houver necessidade real de botão de captura/status em interface local. Nesse caso, expor o mínimo necessário, restringir à interface/rede autorizada e proteger comandos. Isso não exige replicar contas e sessões do site no Pi. O mecanismo de acesso local deve ser definido conforme o ambiente.

Fila de jobs HTTP e endpoint de acompanhamento são opcionais, somente quando esse modo for adotado. Para o modo câmera simples, um executor serial com estado local e sincronizador separado pode bastar. Não criar job framework, broker ou arquitetura distribuída por antecipação.

### Fluxo final pretendido

```text
RASPBERRY
câmera → avaliar laranja → salvar SQLite/outbox → enviar HTTPS
                                                     ↓
API ONLINE
validar dispositivo/registro → gravar no banco existente
login/cadastro/sessão → autorizar consultas → agregar gráficos
                                                     ↑
FRONTEND
validar formulários → chamar API → mostrar dados/gráficos
```

Otimização significa pouca responsabilidade e poucas dependências no Pi, sem remover controles necessários à correção dos resultados e à durabilidade dos dados.
