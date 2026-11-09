# Prisma no OrangeVision já publicado

## Endereço

Depois de publicar estas alterações no **projeto Vercel atual**:

**<https://orange-vision.vercel.app/admin/prisma>**

O código está integrado ao `Frontend/` existente. Mantenha o Root Directory,
framework Vite, build `yarn build` e saída `dist` usados pelo site atual.
Não é necessário criar outro projeto Vercel nem publicar a pasta `admin/`.

## 1. Enviar e publicar as alterações

Envie as alterações para a branch conectada ao projeto atual e acompanhe o
deployment na Vercel. Inclua os arquivos novos, `Frontend/package.json`,
`Frontend/yarn.lock`, `Frontend/vercel.json`, `Frontend/vite.config.ts` e a rota
React. Alterações somente na pasta antiga `admin/` não publicam essa integração.

Se o deploy for bloqueado por autoria, verifique se o autor do commit está
associado à conta GitHub conectada ao proprietário do projeto Vercel.

Após um build bem-sucedido, `/admin/prisma` mostra a tela administrativa. Sem as
variáveis privadas, ela exibe instruções de configuração; não tenta liberar o banco.

## 2. Configurar o GitHub OAuth

No GitHub, abra **Settings → Developer settings → OAuth Apps**:
<https://github.com/settings/developers>.

Crie uma OAuth App ou atualize a que já criou para o painel:

| Campo | Valor |
| --- | --- |
| Homepage URL | `https://orange-vision.vercel.app` |
| Authorization callback URL | `https://orange-vision.vercel.app/api/admin/auth/callback/github` |

**O callback da integração atual é `/api/admin/auth/callback/github`.** Se você
configurou anteriormente `/api/auth/callback/github` para a aplicação separada,
atualize o endereço. Esse novo prefixo não conflita com o login do site no Render.

Copie o Client ID e gere o Client Secret. Obtenha o **ID numérico** da conta
autorizada no campo `id` de `https://api.github.com/users/SEU_USUARIO_GITHUB`.
O painel autoriza apenas esse ID, mesmo que outra conta consiga autenticar no GitHub.

## 3. Variáveis no projeto Vercel existente

Em **Settings → Environment Variables**, adicione em **Production**:

| Variável privada | Valor |
| --- | --- |
| `NEXTAUTH_URL` | `https://orange-vision.vercel.app` — somente a origem, sem `/admin/prisma` |
| `NEXTAUTH_SECRET` | Secret aleatório com pelo menos 32 caracteres |
| `GITHUB_CLIENT_ID` | Client ID da OAuth App |
| `GITHUB_CLIENT_SECRET` | Client Secret da OAuth App |
| `ADMIN_GITHUB_ID` | Seu ID numérico do GitHub |
| `STUDIO_DATABASE_URL` | URL PostgreSQL da role de leitura do Neon com TLS |

Para gerar o secret no computador: `openssl rand -base64 48`.
Não use prefixo `VITE_` para essas variáveis: variáveis `VITE_*` são públicas.
Preencha os secrets diretamente na Vercel, sem enviá-los no chat ou ao Git.

As variáveis de produção já existentes, como `RENDER_API_ORIGIN`, continuam
necessárias conforme a configuração atual do site. Depois de salvar, faça
**Redeploy**: variáveis novas só entram no próximo deployment.

Use o domínio real caso ele mude. Previews devem ter uma OAuth App, origem e
conexão de teste próprias; não compartilhe automaticamente secrets de produção.

## 4. Conexão de leitura do Neon

