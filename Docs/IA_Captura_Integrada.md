# IA local, captura integrada e diagnóstico da fila

## Entrega e limites

- Detector COCO/orange local, ONNX YOLOX-S oficial do OpenCV Zoo, 35.858.002 bytes,
  verificado por SHA-256. Não exige PyTorch, GPU nem API de IA paga na inferência.
  Foi escolhido um ONNX oficial já exportado; **não é o YOLOX-Nano** discutido
  como candidato. Desempenho no Raspberry precisa ser medido no hardware real.
- Caixa da fruta guia automaticamente o GrabCut; não é necessário desenhar um
  retângulo ou ajustar HSV para obter uma máscara e métricas geométricas iniciais.
- Identificação é exibida como **“modelo sugere laranja”**, com score e versão.
  Score não é acurácia nem qualidade. Ausência de detecção e múltiplas candidatas
  recusam avaliação de qualidade de uma fruta única.
- Cor/regiões anormais continuam indisponíveis sem referências calibradas.
  Categoria/score de qualidade só são emitidos com calibração completa validada
  especificamente para `segmentation_method: yolox-s-grabcut-v1`. Uma calibração
  HSV anterior não é promovida automaticamente para o novo método.
- Tudo continua sendo **amostra experimental**, separado de `analises` e das
  estatísticas oficiais. Não há diagnóstico de doença, comestibilidade ou interior.

## Um comando no Windows

O script utiliza o próprio diretório, independentemente de onde o PowerShell abriu.
Não é preciso ativar `.venv-device` da raiz.

```powershell
powershell.exe -ExecutionPolicy RemoteSigned -File "D:\Estudo_Pedro\USF\Arquitetura\Projeto\Orange\OrangeVision_\Start-OrangeVision.ps1"
```

Ele verifica/inicia a API na 8001, Vite na 5173 e abre uma janela do consumidor
`samples --loop --ai`. Também verifica/instala o modelo oficial fixado por hash e
abre `http://127.0.0.1:5173/dashboard/amostras`. Mantenha as janelas em execução.
Não instala bibliotecas nem encerra servidores de outros processos. Se a API
existente estiver desatualizada, orienta encerrar a janela antiga com Ctrl+C.

Para **câmera integrada**, encerre antes o consumidor anterior e execute:

```powershell
powershell.exe -ExecutionPolicy RemoteSigned -File "D:\Estudo_Pedro\USF\Arquitetura\Projeto\Orange\OrangeVision_\Start-OrangeVision.ps1" -Mode Camera
```

Para iniciar a câmera já em **automático**, use `-Mode Auto`. Se já houver
executor, o script informa a existência, evitando abrir consumidores duplicados.
Feche-o antes de trocar o modo. Para não abrir navegador, acrescente `-NoBrowser`.

## Continuar usando arquivos, mesmo sem fruta física

Envie a imagem em Amostras, escolha o equipamento e clique Enviar para análise local.
O consumidor com IA devolve detecção, caixa e, se a segmentação funcionar, máscara,
circularidade/assimetria. Com detecção/segmentação utilizáveis e sem calibração,
fica **Aguardando avaliação**. Ausência de fruta ou falha de segmentação aparece
como **Não foi possível avaliar**, sem aprovação artificial.

Comandos individuais, na raiz OrangeVision:

```powershell
.\backend\.venv-device\Scripts\python.exe -m backend.device.model_setup
.\backend\.venv-device\Scripts\python.exe -m backend.device samples --loop --ai
```

O modo de arquivos não exige pareamento de inspeção, apenas credencial própria
do equipamento e vínculo do proprietário da amostra.

## Usar a webcam sem seleção manual

Primeiro confirme `backend.device status` e uma sessão pareada dentro do prazo.
Se necessário, crie nova inspeção no site e use `backend.device pair` com o código.
O relógio deve respeitar a tolerância existente de 30 segundos; não houve bypass.

```powershell
.\backend\.venv-device\Scripts\python.exe -m backend.device.inspect --camera 0
```

- **C** ou botão **CAPTURAR**: captura uma fruta detectada e estável.
- **A**: alterna automático. `--auto` inicia assim desde o começo.
- Após capturar, retire a fruta do enquadramento por pelo menos um segundo antes
  de outra captura. Três detecções consistentes e pelo menos 1,2 s de estabilidade
  são condições operacionais iniciais, não limiares de qualidade validados.
- Ao iniciar no automático/headless, deixe primeiro a área vazia por pelo menos
  um segundo. Isso evita recapturar a mesma fruta que permaneceu na frente da
  câmera após um reinício. Depois coloque a fruta normalmente.
- **Q** fecha a câmera. A operação de rede em andamento pode levar até o timeout
  para encerrar; fotos já confirmadas no SQLite permanecem guardadas.
- Se a sessão venceu, feche a câmera com Q, encerre/pareie e abra novamente.
- Resolução solicitada padrão: 640×480; `--width` e `--height` permitem ajustar.
  A resolução real vem do frame adquirido, não é declarada como medição de calibração.

O programa mostra a caixa da detecção e envia **a foto original sem desenhos** ao site;
a máscara produzida pelo processamento fica disponível na galeria.
A câmera integrada já consulta a fila de amostras. Rede e processamento remoto
ficam numa thread separada; o modelo compartilhado tem lock de inferência.

