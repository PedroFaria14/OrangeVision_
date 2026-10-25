# OrangeVision — versão funcional

Projeto na raiz do repositório `Orange\OrangeVision_`. O frontend é React com
HTML nativo: **páginas públicas, login e cadastro sem personalização; área
`/dashboard` personalizada após o login**. O painel utiliza menu lateral grafite,
ações laranja, indicadores e tabelas responsivas. Estilos isolados em CSS Modules,
sem MUI/Emotion ou dependências visuais adicionais.

## Estrutura

- `Frontend/`: login/cadastro, perfil, dashboard, histórico/detalhe, inspeções,
  upload/galeria de amostras e estados de processamento.
- `web_api/`: API online FastAPI, autenticação, autorização, migrations e consultas.
- `backend/device/`: executor local, câmera, detecção ONNX, revisão das fotos e filas.
- `backend/app/` e demais arquivos legados: preservados da origem; não são o
  entrypoint da API online atual.
- `contracts/`: OpenAPI e contratos de integração.
- `Docs/`: guias técnicos e registros históricos.
- `calibracao-local/`: imagens locais copiadas; não publicadas no Git.

## Abrir no Windows

O frontend original usa a porta 5173; esta cópia usa a 5174. Os dois podem abrir
simultaneamente. Encerre o Vite anterior desta cópia antes de reiniciar o script;
ele recusa portas ocupadas e não encerra processos automaticamente.

```powershell
powershell.exe -ExecutionPolicy RemoteSigned -File "D:\Estudo_Pedro\USF\Arquitetura\Projeto\Orange\OrangeVision_\Start-OrangeVision.ps1"
```

Por padrão, o script abre somente o site em **http://127.0.0.1:5174** e usa a API
**https://orangevision.onrender.com**, sem iniciar Uvicorn local.
Swagger: **https://orangevision.onrender.com/docs**.
Para o consumidor: `-Mode Samples`; câmera: `-Mode Camera`; automático: `-Mode Auto`.
Use sempre a mesma origem no navegador para manter o cookie de sessão. Portas
diferentes no mesmo host compartilham cookies, contas e banco remoto.

### Comandos separados

Para abrir apenas o site, na pasta `Frontend`:

```powershell
yarn dev
```

O proxy mantém `VITE_API_BASE_URL=/api` e tem o Render como destino padrão.
Configuração e modos do dispositivo: [Frontends e API Render](Docs/FRONTENDS_API_RENDER.md).

## Dependências em uma instalação nova

Os ambientes virtuais desta máquina foram recriados no caminho novo, com as
versões instaladas na origem. Em outra máquina, configure os `.env` a partir
dos exemplos e instale as dependências:

```powershell
py -3.12 -m venv web_api/.venv-web
.\web_api\.venv-web\Scripts\python.exe -m pip install -r web_api/requirements-dev.txt
py -3.12 -m venv backend/.venv-device
.\backend\.venv-device\Scripts\python.exe -m pip install -r backend/device/requirements-lab.txt pytest ruff
.\backend\.venv-device\Scripts\python.exe -m backend.device.model_setup
```

Na pasta `Frontend`: `yarn install --frozen-lockfile`.
No Raspberry sem interface, use `requirements-vision.txt` em vez da variante
com janelas. Não copie o venv Windows para Linux. Não instale simultaneamente
as variantes GUI e headless do OpenCV no mesmo ambiente.

## Configuração e dados

As configurações privadas e o banco SQLite foram copiados localmente. O banco
PostgreSQL remoto continua o mesmo; esta transferência não executou migrations,
provisionamento ou mudança de proprietários. O backup SQLite inclui grants,
tentativa de pareamento, filas e a foto pendente existente no momento da cópia.

`.env`, imagens pessoais, SQLite, pesos ONNX e ambientes virtuais são ignorados
pelo Git. O código de `backend/device` agora é versionável neste repositório;
a pasta inteira não é mais ignorada. O `.git` e o remoto de destino foram preservados.
Nenhum commit ou push é feito pela transferência.

## Verificação

```powershell
.\backend\.venv-device\Scripts\python.exe -m pytest backend/device/tests -q
.\web_api\.venv-web\Scripts\python.exe -m pytest web_api/tests -q
```

Na pasta `Frontend`:

```powershell
yarn build
yarn lint
yarn test:proxy
yarn test:e2e --workers=2
```

Os testes de interface usam contratos interceptados somente no navegador de
teste; não inserem dados fictícios na conta real. Os testes PostgreSQL concorrentes
continuam opt-in e exigem banco dedicado.

## Estado do projeto

A transferência preservou o código atual da câmera/IA, inclusive os ajustes em
andamento. Não é uma declaração de homologação do hardware ou da classificação.
Os testes SQL de recuperação de foto da rodada anterior foram interrompidos;
esta tarefa não retomou esse trabalho nem modificou o banco remoto para validá-lo.
Categorias de qualidade ainda exigem calibração realmente validada.

Leia `Docs/TRANSFERENCIA_ORANGE.md` para escopo e resultados da transferência.
Essa transferência foi inicialmente sem CSS; a personalização posterior ficou
restrita à área logada, conforme a nova solicitação.
Guias anteriores em `Docs` são registros técnicos/históricos e podem mencionar
a apresentação visual antiga. `Docs/README_Anterior.md` preserva o README da origem.
