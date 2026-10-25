# Amostras privadas — contrato aditivo

Extensão 004: endpoints e campos opcionais de contato/detecção/captura descritos
em `Docs/IA_Captura_Integrada.md` e no OpenAPI versionado. A disponibilidade atual
exige as tabelas das migrations 003 e 004.

Amostras de teste/calibração não são inspeções e não alimentam métricas de produção.
O proprietário vem exclusivamente da sessão autenticada. A API guarda imagens;
o dispositivo autorizado processa arquivos, sem exigir fruta física/câmera.

## Navegador (cookie de sessão; mutações também exigem Origin + X-CSRF-Token)

- `GET /api/samples/config`: enabled, max_upload_bytes, processing="device".
- `GET /api/samples/devices`: equipamentos autorizados para o usuário.
- `POST /api/samples?request_id=<UUID>&filename=<nome>`: corpo binário
  application/octet-stream, até 5 MiB, conteúdo JPEG/PNG/WebP válido, até 16 MP.
  Normaliza orientação, remove metadados e guarda JPEG de até 1600 px por lado.
  Idempotência por usuário/request_id e SHA-256 do arquivo original; conflito 409.
- `GET /api/samples?limit=20&offset=0`: items e total, somente do proprietário.
- `GET /api/samples/{id}/image` e `/mask`: imagem/máscara privadas, nunca URLs públicas.
- `POST /api/samples/{id}/queue` com `{device_id}`: verifica vínculo atual, enfileira
  e limpa resultado anterior. Repetir na mesma fila é idempotente; processamento
  com lease válida recusa reatribuição (409).

## Executor (Bearer DeviceCredential, sem cookie/senha do usuário)

- `POST /api/device/samples/claim` com `{claim_id, lease_token}`: uma amostra da fila
  destinada ao equipamento e cujo proprietário ainda autoriza seu uso; retorna
  metadados ou null. Reserva de 5 minutos; reservas vencidas podem ser retomadas.
  Repetir a mesma claim e token recupera a reserva ainda válida.
- `GET /api/device/samples/{id}/image`, header `X-Sample-Lease`: download limitado
  ao arquivo reservado por esse equipamento, enquanto a reserva é válida.
- `POST /api/device/samples/{id}/result`, mesmo header e corpo `{claim_id,state,
  reason,metrics?,classification?,calibration_version?,algorithm_version?,
  calibration_validated,mask_base64?}`. Máscara opcional PNG binária nas mesmas
  dimensões da imagem normalizada. Mesmo resultado/claim é idempotente; resultado
  divergente ou reserva reatribuída é conflito, nunca sobrescreve resultado atual.

## Estados persistidos

`received` (Imagem recebida) → `queued` (Aguardando análise) → `processing`
(Em análise) → `awaiting_review` (Aguardando avaliação), `completed` (Concluída),
`not_evaluable` (Não foi possível avaliar) ou `failed` (Falha no processamento).

`completed` exige categoria e métricas completas, versão de calibração e declaração
de calibração validada pelo dispositivo confiável. Rascunhos não podem fornecer
categoria ou score. Erros técnicos não são a categoria Revisar. Ausências são null.
O site mostra apenas estados conhecidos do servidor, nunca presume envio offline.

Reenvio de resultado é seguro; após reinício/lease vencida o processamento de um
arquivo pode ser repetido. Não há atuação física nem criação de análises oficiais.

## Armazenamento e ativação

Migration manual `003_image_samples.sql`, sem alteração de tabelas de análises.
Original normalizado e máscara são bytea privados no PostgreSQL (MVP limitado a
200 amostras por conta). Listagens não retornam binários, tokens ou hashes.
Sem migration a configuração informa enabled=false. Banco indisponível continua
erro 503, não é confundido com galeria vazia. Futuro volume maior pede object storage.