A foto e o ID do comando são persistidos numa tabela própria do SQLite, junto da
sessão original. O upload utiliza Bearer do equipamento e a lease dessa sessão;
o servidor determina o proprietário, mesmo se outra pessoa entrou no navegador.
Reenvio usa o mesmo comando/conteúdo/horário, sem duplicar. Erros permanentes ficam
em quarentena local, sem apagar a foto nem transferi-la para outra conta.

Para retomar fotos pendentes depois de fechar a câmera:

```powershell
.\backend\.venv-device\Scripts\python.exe -m backend.device samples --loop --ai
```

Máximo de 200 fotos locais não sincronizadas/retenções em quarentena; arquivos de
até 5 MiB. O limite de 200 amostras por conta na API continua valendo. Os blobs
locais sincronizados não são apagados automaticamente nesta entrega.
`backend.device status` agora informa também `camera_outbox`, com contagens de
pending/synced/quarantined, sem revelar fotos, códigos ou leases.

## Raspberry sem monitor

Com dependências `requirements-vision.txt`, câmera/credencial configuradas e
modelo instalado no Raspberry (não copiar o venv Windows):

```bash
python -m backend.device.model_setup
python -m backend.device.inspect --camera 0 --headless --auto
```

`--headless` habilita automático e não usa HighGUI. Ctrl+C encerra. A câmera USB
usa OpenCV; CSI depende do adaptador Picamera2 já existente. Configuração física,
cor, foco, desempenho e condições reais de bancada ainda exigem validação local.

## O que mudou no site para evitar “travamento” silencioso

- Equipamento mostra último contato registrado pelo servidor, estado reportado,
  diagnóstico controlado e modelo informado.
- Contato há mais de 30 segundos é **sem contato recente**, não prova de que a
  máquina está desligada. Contato recente também não garante disponibilidade futura.
- Amostra na fila orienta iniciar o consumidor quando nenhum contato foi registrado.
- Reserva em processamento continua com vencimento de 5 minutos e recuperação.
- Detecção/score/caixa são separados da categoria. Nome `Aprovada1.jpg` não é rótulo.
- Um 401 atual de sessão exige login; o consumidor usa credencial separada e não
  é iniciado por selecionar o equipamento no site.

## Banco e contrato

Migration 004 foi autorizada e aplicada: `sample_executors`, `detection`,
`source_inspection_id`, `captured_at`. Não altera análises oficiais existentes.
Em outro ambiente, revisar e aplicar explicitamente após a 003:

```powershell
.\web_api\.venv-web\Scripts\python.exe -m web_api.migrate --migration 004 --apply
```

Extensões aditivas:

- `GET /api/samples/executors`: equipamentos autorizados com contato/estado.
  `/api/samples/devices` preserva seu contrato anterior.
- `POST /api/device/samples/heartbeat`: Bearer, estado, versão de modelo e mensagem.
- `POST /api/device/samples/capture`: Bearer + `X-Inspection-Lease`, query
  `inspection_id`, `request_id`, `captured_at` com offset e corpo binário de imagem.
  Origem/operador vêm da autorização; o horário deve estar na janela autorizada.
  Upload tardio válido conserva dono original, sem aceitar usuário arbitrário.
- Resultados de amostras aceitam evidência opcional `detection`, limitada e
  coerente; caixas são validadas contra as dimensões da imagem.
- Campos novos são opcionais. Digest de resultado antigo sem detecção foi
  preservado, para não quebrar ACKs repetidos de clientes anteriores.

## Evidências e pendências

- Modelo real reconheceu a imagem `Laranja-Seleta.webp` no ensaio local, com score
  aproximadamente 0,90. Isso é um exemplo, não uma estimativa de acurácia.
- As duas amostras que estavam enfileiradas no ambiente do usuário foram
  processadas com IA: detecção e máscara registradas, estado Aguardando avaliação,
  sem categoria inventada. Foi usada API local temporária para esse ensaio; a
  operação contínua depende de manter API e consumidor rodando.
- Ensaio SQL com schemas transitórios/rollback validou heartbeat, resultados de
  detecção, upload autorizado de câmera, isolamento A/B e repetição idempotente.
- Ensaio da janela com câmera/API simuladas e modelo real realizou uma captura,
  persistiu no SQLite e confirmou um envio simulado. Não comprova webcam física.
- Testes cobrem BGR/padding, saída inválida, NMS, estabilidade/retirada, uso sem GUI,
  preservação offline/operador e mensagens/estado do executor na página.
- Ainda faltam ensaio físico no Raspberry, benchmark nele e calibração/referência
  de qualidade. Os três testes PostgreSQL concorrentes antigos continuam opt-in;
  o ensaio SQL de conexão única não os substitui.

Fonte/licença e SHA-256 em `backend/device/models/README.md` e `LICENSE.yolox.txt`.

Validação final desta rodada: **75 testes do executor**, **81 testes da API** e
**65 testes Playwright aprovados**. Os **3 testes PostgreSQL concorrentes**
permanecem skipped sem banco dedicado. Build/TypeScript, ESLint, Prettier e Ruff
aprovados; script PowerShell analisado sem erro de sintaxe. O ensaio SQL inclui
estado de erro com contato recente (não confundido com ausência de contato).
