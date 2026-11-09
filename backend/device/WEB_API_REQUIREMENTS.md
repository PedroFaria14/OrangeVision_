# Dependência: confirmação de identidade/autenticação sem efeitos

## Contrato disponível nesta instalação

`device/api.py` autentica com `Authorization: Bearer <DEVICE_INGEST_CREDENTIAL>`.
As operações disponíveis incluem pareamento, estado de uma inspeção com lease,
heartbeat, envio de fotos, reserva de trabalhos e publicação de resultados.
Nenhuma delas é uma consulta genérica de identidade do equipamento, sem efeitos
e sem inspeção/lease. O código da Web API de referência não está nesta cópia;
`app/` é a API legada, não esse contrato remoto.

Não usar `/health` como prova de credencial ou identidade. Não executar heartbeat,
pareamento, câmera, reserva de trabalhos ou envio para testar a configuração.
O assistente local portanto faz apenas validação sintática e gravação privada;
não tenta descobrir endpoints nem afirma “conectado”.

## Dependência para a Web API

É necessário disponibilizar/documentar uma operação autenticada, somente leitura,
que confirme o UUID canônico do equipamento associado ao Bearer, sem criar ou
alterar equipamento, inspeção, presença/heartbeat, lease, trabalho ou outbox.
A rota e o esquema devem ser definidos no contrato da Web API; nenhum caminho
hipotético foi implementado no cliente.

O contrato deve definir sucesso, credencial inválida/revogada (401), equipamento
sem permissão/inativo (403), indisponibilidade e limites de requisição. Não deve
devolver a credencial. O cliente deverá comparar o UUID confirmado com `DEVICE_ID`
e bloquear divergências, sem trocar a identidade local ou reassociar pendências.
Usar HTTPS com validação TLS e tempos limite; erros não removem os dados locais.

Até existir esse contrato, o estado correto é **configuração salva/disponível,
autenticação ainda não confirmada**. Uma resposta bem-sucedida em uma operação real
confirma aquela operação, não certifica a câmera ou qualidade da fruta.
