# Publicar o frontend no Vercel e conectar ao Render

Este procedimento vale para as cópias `OrangeVision` e `Orange/OrangeVision_`.
Cada projeto Vercel deve apontar para a pasta `Frontend` do repositório escolhido.

## 1. Configuração do projeto Vercel

| Campo | Valor |
| --- | --- |
| Root Directory | `Frontend` |
| Framework Preset | `Vite` |
| Node.js Version | `24.x` |
| Build Command | `yarn build` |
| Output Directory | `dist` |
| Install Command | `yarn install --frozen-lockfile` |

O `vercel.json` já define framework, build e output. A pasta raiz precisa ser
selecionada no painel. Não selecione `dist` como raiz: a função fica fora do bundle
estático e precisa ser descoberta a partir de `Frontend/api`.

## 2. Variáveis no Vercel

Em **Settings → Environment Variables**, configure para **Production**:

```dotenv
VITE_API_BASE_URL=/api
VITE_API_ENABLED=true
API_PROXY_TARGET=https://orangevision-rs9g.onrender.com
RENDER_API_ORIGIN=https://orangevision-rs9g.onrender.com
```

Para usar Preview, selecione esse ambiente nas quatro variáveis também.
O `.env` privado local não é publicado automaticamente; `.env.example` é apenas
um modelo. Banco, senha e credencial do dispositivo não pertencem ao frontend.

`RENDER_API_ORIGIN` é lida pela função de status durante a execução. Sem ela,
a função aceita `API_PROXY_TARGET` como alternativa, exigindo HTTPS. Um endereço
ausente ou inválido produz HTTP 503 com uma mensagem de configuração.

## 3. O que o roteamento faz

O arquivo `Frontend/vercel.json` aplica esta ordem:

1. Servir arquivos existentes e funções Vercel, incluindo `/api/status/render`.
2. Encaminhar as demais chamadas `/api/...` ao Render, mantendo o prefixo `/api`.
3. Servir `index.html` nas rotas React, como `/login` e `/dashboard/amostras`.

Essa ordem evita encaminhar a função de status para uma rota inexistente do backend.
Erros do backend nas demais rotas `/api/...` não viram páginas HTML da SPA.

**O destino do proxy de produção está explícito em `vercel.json`.**
`API_PROXY_TARGET` configura o proxy do Vite; não substitui automaticamente o
endereço no JSON do Vercel. Se o domínio do Render mudar, atualize o arquivo e
as variáveis antes de publicar novamente.

## 4. Liberar a origem no Render

No serviço da Web API, em **Environment**, configure:

```dotenv
WEB_ENV=production
WEB_ALLOWED_ORIGINS=https://orange-vision.vercel.app,https://orangevision-rs9g.onrender.com
```

Preserve outras origens HTTPS necessárias, separando-as por vírgula. Se outra cópia
for publicada em um domínio diferente, inclua também esse domínio. Não use `/api`
nem uma página específica nessa lista. Domínios Preview precisam de autorização
explícita se forem usados para login.

Mantenha `WEB_DATABASE_URL` no Render. Reinicie/republique a API quando alterar
suas variáveis. O gateway de produção preserva o fluxo HTTPS de cookie e CSRF;
a adaptação de cookie para HTTP do Vite é exclusiva do desenvolvimento local.

## 5. Publicar o código atualizado

Envie as alterações ao repositório/branch conectado ao Vercel e crie um novo
deployment. Apenas cadastrar as variáveis ou republicar uma versão antiga não
cria a função. Em particular, inclua:

```text
Frontend/vercel.json
Frontend/api/status/render.ts
Frontend/server/api-health.ts
```

No deployment publicado, a seção de Functions deve mostrar a função de status.
Depois da publicação, abra:

```text
https://orange-vision.vercel.app/api/status/render
```

Exemplo ilustrativo da resposta:

```json
{
  "state": "available",
  "checkedAt": "2026-10-29T20:00:00.000Z",
  "durationMs": 250,
  "httpStatus": 200
}
```

O HTTP 200 dessa rota significa que a consulta de status foi realizada. A saúde
do Render é indicada por `state` e `httpStatus`: uma consulta bem executada pode
retornar `state: "unavailable"` e `httpStatus: 503` dentro do JSON.

## 6. Comportamento do indicador

- A função consulta somente `/health` da origem HTTPS configurada no servidor.
- Não encaminha cookies, Bearer ou headers de autenticação do visitante.
- Não aceita uma URL de destino por query string; não segue redirects.
- Timeout de 10 segundos e resposta remota limitada a 8 KiB.
- Verifica `status: "ok"` e `service: "orangevision-web"` antes de informar disponível.
- Resultado reutilizado por até 15 segundos por instância; sem cache de navegador/CDN.
- O site atualiza o indicador a cada 60 segundos enquanto a aba está visível e
  oferece o botão **Verificar novamente**.

O health confirma o processo da API, não o banco nem a calibração da laranja.
Processamento de fotos continua dependendo do executor Python autorizado.

## 7. Diagnóstico rápido

| Resultado | Conferir |
| --- | --- |
| Vercel `404 NOT_FOUND` no status | Root Directory, presença da função e versão efetivamente publicada. |
| HTML em vez de JSON no status | Ordem do roteamento; não substituir o `vercel.json` por um fallback SPA genérico. |
| 503 com mensagem de configuração | `RENDER_API_ORIGIN` ou `API_PROXY_TARGET` no ambiente do deployment. |
| JSON com `unavailable` | Código HTTP respondido pelo Render. |
| JSON com `unreachable` | Timeout ou falha de conexão até o Render. |
| JSON com `unexpected` | O serviço não respondeu com o contrato de health esperado. |
| Login com 403 | Domínio do site em `WEB_ALLOWED_ORIGINS` no Render. |
| Sessão com 401 antes do login | Comportamento esperado sem cookie de sessão. |

Build local e verificação de tipagem não substituem a confirmação do novo
deployment no Vercel. Nenhum deploy remoto é executado automaticamente por esses arquivos.
