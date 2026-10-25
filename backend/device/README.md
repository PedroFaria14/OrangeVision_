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

Preencher `device/.env` com valores reais de `.env.example`. Para câmera/processamento,
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
