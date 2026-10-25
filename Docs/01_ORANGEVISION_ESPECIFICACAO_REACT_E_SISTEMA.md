# OrangeVision — Especificação de produto, site React, dashboard e sistema embarcado

> **Versão:** 2.0 — arquitetura híbrida React + Neon PostgreSQL + SQLite local (08/10/2026)  
> **Projeto:** OrangeVision — triagem visual de laranjas com Raspberry Pi  
> **Curso:** Engenharia da Computação — Universidade São Francisco (USF)  
> **Setor:** Primeiro Setor — Agronegócio  
> **ODS relacionado:** ODS 2 — Fome Zero e Agricultura Sustentável  
> **Leitura conjunta:** `02_ORANGEVISION_GUIA_MONTAGEM_RASPBERRY.md`

## 1. Objetivo deste documento

Este arquivo é um **briefing técnico e funcional para desenvolver a versão React do Google Sites e o sistema real**. Pode ser entregue a um desenvolvedor ou a uma IA de programação como fonte de requisitos.

**Distinguir obrigatoriamente:**
- **Conteúdo já definido:** estrutura e narrativa do Google Sites, fluxo lógico, categorias e diretrizes do protótipo.
- **A implementar:** código React, FastAPI, controle de hardware, captura, análise, banco, dashboard, testes e documentação final.
- **A validar na bancada:** modelo exato de Raspberry Pi, câmera, sensores, atuadores, montagem mecânica, condições de iluminação e limiares da classificação.

Não exibir dados de desempenho como reais até serem medidos.

## 2. O que é o OrangeVision

Sistema de **triagem visual de laranjas** que utiliza câmera e processamento local (Edge Computing) em um Raspberry Pi para avaliar **características externas** da fruta e auxiliar a decisão de triagem. O sistema deve registrar cada análise em banco de dados e mostrar indicadores em um dashboard web.

### Problema

A inspeção manual pode ser repetitiva e subjetiva, e o registro de ocorrências pode ser pouco padronizado.

### Proposta de solução

1. Posicionar uma laranja em área de inspeção iluminada.
2. Detectar a presença com sensor IR ou permitir captura manual.
3. Capturar imagem pela câmera conectada ao Raspberry Pi.
4. Segmentar a fruta na imagem usando Python + OpenCV, localmente.
5. Extrair métricas visuais: cor, regiões visualmente anormais, circularidade e assimetria.
6. Calcular score **experimental e calibrado**, com justificativa de cada classe.
7. Classificar: `APROVADA`, `ATENCAO` ou `REVISAR`.
8. Sinalizar o resultado com LEDs, buzzer e posicionamento do servo (conforme desenho mecânico).
9. Persistir primeiro a análise **com UUID**, imagem associada e estado de sincronização no SQLite local + Neon PostgreSQL (sincronizado).
10. Sincronizar registros concluídos com o **Neon PostgreSQL** pela internet (envio de saída a partir do Raspberry), com tentativas e prevenção de duplicidade.
11. Exibir dados remotos reais no React através de **API protegida hospedada**; comandos sobre o hardware permanecem em API local/autenticada.

**Limite científico:** câmera comum identifica indícios visuais externos; não determina automaticamente doenças específicas, integridade interna, inocuidade nem qualidade agronômica completa. Sem conjunto de referência rotulado, não afirmar “acurácia do modelo”.

## 3. Arquitetura aprovada — Neon + SQLite e React público

**Decisão adotada:** React + TypeScript + Vite (site institucional e dashboard), **Neon PostgreSQL como banco de consulta online**, **SQLite local no Raspberry Pi para durabilidade offline**, **Python/FastAPI e worker OpenCV/GPIO no Raspberry Pi**, além de **rotas/funções de API no servidor da hospedagem do React** para leitura protegida do Neon.

**Não é preciso outro backend completo em Node.js/Go:** a API hospedada pode ser composta por funções leves da plataforma de hospedagem (ex.: funções serverless da Vercel). Essas funções, embora sejam código de servidor, não substituem o FastAPI que opera o equipamento.

```text
            USUÁRIO (DESKTOP / CELULAR)
                     |
             React + TypeScript
              site + dashboard
                     |
                HTTPS / JSON
                     v
         API hospedada protegida (somente leitura)
                     |
                     v
            NEON POSTGRESQL (NUVEM)
                     ^
            TLS / saída autenticada
                     |
        sincronizador Python (outbox + retry)
                     |
          SQLITE LOCAL (Raspberry Pi)
                     ^
                     |
     worker OpenCV + câmera + sensor + GPIO
            RASPBERRY PI (EDGE)
                     |
        FastAPI LOCAL para comandos/saúde
            (somente rede autorizada)
```

### Por que arquitetura híbrida?

