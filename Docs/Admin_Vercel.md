# Prisma Studio privado na Vercel

> **Integração atual no site existente:** use
> [Prisma_No_Site.md](Prisma_No_Site.md) e a rota
> `https://orange-vision.vercel.app/admin/prisma`.
> O roteiro abaixo documenta a aplicação separada criada anteriormente em `admin/`;
> ele não é necessário para atualizar o projeto Vercel que já publica o OrangeVision.

O código está em **`OrangeVision/admin/`**. Crie um **novo projeto Vercel** para
esse diretório. A autenticação administrativa é independente das contas do site:
somente uma conta GitHub, identificada por ID numérico, poderá consultar o banco.

## 1. Publicar o projeto separado

### Pela CLI, com os arquivos locais desta entrega

Abra um terminal **na pasta `OrangeVision/admin/`**:

```sh
npm ci
npx vercel login
npx vercel --prod
```

Na configuração interativa:

- selecione sua conta/time;
- escolha **criar novo projeto**, em vez de vincular ao site existente;
- nome sugerido: `orangevision-admin`;
- diretório de código: **`.`**, pois o terminal já está dentro de `admin/`;
- framework: **Next.js**;
- Node.js: **22.x**.

A Vercel fornecerá o endereço real. O primeiro deploy pode ser feito antes de
configurar secrets: o painel mostrará configuração pendente e negará consultas.
O endereço ilustrativo `orangevision-admin.vercel.app` não é reservado por este
código; use o domínio realmente atribuído ao seu projeto.

### Pelo painel da Vercel

Se os arquivos já estiverem enviados ao GitHub, importe o mesmo repositório como
**outro projeto** e escolha **Root Directory = `admin`**. Build: `npm run build`;
install: `npm ci`; framework: Next.js. Arquivos locais ainda não enviados ao Git
não aparecem nesse fluxo. A CLI acima publica diretamente a pasta local.

## 2. Criar a OAuth App no GitHub

Entre em <https://github.com/settings/developers> → **OAuth Apps** →
**New OAuth App**. Use o domínio estável de produção obtido no passo anterior:

| Campo | Valor |
| --- | --- |
| Application name | OrangeVision Admin |
| Homepage URL | `https://SEU-DOMINIO-ADMIN` |
| Authorization callback URL | `https://SEU-DOMINIO-ADMIN/api/auth/callback/github` |

Copie o **Client ID** e gere um **Client Secret**. Eles serão configurados no
servidor Vercel. Não coloque o Client Secret em variáveis públicas do frontend.

Obtenha o ID numérico da sua conta em:

```text
https://api.github.com/users/SEU_USUARIO_GITHUB
```

Use o campo **`id`**, não `login`, `node_id` ou e-mail. Outra conta GitHub,
mesmo autenticada com sucesso no provedor, será recusada.

## 3. Configurar a conexão de leitura do Neon

Crie/obtenha uma role exclusiva conforme
[Ferramentas_Locais.md — conexão de leitura](Ferramentas_Locais.md#criar-a-conexão-somente-leitura-no-neon).
Ela precisa de `USAGE` nos schemas consultados e `SELECT` nas tabelas.

O painel valida os privilégios efetivos a cada consulta e recusa:

- usuário proprietário de banco, schema ou objeto de usuário;
- roles administrativas, com BYPASSRLS ou memberships em outras roles;
- permissões de CREATE em banco/schema ou de escrita em tabelas, colunas ou sequências.

Não use a conexão da API, o owner ou uma role criada no painel com permissões
administrativas padrão. A role SQL de leitura do guia local pode ser reutilizada
se satisfizer esses requisitos.

Se o schema `public` conceder CREATE a todos por `PUBLIC`, a validação poderá
recusar a conexão. Peça ao responsável do banco a revisão desse privilégio;
não revogue permissões globais de produção sem avaliar os consumidores.

No Neon, escolha a **branch e o banco corretos** e copie a conexão da role de
leitura, mantendo o TLS (`sslmode=require` ou `sslmode=verify-full`). A URL não é
enviada ao navegador. RLS e permissões do banco continuam valendo.

## 4. Variáveis privadas na Vercel

No projeto **administrativo**, abra **Settings → Environment Variables** e
adicione em **Production**:

| Variável | Valor |
| --- | --- |
| `NEXTAUTH_URL` | `https://SEU-DOMINIO-ADMIN`, sem caminho |
| `NEXTAUTH_SECRET` | Secret aleatório com pelo menos 32 caracteres |
| `GITHUB_CLIENT_ID` | Client ID da OAuth App |
| `GITHUB_CLIENT_SECRET` | Client Secret da OAuth App |
| `ADMIN_GITHUB_ID` | Seu ID numérico GitHub |
| `STUDIO_DATABASE_URL` | Conexão PostgreSQL da role de leitura no Neon |

Para gerar o secret no seu computador:

```sh
openssl rand -base64 48
```

Não use prefixos `NEXT_PUBLIC_` nem `VITE_`. Não envie os secrets no chat ou no
Git. Configure os valores diretamente no painel. Nenhum `.env` real é necessário
no deploy: a Vercel injeta as variáveis de ambiente no servidor.

Em seguida, execute novamente **na pasta `admin/`**:

```sh
npx vercel --prod
```

Ou faça **Redeploy** do projeto no painel. Variáveis novas só entram no próximo
deploy. Não compartilhe secrets de produção com todos os previews. Para preview
autenticado, configure origem, OAuth App e conexão de teste próprias.

## 5. Conferir o resultado

1. Abra a URL de produção e clique em **Entrar com GitHub**.
2. Autorize com a conta correspondente ao `ADMIN_GITHUB_ID`.
3. Selecione um schema e uma tabela no Prisma Studio; use filtros para recortes menores.
4. Confirme que a interface indica **Somente leitura**.
5. Clique em **Sair** e confira que acessar o painel exige novo login.
6. Uma sessão de outra conta deve ser recusada; sem sessão, `/api/studio` não entrega dados.

Os controles genéricos de edição do Prisma podem aparecer, mas escritas são
recusadas pelo backend e pelo PostgreSQL. Não faça alterações reais de produção
como teste. O componente mantém o branding do Prisma conforme a licença.

## Problemas comuns

| Sintoma | Conferir |
| --- | --- |
| Configuração pendente | Seis variáveis de ambiente, secret ≥ 32 caracteres e novo deploy |
| Erro de callback GitHub | Callback exato, HTTPS e mesmo domínio de `NEXTAUTH_URL` |
| Acesso recusado depois do GitHub | `ADMIN_GITHUB_ID` numérico da conta usada |
| Consulta recusada por role | Conta sem escrita, propriedade, CREATE, memberships ou administração |
| Tabela ausente ou acesso negado | Schema, branch Neon, grants SELECT/USAGE e políticas RLS |
| Resultado muito grande | Paginação/filtros menores; limite do painel é 4 MB por resposta |
| Build exibiu o site público | Root Directory precisa ser `admin` no projeto separado |

## Estado da entrega

Implementação e testes locais prontos, incluindo build de produção, PostgreSQL
descartável e navegação real por Chromium. A CLI Vercel estava **desconectada**
durante a preparação. Não houve publicação nem conexão ao banco de produção.
A primeira troca OAuth real e a navegação no Neon ficam para a validação após
configurar suas credenciais e publicar.
