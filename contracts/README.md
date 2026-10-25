# Contrato da API online

`web-openapi.yaml` corresponde aos schemas HTTP de `web_api/contracts.py` e às rotas online.
Não corresponde à API legada do Raspberry (`app.main`).

Regenerar a partir da raiz `OrangeVision`:

```powershell
python -m web_api.export_contract
```

Requer `web_api/requirements-dev.txt`. Exportação não acessa o banco nem aplica migrations.
Cookie de sessão opaco; logout requer `X-CSRF-Token` recebido em login/sessão e origem permitida.
Erros seguem `detail` do FastAPI; validação retorna somente campo/mensagem, nunca entrada sensível.

`GET /api/metrics/comparison` acrescenta comparação entre períodos por conta autenticada,
com `current`, `previous`, `changes`, intervalos explícitos e snapshot comum. Os contratos
anteriores são preservados. Percentuais de variação são nulos quando a base anterior é zero;
diferença da taxa de aprovação é expressa em pontos percentuais, não em percentual relativo.

O contrato também inclui o fluxo opcional de inspeção/pareamento e ingestão v1 do equipamento.
Exige migration 002 revisada/aplicada e ativação explícita; a flag permanece desligada por
padrão. Cookie/CSRF do usuário e credencial/autorização do equipamento são papéis distintos.
Análises receberam campos opcionais de rastreabilidade; os dados antigos não foram atribuídos
automaticamente a contas. Guia: `../Docs/Raspberry_Sessoes_Inspecao.md`.