- O **Edge é obrigatório**: o Raspberry faz a análise OpenCV e a atuação física mesmo **sem internet**.
- A análise é registrada primeiro no SQLite. Falta de conectividade com o Neon **não bloqueia** a inspeção.
- O sincronizador envia as análises pendentes ao Neon quando a rede retorna, sem criar duplicatas; o painel remoto mostra **última sincronização** e pode estar desatualizado.
- O site React hospedado publicamente consulta **apenas a API da hospedagem**; **não coloca strings de conexão, senhas ou tokens privilegiados no navegador**.
- A **câmera, os GPIOs e `/api/capture` não ficam publicamente acessíveis**. Captura por botão pode operar pela rede local; comandos remotos só com arquitetura específica e autorização reforçada.
- **Imagens** ficam inicialmente no Raspberry. Para mostrá-las no dashboard remoto, é necessário upload a armazenamento de objetos privado (a definir); **não gravar arquivos grandes no PostgreSQL**. Até implementar, exibir métricas e um aviso "imagem disponível apenas no dispositivo".

### Responsabilidades e onde executa

| Camada | Local | Responsabilidades |
|---|---|---|
| React | Vercel ou outra hospedagem estática | Site, dashboard responsivo, gráficos, filtros, estados de carregamento/offline |
| API web (`/api/*`) | Funções serverless da hospedagem | Consultar Neon com segredo do servidor, validar filtros, limitar requisições e controlar acesso |
| Neon PostgreSQL | Nuvem | Armazenar eventos sincronizados, consultas agregadas, histórico por dispositivo/lote |
| FastAPI | Raspberry Pi, rede local | Saúde, diagnóstico, consultas locais e comando manual protegido |
| Worker Python | Raspberry Pi | Presença, câmera, segmentação, 4 métricas, classe e GPIO; um ciclo por fruta |
| SQLite + outbox | Raspberry Pi | Registro durável local, fila de sincronização, reenvio após queda de internet |
| Armazenamento de imagem | Pi (inicial); bucket privado (futuro) | Original/anotada por UUID, retenção e acesso seguro |

### Implantação e operação

- **Desenvolvimento:** React (`npm run dev`) no computador, FastAPI local no Pi e banco Neon de desenvolvimento; segredos em `.env` não versionados.
- **Demonstração sem internet:** Raspberry continua registrando análises e atuando nos LEDs/servo/buzzer; dashboard local opcional via FastAPI. O dashboard público pode exibir a **última versão sincronizada**, identificando que não é tempo real.
- **Site publicado:** React hospedado + API de consulta hospedada + Neon; o Raspberry só faz conexões **de saída** para sincronização, com TLS.
- **Controle de acesso:** leituras públicas agregadas podem ser permitidas se não houver informação sensível; histórico detalhado, fotos e comandos exigem autenticação/autorização, conforme decisão de publicação.
- **Dados simulados:** aceitar apenas com rótulo explícito "simulação"; jamais mesclar com medições reais.

## 4. Escopo funcional: duas áreas dentro do React

### A. Site institucional (substitui o Google Sites)

Deve apresentar o projeto de forma acadêmica e coerente com o que for realmente desenvolvido. Rotas propostas:

| Rota | Página | Conteúdo obrigatório |
|---|---|---|
| `/` | Início | apresentação, resumo, três pilares, fluxo do sistema, problema × solução, setor/ODS 2, stack tecnológica, links |
| `/projeto` | O Projeto | contexto, problema, solução, objeto de estudo (laranja Pêra-Rio, se mantida), objetivos, escopo e limitações |
| `/planejamento` | Planejamento | 5W2H, etapas, cronograma, recursos, custos **estimados** e entregáveis |
| `/desenvolvimento` | Desenvolvimento | arquitetura, hardware, GPIO, visão computacional, lógica de classificação, referências técnicas, software, banco, integração, testes e protótipo |
| `/dashboard` | Dashboard | indicadores e histórico **sincronizados no Neon via API hospedada**, identificando última atualização/atraso; estados de carregamento, sem dados e offline |
| `/resultados` | Resultados | plano de testes, evidências, avaliações, métricas realmente medidas e limitações |
| `/equipe` | Equipe | seis integrantes e áreas de atuação; revisar descrições antes da publicação |
| `/referencias` | Referências | fontes técnicas, citricultura, ODS 2 e fontes bibliográficas completas |

**Design system** já usado no Google Sites:
- Laranja `#F97316` — acentos, detalhes, links/botões.
- Verde `#15803D` — agronegócio, destaque e seções.
- Grafite `#111827` — texto, cabeçalho e rodapé.
- Branco `#FFFFFF` — fundo de cards e conteúdo.
- Tipografia preferencial: Montserrat em títulos e Roboto no corpo, com fallbacks locais.
- **React não usa iframes dos blocos do Google Sites:** construir componentes reais, não copiar os HTMLs incorporados como iframes.
- Responsivo: desktop 3 colunas quando aplicável, tablet 2, mobile 1; gráficos e tabelas com adaptações próprias; **não provocar rolagem horizontal na página**.
- Acessibilidade: contraste, `alt` das imagens, foco visível, navegação por teclado e estados de erro.

### B. Aplicação operacional / Dashboard

Funcionalidades do MVP:

