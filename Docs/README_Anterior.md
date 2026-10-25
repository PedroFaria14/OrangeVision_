# OrangeVision

## Onde está cada parte

```text
OrangeVision/
  Frontend/     # Site React/TypeScript (Node/Yarn apenas para ferramentas e build)
  web_api/      # Backend do site em Python/FastAPI — serviço online para o Render
  backend/      # Código legado/local reservado ao Raspberry; separado do site
  contracts/    # Contrato OpenAPI da API online
  Docs/         # Especificações e requisitos
```

A API que atende o frontend está em **`web_api/` na raiz**, não em `backend/`.
O site usa a API online para autenticação e dados; não depende de iniciar o Raspberry.

## Rodar localmente

Terminal 1, na raiz **OrangeVision**, com Python 3.12+:

```powershell
python -m venv .venv-web
.\.venv-web\Scripts\Activate.ps1
python -m pip install -r web_api/requirements-dev.txt
python -m uvicorn web_api.main:app --host 127.0.0.1 --port 8001 --reload
```

Se já houver ambiente virtual em `backend/.venv-web`, ele foi preservado e pode ser
ativado a partir da raiz com `.\backend\.venv-web\Scripts\Activate.ps1`.

Terminal 2, na pasta **Frontend**:

```powershell
yarn install --frozen-lockfile
yarn dev
```

Confirme primeiro `http://127.0.0.1:8001/health`. O Vite encaminha `/api` para a porta
8001; conexão recusada/502 significa que o serviço online não está disponível nesse endereço.

## Configuração e publicação

- API: `web_api/.env`, somente no servidor. A conexão real deve ser configurada antes de iniciar.
- Frontend: `Frontend/.env`, somente variáveis públicas. Nunca colocar conexão do banco ali.
- Os `.env` são ignorados pelo Git; exemplos não contêm secrets reais.
- No Render: publicar a **API online**, com a raiz do repositório como diretório de execução,
  build `pip install -r web_api/requirements.txt` e start
  `python -m uvicorn web_api.main:app --host 0.0.0.0 --port $PORT`.
- Segredos de produção ficam nas Environment Variables do Render. Nenhum deploy é automático.

Detalhes de configuração, proxy de produção, migrations manuais e testes:
[API online](web_api/README.md) e [frontend](Frontend/README.md).
O health check não comprova integração com banco real; essa validação continua separada.

## Raspberry compartilhado / inspeções por pessoa

O fluxo opcional está preparado em `web_api`, `Frontend/src/features/inspection` e
`backend/device`. Ele permanece desligado até revisar/aplicar a migration 002, provisionar
o equipamento e configurar câmera/calibração. Nenhuma análise antiga ganha dono automaticamente.

Guia e checklist do que precisa ser feito:
[Docs/Raspberry_Sessoes_Inspecao.md](Docs/Raspberry_Sessoes_Inspecao.md).
