# Frontends locais usando a API publicada

Para publicar no Vercel, consulte [Deploy do frontend e função de status](DEPLOY_VERCEL.md).

API: **https://orangevision-rs9g.onrender.com**
Swagger: **https://orangevision-rs9g.onrender.com/docs**
OpenAPI: **https://orangevision-rs9g.onrender.com/openapi.json**

O Swagger já existia no FastAPI e foi conferido por GET. Não foi criada uma
documentação duplicada nem houve alteração/deploy da API nesta tarefa.

## Iniciar os dois frontends

Original, com apresentação visual:

```powershell
Set-Location "D:\Estudo_Pedro\USF\Arquitetura\Projeto\OrangeVision\Frontend"
yarn dev
```

Abra **http://127.0.0.1:5173**.

Versão com páginas públicas básicas e dashboard personalizado:

```powershell
Set-Location "D:\Estudo_Pedro\USF\Arquitetura\Projeto\Orange\OrangeVision_\Frontend"
yarn dev
```

Abra **http://127.0.0.1:5174**. Ambos podem rodar ao mesmo tempo. Encerre as
execuções antigas de Vite e reinicie uma vez para carregar configuração/porta.
`strictPort` impede mudar silenciosamente de porta e confundir origens/cookies.

Na cópia nova, a personalização fica somente na área `/dashboard` após o login;
páginas públicas, login e cadastro continuam com HTML básico. CSS Modules isolados,
sem fontes externas ou bibliotecas visuais adicionais.
Os dois consultam o mesmo backend/banco/contas. Cookies no mesmo host não são
isolados por porta: login/logout em 127.0.0.1 podem se refletir no outro frontend.

## Configuração

`VITE_API_BASE_URL` continua **`/api`**. Não coloque a URL externa nessa variável.
O Vite encaminha o caminho completo `/api/...` para o Render.

As URLs são carregadas de `Frontend/.env`, não de `.env.example`:

```dotenv
API_PROXY_TARGET=https://orangevision-rs9g.onrender.com
RENDER_API_ORIGIN=https://orangevision-rs9g.onrender.com
```

`API_PROXY_TARGET` seleciona o destino das chamadas `/api`. Aceita uma origem HTTPS
sem credenciais/caminho; HTTP é aceito apenas em loopback no desenvolvimento local.
`RENDER_API_ORIGIN` seleciona a API remota consultada pelo indicador de status,
por `yarn status:api` e pelos inicializadores remotos. Assim, o indicador continua
consultando o Render mesmo quando `-Local` direciona as chamadas do site à API local.
Na ausência de `API_PROXY_TARGET`, o proxy usa `RENDER_API_ORIGIN`. Na ausência
desta última, o endereço HTTPS de `API_PROXY_TARGET` também pode identificar o Render.
Sem uma origem remota configurada, a inicialização informa erro em vez de usar
um endereço fixo no código.

O Vite também lê `.env.local` e arquivos específicos do modo. Variáveis já
definidas no processo têm prioridade. Após alterar a configuração, reinicie o Vite.

Não é necessário iniciar Uvicorn local para usar os sites com esse destino.
O proxy também está configurado em `vite preview`, ainda como ferramenta local.

## Login e segurança do gateway local

- A API em produção mantém HTTPS, cookie Secure/HttpOnly/SameSite e suas
  verificações de origem/CSRF. Nenhum desses controles foi removido no servidor.
- O gateway aceita Host de loopback e exige a própria origem local em mutações.
  Origem externa, Host externo, requisição cross-site e POST sem Origin são recusados.
- Após essa validação, o gateway representa sua chamada com a origem HTTPS da API,
  compatível com `WEB_ALLOWED_ORIGINS=https://orangevision-rs9g.onrender.com`.
- Apenas `orangevision_session` é encaminhado; cookies de outros apps locais não
  são enviados ao Render. Set-Cookie de outros serviços não é instalado localmente.
- Para o HTTP local, somente o cookie conhecido é convertido para host local sem
  Secure. HttpOnly, SameSite=Lax e Path=/api permanecem. TLS do upstream é verificado.
- Essa adaptação é exclusivamente de desenvolvimento em loopback. **Não publique
  Vite dev/preview como proxy de produção nem exponha esse gateway na rede.**
  Frontend hospedado exige reverse proxy HTTPS próprio, preservando Secure.

## Inicializadores e dispositivo

`Start-OrangeVision.ps1` agora abre **somente o frontend por padrão**, usando
`Start-Remote.ps1`. O script lê a origem remota do `Frontend/.env` e verifica
`/health` antes de abrir a página. Um `-ApiUrl` explícito tem prioridade.
Não inicia nem exige ambiente virtual da API local.

Acrescente `-Mode Samples` para abrir o consumidor ou `-Mode Camera`/`-Mode Auto`
para a câmera. Nesses modos, apenas os processos filhos recebem temporariamente:

- `WEB_API_BASE_URL=https://orangevision-rs9g.onrender.com`
- `WEB_FRONTEND_ORIGIN=http://127.0.0.1:PORTA_DA_COPIA`

Para iniciar somente o executor quando o site já estiver aberto, seu destino é
carregado de `backend/device/.env`:

```dotenv
WEB_API_BASE_URL=https://orangevision-rs9g.onrender.com
ALLOW_INSECURE_LOCAL_API=false
```

Na raiz do projeto:

```powershell
# Remover sobrescritas locais somente deste terminal, para permitir a leitura do .env:
Remove-Item Env:WEB_API_BASE_URL -ErrorAction SilentlyContinue
Remove-Item Env:ALLOW_INSECURE_LOCAL_API -ErrorAction SilentlyContinue
& ".\backend\.venv-device\Scripts\python.exe" -B -m backend.device samples --loop --ai
```

O `.env.example` é apenas um modelo; não é lido automaticamente. Credenciais,
grants e fotos existentes devem ser preservados. O diálogo de pareamento abre a
cópia correta do site. Um executor já aberto não é
reconfigurado por mudar um arquivo; feche-o com Ctrl+C/Q antes de iniciar o modo.
Vários frontends podem abrir, mas os scripts não iniciam dois executores simultâneos.

Exemplo, no repositório original:

```powershell
powershell.exe -ExecutionPolicy RemoteSigned -File "D:\Estudo_Pedro\USF\Arquitetura\Projeto\OrangeVision\Start-OrangeVision.ps1"
```

No outro repositório, use o caminho `Orange\OrangeVision_\Start-OrangeVision.ps1`.
Para consumer/câmera, adicione o modo desejado. Python/IA não são necessários para
abrir somente os frontends; são requisitos dos modos do dispositivo.

## Verificação

`yarn test:proxy` executa uma API simulada e Vite em portas temporárias. Com um
Chromium real, valida login com Set-Cookie de produção, persistência HttpOnly,
sessão e logout. Também verifica origem, Host, CSRF encaminhado e filtragem de
cookies. Esses testes não criam conta nem fazem login com credenciais reais no Render.
As suítes de interface continuam usando fixtures, sem inserir dados fictícios reais.

A integração pública é conferida por chamadas GET anônimas; 401 de sessão sem
cookie é esperado. O login de uma conta real deve ser confirmado pelo usuário.