1. **Status dos dados**: online/offline da API web, última sincronização conhecida e indicação de dados potencialmente desatualizados. **Estado ao vivo de câmera/sensor** só disponível em rede local ou canal autenticado específico.
2. **Resumo:** total analisado, aprovadas, atenção, revisar e percentual aprovado (`aprovadas / total`; não confundir com acurácia).
3. **Histórico de análises:** data/hora, ID, classe, score, cor, regiões anormais, circularidade, assimetria, miniatura da imagem e detalhes.
4. **Distribuição por classificação:** gráfico de barras/rosca.
5. **Filtros:** período, classificação, lote (se houver).
6. **Detalhes de uma análise:** métricas, critérios e (quando habilitado upload privado) imagem original/anotada. Não inventar URL remota para imagens que só existem no Pi.
7. **Análise manual:** botão **somente no modo local/autenticado**, na rede autorizada, para disparar uma captura no FastAPI. No dashboard público, ocultar ou desabilitar esse controle.
8. **Configurações experimentais:** mostrar valores atuais de calibração; edição protegida e auditada fica para fase posterior.
9. **Exportação:** CSV de análises, se houver tempo; sem inventar dados.
10. **Atualização:** polling remoto em intervalo moderado (ex.: 15–30 s ou refetch manual), com limite de custo e requisições; polling local pode ser mais frequente. WebSocket/SSE não é exigência inicial.

Estados da interface: `carregando`, `sem dados`, `API offline`, `hardware indisponível`, `processando`, `concluído`, `erro`.

### Não implementar inicialmente

- Login complexo, multilocatário, processamento em nuvem, pagamentos, IA generativa como classificador primário, streaming contínuo de vídeo para a internet, predição de doenças específicas, classificação interna da fruta e separação mecânica de alto desempenho.

## 5. Páginas: checklist de conteúdo herdado do Google Sites

### Início

- [ ] Hero com marca OrangeVision e chamada “Visão Computacional aplicada à triagem inteligente de laranjas”.
- [ ] Resumo do sistema (Raspberry + câmera + OpenCV + resultados).
- [ ] Cards: **Visão Computacional**, **Edge Computing**, **Agronegócio**.
- [ ] Fluxo visual do processo com 6+ etapas; refletir sensor/atuadores conforme protótipo.
- [ ] Cards **Problema** e **Solução**.
- [ ] Bloco verde Primeiro Setor / ODS 2.
- [ ] Stack Raspberry Pi, Python, OpenCV, Linux, **SQLite + Neon PostgreSQL**, Edge Computing, React e FastAPI; explicar papel de cada banco.
- [ ] CTAs Projeto / Equipe / Planejamento.

### O Projeto

- [ ] Contexto e justificativa.
- [ ] Objeto de estudo: laranja Pêra-Rio, **se essa variedade estiver realmente disponível nos testes**.
- [ ] Objetivo geral e objetivos específicos.
- [ ] Escopo: inspeção **externa**, iluminação controlada, protótipo acadêmico.
- [ ] Relação com ODS 2 sem prometer impacto quantitativo não medido.
- [ ] Limitações científicas e operacionais.

### Planejamento

- [ ] 5W2H (O quê, Por quê, Onde, Quando, Quem, Como, Quanto).
- [ ] Etapas: pesquisa → arquitetura → hardware → visão → dados/API/React → integração → testes → apresentação.
- [ ] Cronograma com datas reais da disciplina.
- [ ] Lista de materiais e custos registrados; orçamento anterior era **estimativa provisória**, não compra confirmada.
- [ ] Entregáveis N1/N2.

### Desenvolvimento (ordem sugerida)

1. Arquitetura do sistema.
2. Hardware e materiais.
3. GPIO e alimentação com esquema **validado**.
4. Visão Computacional.
5. Lógica de Classificação.
6. Referências Técnicas.
7. Software.
8. Banco de Dados (SQLite local + Neon).
9. Integração.
10. Testes.
11. Protótipo Final.

### Dashboard

- [ ] KPIs consultados no Neon via API hospedada; marcar horário da última sincronização do Pi.
- [ ] Gráfico por classificação.
- [ ] Métricas visuais: cor, regiões anormais, circularidade, assimetria, score visual.
- [ ] Tabela de histórico e detalhe por análise.
- [ ] Foto/print do painel real para documentação.

### Resultados

- [ ] Plano QA-001 a QA-011 (ver seção 12).
- [ ] Fotos e vídeos reais da montagem.
- [ ] Exemplos reais de imagens analisadas, com critérios e limitações.
- [ ] Resultados observados, taxa de êxito dos **testes do sistema** e eventuais métricas de classificação **apenas se validadas com rótulos de referência**.
- [ ] Falhas encontradas e correções.
- [ ] Considerações finais e melhorias futuras.

### Equipe

- [ ] Felipe Kenzo — Software • Documentação.
- [ ] Kauan Fernandes — Redes • Infraestrutura • Integração.
- [ ] Marcelo Capeletto — Qualidade • Testes • Documentação.
- [ ] Pedro Faria — Software • Backend • Integração.
- [ ] Glauber Sandi Martins — Desenvolvimento de Produto • Industrialização • Gestão de Projetos • Integração.
- [ ] João Assis — IoT • Sistemas Embarcados • Conectividade • Integração.
- [ ] Todos apresentados como estudantes do **3º ano de Engenharia da Computação — USF**, sujeito à confirmação editorial.

### Referências

