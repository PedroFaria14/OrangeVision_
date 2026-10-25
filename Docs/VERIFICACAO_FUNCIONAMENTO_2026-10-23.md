# OrangeVision — verificação de funcionamento

Data: 23/10/2026. Revisão da versão atual do diretório local. Sem mudanças de código, migrations ou dados nesta rodada.

## Parecer

A base pode continuar em desenvolvimento: tipagem, lint, build e 23 testes selecionados da API passaram. O sistema completo ainda não está aprovado para publicação ou demonstração de ponta a ponta; faltam evidências de autenticação real, inspeção, câmera e sincronização.

## Executado nesta rodada

| Verificação | Resultado | Limite |
|---|---|---|
| Frontend: yarn typecheck | Aprovado | Verificação estática |
| Frontend: yarn lint | Aprovado | Verificação estática |
| Frontend: build, dentro de yarn test:e2e | Aprovado | Compilação, não integração |
| API: testes selecionados sem HTTP | 23 aprovados, 3 desmarcados | Sem acesso ao banco real |
| API: suíte completa | Iniciada e interrompida sem conclusão | Não declarar aprovada |
| Frontend: Playwright | Build concluído; execução sem conclusão após iniciar servidor de testes | Não declarar aprovada |
| Aplicação em navegador | Porta 5173 inicialmente recusou conexão; após iniciar Vite, ocorreu timeout | Nenhum fluxo ao vivo foi validado nesta rodada |
| API online local | Comando uvicorn iniciado, sem confirmação de prontidão | Não declarar API disponível |

Comando dos testes concluídos:

```powershell
.\web_api\.venv-web\Scripts\python.exe -m pytest web_api/tests/test_comparison.py web_api/tests/test_separation.py web_api/tests/test_database.py web_api/tests/test_config_location.py web_api/tests/test_migration_command.py -k 'not http' -q
```

Cobertura: regras de comparação temporal e denominadores, fronteiras arquiteturais, adaptador de conexão, localização de configuração e comando de migrations com dependências simuladas. Os testes do comando de migration não aplicaram schema no banco real. Há um aviso de depreciação na dependência de TestClient; não causou falha nos testes selecionados.

Processos iniciados apenas para esta verificação foram encerrados ao final. Nenhum processo preexistente do usuário foi encerrado.

## Evoluções encontradas no código atual

- Filtros já têm Hoje, 7 dias, 30 dias e limpar; datas personalizadas recolhem no mobile.
- Inspeções já diferenciam indisponibilidade da consulta, nenhum equipamento autorizado e seleção necessária.
- Aviso de justificativa no detalhe passou a ser condicional.
- Várias melhorias visuais posteriores à primeira rodada estão no diretório e foram preservadas.

Essas observações vêm da leitura do código; não substituem teste operacional. Há alterações locais de trabalho já existentes, que não foram revertidas nem commitadas.

## Ordem para seguir

1. Confirmar API online respondendo /health e frontend na porta efetivamente iniciada. Health confirma processo vivo, não banco ou permissões.
2. Validar cadastro/login/sessão/logout com conta autorizada em ambiente de integração. Não assumir sucesso porque o formulário renderiza.
3. Conferir histórico, detalhe e agregados com uma análise real autorizada; contagens e unidades devem conferir com a fonte.
4. Se inspeções estiverem habilitadas, validar provisionamento/vínculo existente e pareamento físico, sem aplicar migrations por tentativa.
5. No Raspberry, validar captura, segmentação e classificação com iluminação e calibração documentadas. Não afirmar qualidade interna ou doença.
6. Validar persistência offline e sincronização, incluindo reenvio do mesmo UUID após perda de confirmação.
7. Reexecutar suíte completa HTTP/Playwright até obter resultados conclusivos e guardar evidências.

## Critério para avançar à publicação

Login e autorização reais; uma análise rastreável da câmera até o dashboard; métricas sem divergência de unidade; perda de internet sem perda de registro; reenvio sem duplicação; operações sem periféricos opcionais; testes HTTP/navegador concluídos; configuração de hospedagem/segredos/reverse proxy revisada.

Sem esses passos, é adequado avançar no desenvolvimento, mas não declarar a integração completa concluída.
