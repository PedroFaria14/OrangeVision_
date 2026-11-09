# Pipeline mínimo do Raspberry

Captura local serial, OpenCV com calibração explícita, SQLite/outbox e sincronização HTTPS.
Sem contas web, senha do Neon, FastAPI local obrigatório ou GPIO obrigatório.

Guia principal: **[Docs/Raspberry_Sessoes_Inspecao.md](../../Docs/Raspberry_Sessoes_Inspecao.md)**.
Ele descreve o que já existe, o que falta na bancada, configuração, pareamento, operação,
tratamento offline e testes. Não confundir este pipeline com `backend/app` legado.

No Pi, a partir de `OrangeVision/backend`, com ambiente separado:

```bash
python3 -m venv .venv-device
source .venv-device/bin/activate
python -m pip install -r device/requirements.txt
```

Configure os valores reais emitidos em **Equipamentos** com `python -m device configure`.
Não é necessário editar `device/.env` manualmente. Para câmera/processamento,
confirmar USB/CSI, bibliotecas do SO e calibração conforme o guia antes de instalar visão.
O exemplo de calibração não é operacional e impede classificar sem configuração validada.

```bash
python -m device pair
python -m device run
# Em outro terminal/pasta/ambiente iguais:
python -m device sync --loop
python -m device status
```

A aplicação da migration 002, o provisionamento e a ativação da API são manuais. O software
foi verificado com SQLite, mocks e imagens sintéticas; a câmera física ainda precisa ser validada.

## Janela da câmera (Raspberry com monitor)

Instale `device/requirements-lab.txt` no ambiente usado para executar a câmera.
Não misture `opencv-python` e `opencv-python-headless` no mesmo ambiente.

```bash
app/.venv/bin/python3 -m device.inspect --camera 0
```

- **C / Capturar**: aguarda um novo quadro analisado e salva essa mesma imagem para revisão.
- **U / Usar foto**: confirma a autorização e coloca a imagem na fila de envio.
- **R / Tirar outra**: descarta explicitamente apenas a foto em revisão.
- **P / Sessão**: mostra o pareamento válido, oferece retomar uma tentativa pendente ou pede código.
- **A / Modo**: alterna manual/automático. **Q** ou fechar a janela encerra a câmera.

O painel escuro separa autorização local, envio e análise. “Recebida pelo servidor”
só aparece depois da resposta válida ao upload; não garante que o navegador já atualizou.
Os contadores da fila são atualizados aproximadamente a cada segundo. Fotos retidas
precisam de revisão de autorização/limite; falhas transitórias preservam a fila para nova tentativa.
A falha no heartbeat é informada, mas não impede uma tentativa independente de envio.

**Última análise / amostra** identifica a amostra pelo ID; ela não representa a fruta
ao vivo. Só mostra APROVADA/ATENÇÃO/REVISAR quando o processamento tem calibração
validada e confirmação do servidor. Sem isso, mostra qualidade não avaliada ou falha.
Não é uma garantia de segurança alimentar.

No Pi 4, a detecção fica em segundo plano, com no máximo um quadro pendente e intervalo
mínimo de 0,5 s entre inícios de inferência (não garante 2 inferências/s). A captura usa
a imagem e a detecção correspondentes, e a estabilidade automática conta somente resultados
novos. O vídeo ao vivo não desenha uma caixa antiga sobre uma imagem diferente; a caixa
é mostrada na foto em revisão. Resultados antigos e falhas de IA não liberam captura.

## Assistente do equipamento e rotação da credencial

Execute os comandos na pasta que contém `device/` e `app/`. Nesta instalação apenas
o conteúdo de `backend/` foi copiado para o Raspberry; **não** use `backend.device`.

```bash
# Configurar os dados do equipamento que JÁ existe no site:
app/.venv/bin/python3 -m device configure
# Equivalente pelo lançador:
./start.sh configurar

# Atualizar apenas a credencial depois de rotacioná-la no site:
app/.venv/bin/python3 -m device update-credential
# Equivalente:
./start.sh atualizar-credencial

# Iniciar normalmente; configuração completa é reutilizada:
./start.sh
# Ou iniciar diretamente a janela:
app/.venv/bin/python3 -m device.inspect --camera 0
```

O assistente solicita somente campos ausentes/inválidos: `DEVICE_ID` (UUID do site),
`WEB_API_BASE_URL` (origem HTTPS da API, sem `/api` ou `/docs`) e
`DEVICE_INGEST_CREDENTIAL` (credencial privada, sem escrever `Bearer`). A entrada
da credencial é oculta e o envio usa `Authorization: Bearer ...`. Não é criado outro
equipamento nem gerado um novo UUID. Não confunda a origem da API com a URL do frontend.

Na câmera iniciada diretamente em um terminal interativo, dados ausentes abrem o
diálogo local Tkinter já usado pelo pareamento. A CLI e o lançador usam o terminal.
Ctrl+C, fim da entrada, o botão Cancelar ou a palavra `cancelar` antes da gravação
abandonam o assistente sem salvar campos parciais. Sem terminal interativo, configuração
ausente gera orientação e erro de saída, sem aguardar entrada nem abrir diálogo.
Configuração completa funciona sem terminal. O comando
`python -m device configure --if-needed` apenas confere/reutiliza os dados locais,
solicitando campos somente se necessário e houver terminal.