- [ ] Embrapa: citricultura/variedades.
- [ ] Fundecitrus: contexto de alterações visuais, sem converter em diagnóstico.
- [ ] OpenCV: APIs de processamento de imagem.
- [ ] Raspberry Pi: câmeras, eletrônica, documentação da placa.
- [ ] Python, SQLite, Neon PostgreSQL e FastAPI.
- [ ] ONU — ODS 2.
- [ ] Artigos científicos adicionais, quando utilizados; formatar conforme padrão exigido pela universidade.

## 6. Arquitetura de código sugerida

```text
orangevision/
├── README.md
├── docs/
│   ├── requisitos.md
│   ├── montagem.md
│   ├── esquema-eletrico.png      # criar após validar ligações
│   └── evidencias/
├── frontend/                     # React + TypeScript + Vite
│   ├── package.json
│   ├── src/
│   │   ├── app/                  # Router e providers
│   │   ├── pages/                # Inicio, Projeto, Planejamento, Desenvolvimento...
│   │   ├── components/           # Header, Footer, Card, Stat, Timeline, Flow
│   │   ├── features/dashboard/   # KPIs, gráficos, histórico, status, filtros
│   │   ├── services/api.ts       # cliente HTTP para API web no mesmo domínio
│   │   ├── types/                # contratos TS espelhando API
│   │   └── styles/               # tokens responsivos
│   └── public/                   # logo, fotos autorizadas, assets
├── web-api/                      # funções HTTPS no servidor da hospedagem
│   ├── analyses/                 # consultas paginadas ao Neon
│   ├── metrics/                  # KPIs por período
│   └── sync-status/              # último recebimento do dispositivo
├── backend/                      # FastAPI no Raspberry Pi
│   ├── app/
│   │   ├── main.py              # ASGI, rotas e middleware
│   │   ├── api/                  # health, status, analyses, metrics, capture
│   │   ├── schemas/              # Pydantic
│   │   ├── services/             # orquestração, regras, exportação
│   │   └── repository/           # consultas locais SQLite
│   ├── sync/                    # outbox, reenvio idempotente, backoff
│   │   ├── outbox.py
│   │   └── neon_sync.py
│   ├── worker/
│   │   ├── camera.py             # Picamera2 ou adaptador USB
│   │   ├── sensor.py
│   │   ├── processor.py          # segmentação e métricas
│   │   ├── classifier.py         # decisão calibrada
│   │   ├── outputs.py            # LEDs, buzzer, servo
│   │   └── runner.py             # máquina de estados/eventos
│   ├── database/
│   │   ├── schema_sqlite.sql
│   │   ├── schema_neon_postgres.sql
│   │   └── migrations/
│   ├── tests/
│   └── requirements.txt ou pyproject.toml
└── data/
    ├── orangevision.db
    └── imagens/
        ├── originais/
        └── anotadas/
```

**Nota operacional:** FastAPI e worker podem compartilhar a mesma aplicação no MVP, mas o loop de sensores não deve bloquear requisições HTTP. Preferir fila de comandos e executor serial/worker dedicado. Apenas **um dono** acessa GPIO/câmera de cada vez.

## 7. Contratos preliminares das APIs

**API local no Pi:** `http://<IP_DO_PI>:8000/api`, **somente na rede autorizada**. Os endpoints `POST /capture`, `/jobs` e `/system/status` pertencem ao Pi.

**API web na hospedagem React:** `/api/analyses`, `/api/metrics/*`, `/api/sync/status` e `/api/analyses/:id`; consultas ao Neon ocorrem no servidor. Evitar conflito de roteamento ao implantar. A tabela abaixo indica o proprietário.

| Método | Rota | Onde roda / o que faz |
|---|---|---|
| GET | `/health` | Pi local: API online, versão, timestamp |
| GET | `/system/status` | Pi local: câmera, sensor, saídas, worker, última falha |
| GET | `/analyses?limit=20&offset=0&classification=...` | API web → Neon: histórico paginado validado |
| GET | `/analyses/{id}` | API web → Neon: análise detalhada por UUID |
| GET | `/analyses/{id}/image?kind=original` | Somente com bucket privado configurado, URL autorizada; caso contrário, indisponível no dashboard remoto |
| GET | `/metrics/summary?from=...&to=...` | API web → Neon: totais e taxa de aprovação |
| GET | `/metrics/distribution?from=...&to=...` | API web → Neon: distribuição de classes |
| POST | `/capture` | Pi local autenticado: agenda captura; 409 se ocupado |
| GET | `/jobs/{id}` | Pi local: andamento da operação |
| GET | `/export.csv` | API web → Neon: CSV filtrado opcional |
| GET | `/sync/status` | API web → Neon: último recebimento por device_id, marca atraso |

### Exemplo de resposta de análise (ilustrativo — NÃO é dado real)

```json
{
  "id": "9b6f6498-2fb6-4c94-b3f4-e8809bc69f0c",
  "timestamp": "2026-10-08T14:20:30-03:00",
  "classification": "ATENCAO",
  "metrics": {
    "orange_color_ratio": 0.64,
    "abnormal_region_ratio": 0.09,
    "circularity": 0.81,
    "asymmetry": 0.12,
    "visual_score": 67.0
  },
  "image_url": null,
  "lot": null,
  "calibration_version": "experimental-01",
  "device_id": "orangevision-pi-01",
  "synced_at": "2026-10-08T14:20:35-03:00"
}
```

