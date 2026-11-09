# Ferramentas locais: Prisma Studio e Graphify

Execute os comandos na cópia principal **`OrangeVision/`**. São ferramentas do
computador de desenvolvimento: Prisma Studio consulta o PostgreSQL do Neon e
Graphify cria um mapa do código para consultas mais focadas pelo OpenCode.

## 1. Pré-requisitos

- **Node.js 22.12+ da linha 22**, ou uma versão LTS 24+ compatível com Prisma 7.
  Download: <https://nodejs.org/>.
- **Python 3.10+** e **uv** para o Graphify. O Python do Graphify é independente
  do ambiente Python 3.12+ da API.
- OpenCode para usar a integração do agente.

Verifique em um terminal:

```sh
node --version
npm --version
uv --version
```

Para instalar uv no Linux/macOS, siga <https://docs.astral.sh/uv/getting-started/installation/>.
No Windows, uma opção é `winget install --id=astral-sh.uv -e`.
Abra um novo terminal depois da instalação.

## 2. Prisma Studio: instalação

Na raiz `OrangeVision/`:

```sh
npm --prefix tools/db-studio ci
```

A versão está fixada em **Prisma 7.10.1**, com dependências registradas em
`tools/db-studio/package-lock.json`. O pacote é independente do frontend.
Não é necessário instalar Prisma globalmente, gerar Prisma Client ou criar
`schema.prisma`: o Studio inspeciona o banco existente.

### Criar a conexão somente leitura no Neon

No painel do Neon, selecione o projeto e a **branch de produção correta**.
Peça ao administrador uma role exclusiva de leitura ou crie-a no SQL Editor
usando a conta administradora. O exemplo abaixo é **manual**; os placeholders
precisam ser substituídos localmente antes da execução:

```sql
-- Execute uma vez. Use uma senha única e gerada por gerenciador de senhas.
CREATE ROLE orangevision_reader
  LOGIN PASSWORD 'SUBSTITUA_POR_UMA_SENHA_FORTE'
  NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;

GRANT CONNECT ON DATABASE "NOME_REAL_DO_BANCO" TO orangevision_reader;
GRANT USAGE ON SCHEMA public, orangevision_web TO orangevision_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA public, orangevision_web TO orangevision_reader;

-- Defesa adicional; as permissões SELECT são a restrição efetiva de escrita.
ALTER ROLE orangevision_reader SET default_transaction_read_only = on;
```

Se a role já existir, revise suas permissões com o administrador em vez de
recriá-la. Não use a conta proprietária da API nem conceda outras roles à conta
de leitura. Os grants acima cobrem as tabelas atuais; novas tabelas podem exigir
novos grants revisados. Eles não contornam políticas de RLS existentes.

Os schemas documentados são `public` e `orangevision_web`. Se o ambiente real
for diferente, ajuste os grants com base no inventário daquele banco.

No diálogo **Connect** do Neon, selecione a role `orangevision_reader`, o banco
e a branch corretos e copie a conexão PostgreSQL com TLS. Use-a apenas no `.env`
local. Não envie a conexão no chat, no frontend ou no Git.

### Configurar o arquivo privado

No Linux/macOS, a partir da raiz:

```sh
cp tools/db-studio/.env.example tools/db-studio/.env
chmod 600 tools/db-studio/.env
```

No PowerShell:

```powershell
Copy-Item tools/db-studio/.env.example tools/db-studio/.env
```

Se `.env` já existir, apenas edite-o. Abra o arquivo no editor e substitua o
placeholder pelo endereço copiado do Neon:

```dotenv
STUDIO_DATABASE_URL="postgresql://orangevision_reader:SENHA@HOST_NEON/BANCO?sslmode=require"
```

A URL deve manter o TLS exigido pelo Neon; use a URL fornecida pelo painel,
incluindo seus parâmetros. Senhas com caracteres especiais precisam estar
codificadas na URL. O arquivo é ignorado pelo Git. `WEB_DATABASE_URL` e
`DATABASE_URL` da API não são usados como fallback pelo Studio.

### Abrir o banco

```sh
npm --prefix tools/db-studio run studio
```

Abra **<http://127.0.0.1:5555>** no navegador. Selecione o schema e a tabela
desejada. Para encerrar, pressione **Ctrl+C** no terminal.

O Studio oferece edição na interface; o acesso somente leitura depende das
permissões da role PostgreSQL. Não existe um bloqueio de escrita implementado
apenas por este arquivo de configuração.

Validação inicial: confirme o banco/branch no Neon, abra uma tabela e aplique um
filtro pequeno. Para conferir permissões, conecte o SQL Editor como a role de
leitura e execute (ajuste o nome caso a tabela não exista nesse ambiente):

```sql
SELECT current_user,
       has_table_privilege(current_user, 'public.analises', 'SELECT') AS pode_ler,
       has_table_privilege(current_user, 'public.analises', 'INSERT') AS pode_inserir,
       has_table_privilege(current_user, 'public.analises', 'UPDATE') AS pode_alterar,
       has_table_privilege(current_user, 'public.analises', 'DELETE') AS pode_apagar;
```

O esperado é `pode_ler = true` e as três permissões de escrita `false`. Repita
para as outras tabelas que serão consultadas, sem executar INSERT/UPDATE/DELETE
como teste em produção.

## 3. Graphify: instalação