O arquivo `device/.env` é salvo por substituição atômica com permissão `0600`, sem
alterar ajustes de câmera, modelo, calibração ou caminho do banco. Variáveis de ambiente
continuam tendo precedência. Se a credencial vier do ambiente, a atualização local é
recusada com orientação para atualizá-la na origem; não será salvo um valor ignorado.
Reinicie os executores após a rotação: processos já abertos conservam a credencial antiga.
Links simbólicos e alterações concorrentes detectadas no arquivo são recusados.

A inicialização operacional registra no SQLite um vínculo `device_identity` com UUID
e origem da API. Vínculos/histórico incompatíveis bloqueiam a execução, sem transferir
sessões ou pendências. A configuração também compara as variáveis herdadas com a
identidade local. **Não troque o UUID, API ou banco para contornar um erro**: recupere
a configuração original. Em uma base antiga sem referência confiável de identidade,
o programa pode exigir recuperação em vez de adivinhar o equipamento. Não há migração
automática entre equipamentos ou APIs.

O assistente não acessa a rede, não inicializa SQLite, não abre câmera, não pareia
inspeção e não consome trabalhos. Após salvar ele informa **“autenticação ainda não
confirmada”**. Falta no contrato um endpoint autenticado de identidade sem efeitos;
veja [WEB_API_REQUIREMENTS.md](WEB_API_REQUIREMENTS.md). `/health` não resolve isso.
Nas operações reais, falha de rede, HTTP 5xx (API indisponível), HTTP 401 (credencial
recusada) e HTTP 403 (permissão recusada) são informados separadamente. Esses erros
não apagam a configuração nem reabrem o cadastro; a verificação TLS permanece ativa.

### Qualidade da fruta

A janela agora usa também `CALIBRATION_PATH` quando `--calibration` não é passado.
Caminhos relativos de `CALIBRATION_PATH` são relativos a `device/`. Uma calibração
explicitamente passada na linha de comando tem precedência:

```bash
./start.sh --calibration /caminho/para/calibracao-validada.json
```

O arquivo precisa ser validado com fotos reais para `yolox-s-grabcut-v1` e aceito por
`CalibratedVision`. `calibration/calibration.json` desta instalação é **provisório**, tem
outro formato e não é promovido automaticamente a calibração válida. Simplesmente
esperar a fruta parada ou cadastrar o equipamento não habilita “boa/ruim”.

## Avaliação e confirmação de registro no histórico

A tela separa detecção ao vivo, qualidade da **última amostra**, envio da foto e
registro no histórico. O botão **Detalhes [I]** (ou a tecla I, inclusive em revisão)
mostra o motivo, o UUID completo da amostra, o `analysis_id` e o estado de confirmação.
Use **[** e **]** no painel de detalhes para navegar motivos longos.
Esses resultados não representam automaticamente a fruta que está ao vivo na câmera.

**“Recebida pela API” não significa “incluída nos gráficos”.** O registro só é mostrado
como confirmado quando uma resposta da API traz `analysis_id` válido para a amostra.
Sem esse campo, a qualidade/motivo continuam disponíveis, mas o registro não é afirmado.
A visibilidade nos gráficos ainda depende de período, filtros e atualização do site.

O resultado e a confirmação ficam no SQLite e são recuperados ao reiniciar. Uma
resposta perdida mantém **confirmação pendente**, sem concluir que a API não recebeu.
O executor retoma a mesma reserva/payload no endpoint de resultado já existente;
não há um segundo envio via ingestão de análises. Reservas recusadas permanecem
pendentes, sem inventar uma consulta ou reconciliação que não existe no contrato local.
Veja [SAMPLE_SYNC.md](SAMPLE_SYNC.md) para limites e compatibilidade.

Na segmentação por IA, uma seleção apertada pode receber até duas ampliações de margem
somente quando o contorno chega ao limite do recorte. A proteção continua ativa:
detecção na borda da foto ou falha persistente não produz categoria. Essas mudanças
devem ser verificadas com as fotos reais e a calibração da sua bancada antes de confiar
nas categorias; os testes automatizados são sintéticos.

## Acompanhamento das avaliações pela Web API

A tela mostra, separadamente e por amostra: detecção da fruta, avaliação local,
estado do Gemini, resultado adotado e comparação. Nada disso substitui a avaliação
local. O cartão **WEB API / GEMINI** resume o estado; em **Detalhes [I]**, a tecla **]**
avança até a página com captura local, amostra remota, sessão de origem e justificativas.

A consulta é somente leitura, usa a lease da sessão de origem e não agenda Gemini.
Não instale SDK Gemini nem coloque `GEMINI_API_KEY` no Raspberry. Veja os limites em
[SAMPLE_SYNC.md](SAMPLE_SYNC.md).