Observações:
- Razões métricas de `0.0` a `1.0`; score de `0` a `100` — padronizar no backend e converter para `%` na tela.
- A nomenclatura de banco é **`regioes_anormais`**, evitando alternância com `manchas`.
- Salvar versão de calibração para rastrear classificações ao longo do projeto.
- Operações de comando precisam ter proteção/autorização, mesmo que rede local, e limites de frequência.
- Liberar CORS **somente** para origens conhecidas quando frontend estiver em outro host/porta.

## 8. Modelo de dados — SQLite (local) e Neon PostgreSQL (online)

Tabela principal `analises`:

| Campo | Tipo sugerido | Observação |
|---|---|---|
| `id` | TEXT UUID PRIMARY KEY | mesmo identificador local/remoto; gerado uma única vez no Pi |
| `data_hora` | TEXT local / TIMESTAMPTZ cloud | horário do evento em UTC ou ISO 8601 com timezone |
| `classificacao` | TEXT | APROVADA / ATENCAO / REVISAR |
| `cor_proporcao` | REAL | 0–1, medido **dentro da região da fruta** |
| `regioes_anormais` | REAL | 0–1, calculado **dentro da máscara da fruta** |
| `circularidade` | REAL | métrica com domínio definido e validado |
| `assimetria` | REAL | 0–1, alinhamento pelo objeto, não pelo quadro inteiro |
| `score_visual` | REAL | 0–100, versão experimental calibrada |
| `imagem_original` | TEXT | caminho relativo controlado |
| `imagem_anotada` | TEXT NULL | opcional |
| `versao_calibracao` | TEXT | rastreabilidade |
| `lote` | TEXT NULL | opcional |
| `status_execucao` | TEXT | concluída/erro conforme arquitetura |
| `observacoes` | TEXT NULL | motivo de revisão/falha |
| `device_id` | TEXT NOT NULL | origem estável da análise |
| `sincronizado_em` | TEXT / TIMESTAMPTZ NULL | marcar no local após confirmação do Neon |
| `criado_em_nuvem` | TIMESTAMPTZ cloud | timestamp de ingestão no Neon |

**Outbox SQLite:** tabela `sync_outbox(event_id UUID, entity_type, entity_id UUID, payload_json, status PENDING|SYNCED|FAILED, attempt_count, next_retry_at, last_error, created_at, synced_at)`. A análise e o evento outbox devem ser gravados na **mesma transação local**.

**Neon:** tabela `analises` com `id UUID PRIMARY KEY`, `device_id`, métricas, classe, lote, versão, timestamps e links de imagens **somente quando efetivamente enviados a um bucket**. Índices por `data_hora`, `classificacao`, `device_id` e `lote`; `ON CONFLICT (id) DO UPDATE` controlado ou `DO NOTHING` para idempotência. Aplicar migrations SQL/ORM nas duas bases, respeitando diferenças de dialeto.

Adicionais recomendados: `eventos_sistema` (falhas e ações), `dispositivos` (última atividade/sincronização) e `config_calibracao` (parâmetros e versão); opcional `avaliacoes_manuais` para rótulos humanos de validação.

**Regras:** abrir conexões por operação ou pool adequado; habilitar WAL no SQLite se necessário; consultar sempre com parâmetros; preservar imagens no sistema de arquivos; fazer backup e definir retenção. Não guardar senha/URL de conexão do Neon no frontend nem em Git. O sincronizador pode usar `psycopg`/driver compatível em conexão TLS de saída no Pi, ou uma API de ingestão autenticada no servidor; **escolher e documentar somente uma estratégia de escrita em produção**.

## 8.1. Protocolo de sincronização offline-first (obrigatório)

1. Worker gera `UUID v4` antes do processamento/persistência da análise.
2. Em **uma transação SQLite**, salva análise + entrada `PENDING` na outbox; se falhar, registra erro e não finge êxito.
3. Tarefa separada tenta enviar lotes pendentes, preservando ordem razoável, com **timeout**, TLS, limites e retry com backoff exponencial e jitter.
4. Neon grava pelo mesmo UUID e trata reenvios de forma **idempotente**. Não gerar novo UUID ao retransmitir.
5. Só depois de receber confirmação real do banco remoto, o Pi marca a entrada `SYNCED` e anota horário.
6. Em queda de rede, mantém filas locais; limite de disco, retenção de imagens, backup e observabilidade devem ser definidos.
7. Se a sessão cair **depois** do Neon gravar e **antes** da confirmação ao Pi, o reenvio por UUID deve manter apenas um registro.
8. Exibir `last_synced_at`, `pending_count` (somente status local) e aviso de **dados desatualizados** em interfaces apropriadas.
9. Tratar timestamps em UTC no banco e converter para `America/Sao_Paulo` apenas para exibição, quando aplicável.

**Exemplo de payload (ilustrativo):**