O nome oficial no PyPI é **`graphifyy`**, com dois `y`. O executável chama-se
`graphify`. A configuração foi validada com **0.9.47**, incluindo suporte SQL:

```sh
uv tool install "graphifyy[sql]==0.9.47"
uv tool update-shell
```

Abra outro terminal e confira:

```sh
graphify --version
```

Se já houver instalação sem o extra SQL, use
`uv tool install --force "graphifyy[sql]==0.9.47"` para reinstalar essa versão
com o extra. Esse comando afeta a instalação da ferramenta no usuário atual.

### Integração com OpenCode

Este repositório já contém:

- `AGENTS.md`: orientações para consultar o grafo antes de explorar muitos arquivos.
- `.opencode/skills/graphify/`: skill e referências distribuídas pelo Graphify.
- `.opencode/commands/graphify.md`: comando `/graphify` com padrão local e sem LLM.
- `.graphifyignore`: exclusões de credenciais, dependências e artefatos.
- As instruções do agente usam `--budget 1500` para limitar cada consulta;
  a versão fixada usa 2000 se o parâmetro for omitido.

**Encerre e reabra o OpenCode dentro de `OrangeVision/`** para carregar a skill e
o comando. Não é necessário executar `graphify install` novamente neste clone.
Não há MCP ou plugin adicional para configurar: as instruções do projeto e o
comando usam a CLI instalada.

### Gerar o grafo pela primeira vez

No terminal Linux/macOS, na raiz:

```sh
GRAPHIFY_BACKEND=none GRAPHIFY_QUERY_LOG_DISABLE=1 graphify extract . --code-only --max-workers 4
GRAPHIFY_BACKEND=none graphify cluster-only . --no-label
```

No PowerShell, na raiz:

```powershell
$env:GRAPHIFY_BACKEND = 'none'
$env:GRAPHIFY_QUERY_LOG_DISABLE = '1'
graphify extract . --code-only --max-workers 4
graphify cluster-only . --no-label
```

Ou use **`/graphify`** no OpenCode após reiniciá-lo. O comando do projeto aplica
esse mesmo padrão sem extração semântica de documentação e sem API de IA.

Saídas locais em `graphify-out/`, ignoradas pelo Git:

| Arquivo | Uso |
| --- | --- |
| `graph.json` | Grafo consultado pela ferramenta |
| `graph.html` | Visualização interativa; abra no navegador |
| `GRAPH_REPORT.md` | Visão geral da arquitetura gerada a partir do grafo |

O HTML usa recursos externos de visualização via CDN; abrir o arquivo pode
exigir internet. A extração AST e as consultas do grafo são locais.

### Consultar e atualizar

Exemplos no terminal, na raiz:

```sh
graphify query "AuthService" --budget 1500
graphify query "QueryService" --budget 1500
graphify explain "AuthService"
```

Use nomes de símbolos do código: a busca local não é um modelo que interpreta
livremente qualquer pergunta em português. A resposta retorna um recorte do
grafo; o agente lê depois os arquivos relevantes para confirmar o comportamento.

Depois de mudanças no código, no Linux/macOS:

```sh
GRAPHIFY_BACKEND=none graphify update .
```

No PowerShell, mantenha `$env:GRAPHIFY_BACKEND = 'none'` e execute
`graphify update .`. Também é possível usar `/graphify --update` no OpenCode.

O grafo inicial inclui Python, TypeScript/TSX e os scripts SQL. A modalidade
`--code-only` não indexa prosa da documentação nem lê dados do banco. Não há
consumo de API de IA para essa extração. A economia de tokens na assistência
depende de consultar recortes úteis em vez de reler o projeto inteiro; não há
percentual garantido.

## 4. Problemas comuns

| Mensagem ou sintoma | Ação |
| --- | --- |
| `Cannot resolve environment variable: STUDIO_DATABASE_URL` | Crie/edite `tools/db-studio/.env` com a conexão de leitura. |
| Falha de autenticação no banco | Confira role, senha codificada na URL, branch, banco e TLS no Neon. |
| Tabelas ausentes no Studio | Confira o schema e os grants SELECT/USAGE da role. |
| Porta 5555 ocupada | Encerre o Studio anterior antes de abrir outro. |
| `graphify: command not found` | Execute `uv tool update-shell` e abra um novo terminal. |
| Grafo ausente ou antigo | Execute a geração inicial ou `/graphify --update`. |
| Graphify avisa sobre `pyproject.toml` sem nós | Na versão validada, esse arquivo de configuração não produz símbolos; isso não impede consultar os arquivos Python. |

## Validação realizada nesta preparação

- Dependências do Prisma instaladas; auditoria npm sem vulnerabilidades reportadas.
- Studio respondeu HTTP 200 e escutou apenas `127.0.0.1:5555`, usando URL fictícia
  sem banco real. O processo de validação foi encerrado.
- Grafo gerado em modo código, com suporte SQL e sem backend de LLM.
- Consulta de autenticação retornou símbolos do frontend e do backend.

**Pendente operacional:** criar/obter a role de leitura, preencher o `.env` e
validar a visualização no Neon. Nenhuma credencial real estava configurada no
clone durante esta preparação.

Fontes: [Prisma Studio](https://www.prisma.io/docs/studio),
[Graphify](https://github.com/Graphify-Labs/graphify) e configuração do próprio projeto.
