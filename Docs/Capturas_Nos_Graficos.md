# Capturas da câmera no histórico e nos gráficos

> Para as duas avaliações independentes, confirmação/correção do operador e
> implantação do worker Gemini, consulte
> [Avaliacoes_Local_Gemini.md](Avaliacoes_Local_Gemini.md). A migration 008 sucede
> a 007 e preserva uma única contagem por captura.

## Comportamento

A galeria **Amostras** mantém as imagens, detecção, máscara e diagnóstico. Após a
ativação desta integração, a conclusão de uma captura válida também registra uma
análise em `public.analises`, fonte do histórico, comparações e gráficos existentes.
O operador continua sendo o da sessão de origem, não quem está logado depois.

Requisitos para inclusão automática:

- Resultado `completed`, com categoria `APROVADA`, `ATENCAO` ou `REVISAR`, métricas
  completas, motivo e versões de calibração/algoritmo válidos pelo contrato.
- Origem de câmera: `source_inspection_id` e `captured_at` preenchidos.
- Conta e equipamento da amostra iguais aos da sessão de origem; horário da foto
  dentro da autorização dessa sessão. A sessão pode já ter sido encerrada.
- `WEB_INSPECTIONS_ENABLED=true` e migration 007 aplicada.
- Identificador do algoritmo com até 50 caracteres, limite do histórico legado.

O score do detector **não** vira score de qualidade. `awaiting_review`,
`not_evaluable`, `failed` e arquivos experimentais sem sessão não geram análise.
Capturas offline recuperadas sem uma sessão de origem comprovada também não são
atribuídas retroativamente à sessão usada apenas para autorizar seu upload.

## Resultados anteriores

Uma captura anterior já concluída e com origem comprovada mostra **Incluir nos
gráficos**. Essa ação registra o resultado uma única vez. A migration não publica
dados antigos automaticamente. Fotos sem avaliação precisam ser reprocessadas
com configuração/calibração adequadas no executor.

Após a inclusão, o cartão mostra **Incluída nos gráficos e no histórico**, com
links **Ver análise** e **Ver gráficos**. Os gráficos usam a data da captura:
confira período e filtros do dashboard. Amostras publicadas ficam imutáveis para
reprocessamento; faça uma nova captura para produzir outra análise.

## Ativação em produção — etapa operacional separada

```bash
# Somente plano, sem conectar ao banco:
python -m web_api.migrate --migration 007
# Apenas após revisar/autorização, no ambiente do banco correto:
python -m web_api.migrate --migration 007 --apply
```

Pré-requisitos: schema legado de análises e migrations 001–005. A 007 adiciona
`image_samples.analysis_id`, FK para a análise e índice único. Não apaga dados nem
faz backfill. Revisar privilégios do papel da API para `analises`,
`ingestion_receipts` e o novo campo. Publicar Web API/Render e frontend/Vercel.

Sem a 007, o processamento continua salvando resultados na galeria, mas não os
publica no dashboard. O site informa que a integração está indisponível. Depois
de ativar, resultados anteriores válidos podem ser incluídos pelo botão.

Não desligue inspeções indiscriminadamente para voltar ao modo legado: consulte
o tratamento do histórico em `Raspberry_Sessoes_Inspecao.md`. Análises pessoais
continuam protegidas, e não passam a ser compartilhadas entre contas.

## Contrato e implementação

- `ImageSample.analysis_id`: identificador opcional da análise publicada.
- `SamplesConfig.dashboard_enabled`: prontidão da integração (migration + modo).
- `POST /api/samples/{sample_id}/analysis`: sessão, Origin e CSRF; 200 idempotente;
  404 para outra conta, 409 para origem/resultado incompatível, 503 sem ativação.
- `POST /api/device/samples/{sample_id}/result`: payload existente preservado;
  após salvar um resultado válido, publica na mesma transação.
- `queue` retorna 409 para uma amostra que já possui análise publicada.

O lock da linha da amostra serializa publicação e reenvios. Resultado, análise,
receipt e vínculo são confirmados juntos; erro de escrita reverte a transação.
Razões 0–1 são convertidas aos percentuais legados e lidas novamente como razões.
Não existe GET que publique resultados ou atribua proprietário.

O contrato está em `contracts/web-openapi.yaml`. Teste local, sem banco real:

```bash
python -m pytest web_api/tests -q
python -m web_api.tests.run_sample_publication_postgres
```

O segundo comando sobe PostgreSQL 16 descartável em Docker e testa concorrência,
isolamento, unidades, categorias, autorização, replay e rollback.

## Prompt para corrigir o processamento no Raspberry

Copie para o agente que trabalha na cópia do backend do Raspberry:

```text
Investigue e ajuste o processamento de capturas do OrangeVision. O site já mantém
as imagens em Amostras e a Web API publica automaticamente resultados válidos de
capturas de inspeção no histórico/gráficos após a migration 007.

Problema observado: uma foto retorna awaiting_review e outras not_evaluable com
"O contorno encostou no limite da seleção". O detector identifica orange, mas
isso não é uma classificação de qualidade.

Confira os arquivos reais desta cópia. Referências: device/samples.py
(sample_result), device/segmentation.py (segment_guided), device/vision.py
(CalibratedVision), device/inspect.py e device/camera_window.py. A cópia pode
conter diretamente device/, sem a pasta backend/ externa.

1. Investigue a seleção automática em volta da caixa do detector e o GrabCut.
   Não remova a proteção de contorno na borda para esconder uma fruta recortada.
   Avalie margem adaptativa e nova tentativa limitada somente quando houver
   espaço na foto; fruta cortada na borda da imagem deve continuar rejeitada.
   Verifique os testes com imagens completas, cortadas e fundo semelhante.
2. Confira se a calibração efetivamente é carregada no modo em execução.
   --ai sozinho não produz qualidade. Para yolox-s-grabcut-v1 é necessária
   calibração compatível, faixas e regras/limiares verificados com fotos rotuladas.
   Não marque validated=true nem invente limiares para forçar uma classe.
   Sem calibração real, apresente diagnóstico e indique as medições pendentes.
3. Preserve source_inspection_id e captured_at reais e imutáveis em capturas,
   recuperação offline e reenvios. Não substituir pela conta ou sessão atual.
4. Continue usando o contrato existente de SampleResult: completed só com
   classification, todas as metrics, calibration_validated=true e versões reais.
   Garanta algorithm_version coerente com o método e com até 50 caracteres.
   O score do detector não é visual_score. Não enviar user_id ou analysis_id.
5. Não envie uma segunda análise diretamente para ingest só para alimentar o
   gráfico: a Web API fará a integração. Evite duplicação e preserve retries,
   SQLite, outbox, leases e isolamento por sessão.
6. Crie testes sintéticos de segmentação, carregamento de calibração e payload,
   sem câmera ou serviços reais. Não altere dados de produção.

Entregue causa encontrada, arquivos alterados, testes e o comando exato para
iniciar esta instalação com a calibração apropriada. Se faltarem fotos rotuladas
ou parâmetros de bancada, explique o que falta; não afirme classificação validada.
```