```json
{
  "id": "9b6f6498-2fb6-4c94-b3f4-e8809bc69f0c",
  "device_id": "orangevision-pi-01",
  "data_hora": "2026-10-08T17:20:30-03:00",
  "classificacao": "ATENCAO",
  "cor_proporcao": 0.64,
  "regioes_anormais": 0.09,
  "circularidade": 0.81,
  "assimetria": 0.12,
  "score_visual": 67.0,
  "versao_calibracao": "experimental-01",
  "imagem_original": null
}
```

**Política de conflito:** a versão inicial é **append-only** para análises concluídas: uma análise não é editada pelo dashboard. Eventuais avaliações humanas ficam em tabela separada. Não sincronizar banco SQLite inteiro nem expor o Pi para receber conexões públicas.

## 8.2. Privacidade, credenciais e publicação

- **Frontend React:** variáveis `VITE_*` são públicas no bundle; guardar somente URLs e configurações públicas. **Nunca `DATABASE_URL`, tokens do Neon ou senhas**.
- **API hospedada:** variável secreta `DATABASE_URL` no ambiente do servidor; usar acesso de banco restrito a `SELECT` quando viável, autenticação nas rotas sensíveis e paginação obrigatória.
- **Raspberry Pi:** segredo de escrita do Neon em arquivo `.env` com permissões restritas fora do Git; usuário do banco com permissões mínimas (`INSERT`/`UPDATE` necessários). Preferir credenciais distintas para leitura e escrita.
- **Fotos:** não tornar bucket público por padrão; escolher armazenamento de objetos privado e fornecer URL temporária autorizada após implementar upload e consentimento aplicável.
- **Custo/uso:** verificar os limites atuais do plano Neon e da hospedagem antes do deploy; limitar taxa e quantidade das consultas, retenção e quantidade de imagens.
- **Disponibilidade:** o banco pode estar online enquanto o Pi está offline; apresentar "última análise recebida" em vez de chamar de status em tempo real.

## 8.3. Variáveis e configuração esperadas

```dotenv
# frontend/.env (somente dados públicos)
VITE_API_BASE_URL=/api
VITE_APP_MODE=production

# API web (somente servidor, nunca expor no navegador)
DATABASE_URL=postgresql://USUARIO:SENHA@HOST/DB?sslmode=require

# Raspberry Pi (somente dispositivo, acesso restrito)
DEVICE_ID=orangevision-pi-01
SQLITE_PATH=./data/orangevision.db
NEON_DATABASE_URL=postgresql://USUARIO_ESCRITA:SENHA@HOST/DB?sslmode=require
SYNC_INTERVAL_SECONDS=30
SYNC_BATCH_SIZE=25
```

Valores acima são **placeholders**; não compartilhar segredos em prints, GitHub ou documentos publicados.

## 9. Regras de Visão Computacional — cuidados obrigatórios

1. **Detectar a fruta antes de classificar.** Se não houver fruta bem segmentada, registrar erro de aquisição/segmentação, e não “REVISAR” automaticamente.
2. **Não avaliar o fundo como se fosse mancha.** Região escura deve ser medida somente **dentro da máscara segmentada**.
3. **Não supor que toda laranja esteja perfeitamente laranja.** Cor verde pode fazer parte da casca e da maturação; estabelecer critérios com imagens reais e referências.
4. **Circularidade:** usar contorno da fruta, área, perímetro e cuidados com ruído/oclusões; `4πA/P²` é sensível à qualidade do contorno.
5. **Assimetria:** calcular após localizar e alinhar a fruta, e não a partir da metade do frame da câmera.
6. **Score e thresholds:** **não validar como verdade** `75/50` nem percentuais do código inicial de exemplo; são hipóteses a calibrar com dados reais.
7. **Condições de captura:** fundo de cor contrastante, distância e luz controladas, câmera fixa; aplicar pré-processamento consistente.
8. **Registro:** guardar imagem e métricas, máscara/overlay quando útil, versão de parâmetro e motivo da classificação.
9. **Validação:** separar imagens de calibração e imagens de avaliação; se for calcular acurácia/precision/recall, comparar com critérios e classes rotulados por avaliação humana consistente.
10. **Limitação:** a proposta é triagem visual externa, não diagnóstico fitossanitário.

## 10. Lógica física e de estados

```text
INICIALIZANDO → PRONTO → FRUTA_DETECTADA → CAPTURANDO
         → ANALISANDO → CLASSIFICANDO → ATUANDO → REGISTRANDO → PRONTO
                             ↘ ERRO → SAÍDAS_SEGURAS → PRONTO/INTERVENÇÃO
```

- Sensor IR deve gerar uma **transição estável** (detecção com debounce). Evitar analisar a mesma fruta repetidamente sem a remoção dela.
- Botão de captura manual no React pode disparar operação enquanto sistema estiver `PRONTO`; caso contrário retornar `409 / ocupado`.
- Estado de erro deve desativar buzzer e levar servo a posição segura, respeitando mecanismo.
- Se SQLite estiver temporariamente indisponível, registrar evento de falha e **não fingir persistência bem-sucedida**.
- Sistema pode oferecer modo de **simulação** para desenvolver frontend/algoritmo sem Raspberry, sem confundir dados simulados com medições reais.

## 11. Implementação por fases (recomendação)

### Fase 0 — Decisões e inventário

