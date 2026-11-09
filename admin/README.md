# OrangeVision Admin — Prisma Studio na Vercel

> O fluxo atual está integrado ao site em `Frontend/`, na rota `/admin/prisma`.
> Para atualizar o projeto Vercel existente, siga [Docs/Prisma_No_Site.md](../Docs/Prisma_No_Site.md).
> Este diretório registra a implementação independente anterior.

Aplicação Next.js independente, em `admin/`, para visualizar o PostgreSQL do Neon.
O frontend público continua em `Frontend/` e a API do site em `web_api/`.

## Acesso

- Login GitHub via NextAuth, com state, PKCE e sessão de até uma hora.
- Apenas o **ID numérico** definido em `ADMIN_GITHUB_ID` é autorizado.
- Autorização verificada na página **e em cada chamada** de `/api/studio`.
- Conexão do banco apenas no servidor, com role exclusiva de leitura.
- O backend rejeita roles com escrita, propriedade, memberships ou privilégios
  administrativos. Consultas executam em transação `READ ONLY`, com timeout.

O Prisma Studio mantém sua interface e branding originais. A interface pode
exibir controles de edição; as escritas são recusadas no servidor e no banco.

## Instalação local

Requisito: Node.js 22.12+ da linha 22.

Na raiz `OrangeVision/`:

```sh
npm --prefix admin ci
```

Copie `admin/.env.example` para `admin/.env.local`, preencha os valores e rode:

```sh
npm --prefix admin run dev
```

Abra <http://127.0.0.1:3001>. Para login local, use uma OAuth App do GitHub com
callback `http://127.0.0.1:3001/api/auth/callback/github`.
Use uma OAuth App diferente da de produção, pois os callbacks têm origens distintas.

## Publicação

Passo a passo, variáveis e configuração do GitHub:
[Docs/Admin_Vercel.md](../Docs/Admin_Vercel.md).

## Validação

```sh
npm --prefix admin test
npm --prefix admin run typecheck
npm --prefix admin run build
```

Integração com PostgreSQL descartável e testes em navegador requerem Docker:

```sh
npm --prefix admin run test:database:docker
```

Para E2E, instale o Chromium uma vez **dentro da pasta `admin/`** com
`npx playwright install chromium`, depois, na raiz:

```sh
npm --prefix admin run test:e2e
```

O runner cria um container `postgres:16-alpine`, portas aleatórias apenas no
loopback, dados fictícios e secrets efêmeros. Encerra o container ao final.
Não usa a URL de produção. O teste de navegador valida sessão, introspecção,
visualização, bloqueio de escrita e logout; o redirecionamento ao GitHub é
interceptado. A troca real de código OAuth depende da sua OAuth App configurada.

## Contrato do endpoint

`POST /api/studio`: sessão válida, `Origin` idêntico a `NEXTAUTH_URL`, JSON até
64 KiB. Suporta apenas a procedure `query` do BFF oficial do Prisma Studio:

```json
{"procedure":"query","query":{"sql":"SELECT 1 AS value","parameters":[]}}
```

Sucesso: `[null, [{"value":1}]]`. Erro: `[{"name":"Error","message":"..."}]`,
sem stack, URL de conexão, SQL ou erro bruto do PostgreSQL. Não habilita batches,
migrations, LLM ou procedures de escrita.

| Status | Significado |
| --- | --- |
| 200 | Consulta concluída |
| 400 | Payload inválido ou procedure não suportada |
| 401 | Sem sessão administrativa válida |
| 403 | Origem externa, operação bloqueada ou role não restrita |
| 413 | Request acima de 64 KiB ou resultado acima de 4 MB |
| 415 | Content-Type não é JSON |
| 422 | Consulta indisponível/não permitida, timeout ou erro de conexão |
| 503 | Configuração incompleta |

Queries parametrizadas usam protocolo PostgreSQL extended, que rejeita múltiplos
statements. Cada consulta abre e descarta sua conexão, com limite de conexão de
5 segundos, execução SQL de 10 segundos e espera por lock de 2 segundos. Dados
privados têm `Cache-Control: no-store`; a CSP restringe conexões do navegador à
própria origem, inclusive chamadas externas do componente incorporado.

## Arquivos principais

- `app/login/`: entrada e estados de configuração/erro.
- `app/page.tsx`: página administrativa protegida.
- `app/ui/studio-view.tsx`: componente Studio, carregado sob demanda.
- `app/api/auth/[...nextauth]/`: OAuth e sessão.
- `app/api/studio/`: BFF protegido para consultas.
- `lib/auth.ts`: allowlist GitHub e configuração da sessão.
- `lib/database.ts`: validação de privilégios e executor de leitura.
- `lib/studio-handler.ts`: contrato HTTP, validação e erros seguros.
- `vercel.json`: build e instalação do projeto separado.