Use uma role exclusiva com `USAGE` nos schemas e `SELECT` nas tabelas desejadas.
Passos e SQL de criação:
[Ferramentas_Locais.md](Ferramentas_Locais.md#criar-a-conexão-somente-leitura-no-neon).

O servidor valida as permissões a cada consulta e recusa roles com:

- propriedade de banco, schema ou objeto de usuário;
- privilégios administrativos, BYPASSRLS ou memberships em outras roles;
- CREATE em banco/schema, escrita em tabelas/colunas ou uso de sequências de escrita.

Não reutilize a conta da API ou o owner. Mantenha `sslmode=require` ou
`sslmode=verify-full` na conexão do Neon. RLS e permissões do banco continuam valendo.
Se o schema público conceder CREATE a `PUBLIC`, o responsável pelo banco precisa
revisar esse privilégio antes de usar o painel; não altere grants globais sem avaliar o impacto.

## 5. Conferir

1. Abra `/admin/prisma` e confira que a página existe.
2. Clique em **Entrar com GitHub** e use a conta autorizada.
3. Selecione um schema e uma tabela no Studio.
4. Use filtros e paginação para recortes menores.
5. Clique em **Sair do painel**. O login normal do OrangeVision é independente.

O Studio mantém sua interface e branding oficiais. Alguns controles genéricos
de edição podem aparecer, mas escritas são recusadas no servidor e no PostgreSQL.
Não faça alterações reais de produção como teste.

## Execução local

Na pasta `Frontend/`, instale com `corepack yarn install --frozen-lockfile`.
Configure as variáveis privadas em `.env.local`, ignorado pelo Git, usando:

```dotenv
NEXTAUTH_URL=http://127.0.0.1:5173
```

Use uma OAuth App local com callback
`http://127.0.0.1:5173/api/admin/auth/callback/github`, preencha as outras variáveis
e execute `corepack yarn dev`. Acesse `http://127.0.0.1:5173/admin/prisma`.
O plugin de desenvolvimento atende `/api/admin/*` localmente antes do proxy do Render.

## Organização técnica

- `Frontend/src/features/admin-prisma/AdminPrismaPage.tsx`: rota e login.
- `Frontend/admin-prisma.html`: entrada isolada do Studio para não aplicar seu CSS ao site.
- `Frontend/api/admin/auth.ts`: função Vercel de OAuth/sessão.
- `Frontend/api/admin/studio.ts`: função Vercel que executa consultas autenticadas.
- `Frontend/server/admin/`: configuração privada, Auth.js e executor PostgreSQL de leitura.
- `Frontend/vercel.json`: reserva `/api/admin/*` antes do proxy geral `/api/*` do Render.

O login GitHub usa state, PKCE, CSRF e cookies HttpOnly/SameSite, Secure em HTTPS.
O cookie administrativo tem Path `/api/admin`, portanto não acompanha as chamadas
de usuários a `/api/auth/*` no Render. A página renova a verificação da sessão a
cada 30 segundos; cada consulta também é autorizada no servidor.

O endpoint `POST /api/admin/studio` implementa a procedure `query` do BFF oficial
do Prisma. Usa protocolo extended (um statement), transação READ ONLY, timeout
SQL de 10 segundos, limite de request de 64 KiB e resultado de 4 MB. Não expõe
migrations, batches, escrita ou LLM. Erros não retornam SQL, parâmetros, stack ou
URL do banco. Respostas privadas não são armazenadas em cache.

## Testes

Na pasta `Frontend/`, com `RENDER_API_ORIGIN` configurada conforme o ambiente:

```sh
corepack yarn build
corepack yarn test:functions
corepack yarn lint
corepack yarn test:proxy
corepack yarn test:admin
corepack yarn test:admin:database
corepack yarn test:admin:e2e
corepack yarn test:admin:unconfigured
```

Os três últimos comandos usam PostgreSQL descartável em Docker, apenas no loopback,
e o E2E requer Chromium (`corepack yarn playwright install chromium`). Não usam o
banco de produção. Testes de OAuth interceptam o redirect antes da rede externa;
a troca real com o GitHub e o Neon precisa ser conferida após configurar o deployment.

### Validação das funções publicadas

O build também emite `api/` e `server/` como JavaScript Node/ESM, carrega os três
entrypoints sem loader TypeScript e verifica respostas de sessão, Studio e status
com configuração sintética. Não acessa banco, GitHub ou Render reais e remove os
artefatos temporários ao terminar. Esse gate pode ser executado isoladamente com
`corepack yarn test:functions`.

Os imports relativos nas funções usam extensão `.js`, mesmo quando o fonte é
`.ts`, para corresponder aos módulos emitidos. Não troque esses imports por `.ts`:
o Node do deployment não encontrará o arquivo TypeScript no pacote compilado.
O Vite/tsx resolve o fonte local, por isso testes somente em preview não detectam
necessariamente esse erro.

Se os logs mostrarem `ERR_MODULE_NOT_FOUND` procurando `server/... .ts` a partir
de `api/... .js`, publique a correção dos imports e faça um novo deploy. Depois
confira no deployment: `GET /api/admin/studio` deve responder 405 e, com o login
configurado, `/api/admin/auth/session` deve retornar JSON de sessão. Essas
verificações não substituem a validação do OAuth real e da conexão de leitura.

Se a página ainda disser “Página não encontrada”, confira se o deployment contém
os arquivos novos de `Frontend/`. Se mostrar configuração pendente, confira as seis
variáveis e faça Redeploy. Se o login voltar com erro, confira o callback e o ID.