- [ ] Confirmar Raspberry Pi 4 ou 5 e Raspberry Pi OS.
- [ ] Confirmar câmera CSI ou USB, sensor IR específico e servo.
- [ ] Confirmar se o servo será **indicador físico** ou **desviador mecânico real**.
- [ ] Definir suporte físico, fundo, luz e posição da laranja.

### Fase 1 — Protótipo da interface React

- [ ] Criar Vite + React + TypeScript.
- [ ] Montar rotas institucionais com os conteúdos do Google Sites.
- [ ] Criar componentes reutilizáveis e tema.
- [ ] Implementar dashboard com dados **mock explicitamente identificados como simulação**.
- [ ] Criar API web somente-leitura + conexão segura ao Neon; React não acessa PostgreSQL diretamente.
- [ ] Conferir versão mobile em larguras pequenas (ex.: 320, 375, 390, 768 px).

### Fase 2 — Serviços locais do Raspberry

- [ ] Instalar Raspberry Pi OS e ambiente Python adequado.
- [ ] Testar sensor, 3 LEDs, buzzer e servo **isoladamente**.
- [ ] Testar câmera e salvar uma imagem.
- [ ] Criar `GET /api/health`, `GET /api/system/status`.

### Fase 3 — Pipeline OpenCV

- [ ] Captura estável, identificação de laranja e segmentação.
- [ ] Extração das 4 métricas.
- [ ] Regras provisórias versionadas e calibração.
- [ ] Salvar amostras anotadas e tratar falhas de segmentação; manter imagens no Pi até existir armazenamento de objetos privado.

### Fase 4 — Persistência e API

- [ ] Criar schemas/migrations **SQLite e Neon PostgreSQL** com UUID comum e versionamento.
- [ ] Gravar análises e caminhos locais das imagens com UUID consistente; montar tabela outbox para eventos pendentes.
- [ ] Implementar API hospedada de leitura do Neon (histórico, resumo, distribuição, detalhe), com filtros validados e segredos no servidor.
- [ ] Conectar React à API web protegida; fornecer status de sincronização e UX de dados desatualizados.
- [ ] Criar sincronizador de outbox, retries e proteção contra duplicatas no Neon.
- [ ] Implementar banco Neon de desenvolvimento e produção separados.

### Fase 5 — Integração física

- [ ] Leitura do sensor aciona uma única análise por fruta.
- [ ] Classificação aciona LEDs/buzzer/servo sem sobrecorrente nem ruído.
- [ ] Worker serializa operações e registra erros.
- [ ] Validar comportamento sem internet, reenvio em reconexão, idempotência e reinicialização segura.
- [ ] Testar falha após commit remoto e antes do ACK local (reenvio sem duplicar).

### Fase 6 — Avaliação e documentação

- [ ] Execução de QA-001 a QA-015 (incluindo Neon, offline e sincronização).
- [ ] Fotos, vídeo do ciclo completo, esquema final e evidências do dashboard.
- [ ] Preencher resultados e limitações com dados observados.
- [ ] Atualizar conteúdo institucional para marcar o que está efetivamente implementado.

## 12. Plano de QA e evidências exigidas

| ID | Teste | Evidência mínima |
|---|---|---|
| QA-001 | sensor IR | foto/vídeo e logs de detecção/remoção |
| QA-002 | câmera | imagem original e log de captura |
| QA-003 | 3 LEDs | foto/vídeo de cada resultado |
| QA-004 | buzzer | vídeo curto da sinalização |
| QA-005 | servo | vídeo dos estados físicos e alimentação correta |
| QA-006 | segmentação | exemplo de imagem + máscara |
| QA-007 | métricas visuais | tabela de valores e imagem associada |
| QA-008 | classificação | conjunto de casos e justificativa de classes |
| QA-009 | SQLite | consulta real da linha salva |
| QA-010 | dashboard React | screenshot com dados reais do Neon, horário da última sincronização e histórico |
| QA-011 | ciclo completo | vídeo sensor→foto→classificação→atuação→SQLite→Neon→dashboard |
| QA-012 | perda de internet | análise continua e SQLite recebe registro pendente |
| QA-013 | reconexão e sincronização | registro é enviado ao Neon; outbox marca sincronizado |
| QA-014 | reenvio idempotente | nova tentativa não duplica UUID/análise no Neon |
| QA-015 | API e credenciais | React não contém segredo do Neon; acesso indevido é bloqueado |

**Indicadores diferentes:**
- `taxa_aprovacao_frutas = aprovadas / total_validas`;
- `taxa_sucesso_qa = testes_aprovados / testes_executados`;
- `acuracia_classificacao` só com **referência rotulada** e metodologia descrita.

## 13. Rastreabilidade: o site promete, o sistema precisa provar

