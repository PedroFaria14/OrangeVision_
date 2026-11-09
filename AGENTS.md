# OrangeVision — contexto para agentes

## Ferramentas locais

- Execute comandos a partir da raiz `OrangeVision/`.
- Use Graphify apenas em modo local de código. Para gerar o grafo:
  `GRAPHIFY_BACKEND=none GRAPHIFY_QUERY_LOG_DISABLE=1 graphify extract . --code-only --max-workers 4`.
- Para atualizar após mudanças: `GRAPHIFY_BACKEND=none graphify update .`.
  No PowerShell, defina `$env:GRAPHIFY_BACKEND = 'none'` antes do comando.
- Não faça extração semântica de documentação/mídia nem configure provedores de LLM
  sem solicitação explícita. O fluxo padrão não consome API de IA.
- Consulte o grafo com termos dos símbolos do código e orçamento pequeno
  (`graphify query "AuthService" --budget 1500`); confirme os trechos relevantes
  no código antes de editar. Um grafo pode estar incompleto ou desatualizado.
- Credenciais e dados reais do banco não fazem parte do grafo. Prisma Studio usa
  `tools/db-studio/.env` com conexão exclusiva de leitura; não reutilize a conta da API.
- Guia de instalação e operação: `Docs/Ferramentas_Locais.md`.
- O Prisma web atual fica em `Frontend/`, rota `/admin/prisma`, com funções em
  `Frontend/api/admin/` e código privado em `Frontend/server/admin/`.
  Consulte `Docs/Prisma_No_Site.md`. O diretório `admin/` é a implementação
  independente anterior; não substitua o Root Directory do projeto Vercel atual.

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

When the user types `/graphify`, use the installed graphify skill or instructions before doing anything else.

Rules:
- For codebase questions, first run `graphify query "<question>" --budget 1500` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- Dirty graphify-out/ files are expected after hooks or incremental updates; dirty graph files are not a reason to skip graphify. Only skip graphify if the task is about stale or incorrect graph output, or the user explicitly says not to use it.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `GRAPHIFY_BACKEND=none graphify update .` to keep the graph current (AST-only, no API cost).