| Item divulgado no site | Componente técnico correspondente | Como comprovar | Estado inicial |
|---|---|---|---|
| Captura de imagens | câmera + driver | imagem real | Planejado |
| Edge Computing | OpenCV no Pi | log sem dependência de cloud | Planejado |
| Cor e regiões anormais | `processor.py` | máscara + valores | Planejado |
| Circularidade/assimetria | `processor.py` | valores e contornos | Planejado |
| Três classes | `classifier.py` | exemplos e regras versionadas | Planejado |
| LEDs, buzzer e servo | `outputs.py` + montagem | vídeo + esquema | Planejado |
| Registro e rastreio | SQLite local + Neon e UUID | consultas locais/remotas conciliadas | Planejado |
| Dashboard | React + API hospedada + Neon | print, horário de sincronização e métricas reais | Planejado |
| Offline/sincronização | SQLite outbox + sincronizador | testes QA-012 a QA-014 | Planejado |
| ODS 2 e agronegócio | fundamentação | referências e contexto | Definido |
| Resultados de desempenho | testes e avaliação | números medidos | Ainda não medido |

> Atualizar a tabela durante o projeto. Não marcar como “implementado” por existir um protótipo de código não testado.

## 14. Sugestões para a experiência React

- Layout visual consistente com o Google Sites, mas com navegação responsiva nativa.
- Dashboard com `TanStack Query` (opcional) para cache/refetch, `Recharts` (opcional) para gráficos; manter dependências pequenas.
- Indicação explícita **“Dados reais do Raspberry Pi”** vs **“Demonstração/simulação”**.
- Exibir último horário de atualização da API e alerta quando offline.
- Fotos/frames responsivos em `width:100%` e `object-fit:contain`.
- Tabela mobile em cartões ou colunas essenciais + botão detalhes; não forçar rolagem de **toda a página**.
- Sem altura fixa em seções/cards; usar layout fluido.
- Rodapé e referências com autoria da equipe e contexto acadêmico.

## 15. Segurança, operação e implantação

- GPIO Raspberry Pi é **3,3 V**; não ligar sinais 5 V diretamente.
- Usar fonte compatível com a placa e alimentação separada adequada para servo/motores.
- Não expor `/api/capture` publicamente; restringir à rede local/autenticação. Evitar abrir portas do roteador para acessar o Pi.
- Nunca permitir URL de imagem arbitrária atravessar diretórios (`../`).
- Backups de SQLite + imagens antes de demonstração; Neon não substitui backup de arquivos locais nem política de retenção.
- Rodar serviços automaticamente via `systemd` **após** testes na bancada; registrar logs e falhas.
- Executar worker com permissões mínimas necessárias; evitar iniciar toda a aplicação com `sudo` sem necessidade.
- Docker é **opcional** e inicialmente desnecessário para facilitar GPIO/câmera. A sincronização deve usar conexões de saída TLS e secrets com permissões restritas.

## 16. Referências úteis de implementação

- Raspberry Pi — documentação de câmera: https://www.raspberrypi.com/documentation/computers/camera_software.html
- Raspberry Pi — instalação da câmera: https://www.raspberrypi.com/documentation/accessories/camera.html
- Picamera2: https://github.com/raspberrypi/picamera2
- OpenCV: https://docs.opencv.org/
- FastAPI: https://fastapi.tiangolo.com/
- React: https://react.dev/
- Vite: https://vite.dev/
- SQLite: https://www.sqlite.org/docs.html
- Neon PostgreSQL: https://neon.com/docs
- PostgreSQL: https://www.postgresql.org/docs/
- ONU ODS 2: https://brasil.un.org/pt-br/sdgs/2

## 17. Prompt para começar com outra IA de programação

> Implemente o projeto OrangeVision descrito neste Markdown, sem inventar dados ou estados de conclusão. Comece pelo monorepo React + TypeScript + Vite, FastAPI no Raspberry Pi, uma API web hospedada de leitura e schemas SQLite/Neon com UUID e outbox. Defina contratos de API, componentes e páginas institucionais. O dashboard deve aceitar dados simulados **explicitamente rotulados** até a API Raspberry estar pronta. O processamento OpenCV, GPIO, SQLite, outbox e worker devem permanecer no Raspberry Pi; os registros sincronizados vão para Neon e o React consulta por API do servidor, nunca diretamente com credenciais. Não usar Arduino. Gere código por etapas, com testes, instruções de execução, interfaces responsivas sem overflow horizontal, e mantenha o checklist de rastreabilidade atualizado. Não prometa diagnóstico de doença ou precisão sem validação real.

## 18. Critérios de aceite da arquitetura híbrida

- [ ] O Pi processa **3 frutas diferentes sem internet** e mantém os 3 registros no SQLite.
- [ ] Ao religar a internet, os registros aparecem no Neon com os mesmos UUIDs e sem duplicatas.
- [ ] Uma segunda sincronização não aumenta artificialmente a contagem.
- [ ] O dashboard público exibe totais coerentes com o Neon e a hora da última sincronização.
- [ ] Frontend publicado não contém segredo do PostgreSQL; apenas funções de servidor acessam o banco.
- [ ] Clicar em "capturar" no site público não controla o Raspberry; o comando existe somente em ambiente autorizado local.
- [ ] Sem imagens na nuvem, o dashboard não publica links quebrados nem URLs locais privadas.
- [ ] Evidências físicas e acadêmicas permanecem consistentes com o que é anunciado no site.

**Status atual desta documentação:** decisões de arquitetura e escopo **definidas**; implementação, esquema elétrico definitivo, medições e resultados **pendentes de validação na bancada**.
