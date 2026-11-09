# Avaliação de amostras e confirmação local

## Contrato usado

O cliente continua usando apenas upload, reserva, imagem e resultado já presentes
em `device/api.py`. A resposta de upload tem `id` da amostra e
`source_inspection_id`; o resultado tem `state`. O campo **opcional** `analysis_id`,
informado como parte da integração da Web API, é lido no nível superior dessas respostas.
Não se presume outro endpoint, formato aninhado ou consulta de gráficos. O documento
`Docs/Capturas_Nos_Graficos.md` e o código da Web API atual não estão nesta cópia.

Quando presentes na resposta de resultado, categoria, motivo e validação da calibração
têm precedência sobre o resultado calculado localmente. Categorias só são exibidas
como avaliação válida quando o estado é `completed` e a calibração é validada.
Caso contrário, a interface mostra o motivo e não inventa uma categoria.

## Quatro informações independentes

1. **Detecção**: estado do último quadro analisado; não é avaliação de qualidade.
2. **Qualidade**: categoria/motivo da amostra identificada. Um resultado aguardando
   resposta aparece como local, sem fingir confirmação da API.
3. **Envio**: foto salva, aguardando confirmação, em envio ou recebida pela API.
4. **Registro**: confirmado somente por `analysis_id` UUID não nulo. Campo ausente,
   nulo ou vazio não comprova inclusão no histórico/gráficos. Campo inválido ou
   divergente não substitui uma confirmação conhecida e mantém a avaliação pendente.

O UUID da análise não é confundido com o UUID da amostra, foto local, equipamento
ou inspeção. A interface identifica a amostra do registro separadamente da amostra
da última avaliação, pois uploads e trabalhos podem terminar em outra ordem.
Mesmo com registro confirmado, os gráficos dependem de filtros, período e atualização
do site. A confirmação é do histórico, não da visualização atual de um navegador.

## Persistência e tentativas

`sample_status` preserva a associação foto/amostra, resultado público, confirmação
e `analysis_id` no SQLite existente. `sample_claim_attempt` preserva a tentativa de
reserva caso sua resposta se perca. Sessões e outboxes existentes não são apagadas.
Dados antigos sem recibos não recebem UUIDs inventados nem são reenviados para
preencher confirmações que não foram guardadas.

O payload fica salvo **antes** de publicar o resultado. Após falha ou reinício,
reserva, lease e payload são reutilizados: não se pede outro trabalho, não se recalcula
um resultado já pronto e não se chama o endpoint de ingestão de análises.
Após confirmação válida, dados transitórios de lease/claim/payload são removidos da
linha ativa; o resultado público e o UUID confirmado permanecem. O banco deve continuar
privado, inclusive seus backups: leases pendentes são dados sensíveis, nunca exibidos.

Esse fluxo depende da idempotência do endpoint de resultado para o mesmo identificador
de amostra/claim. Se uma reserva expirar ou for recusada após resposta perdida, a
pendência fica preservada. Não é seguro afirmar que a API não recebeu ou criar uma
segunda análise para contornar isso. A recuperação automática além desse ponto depende
de contrato documentado de reconciliação/idempotência na Web API; nenhuma rota foi inventada.

## Contorno e calibração

A seleção assistida rejeita contornos no limite do retângulo. Na detecção automática,
uma margem fixa de 10% podia ficar apertada para uma caixa imprecisa. Agora apenas
esse tipo específico de falha tenta margens de 25% e 50% (máximo de três tentativas).
Outros erros não são ignorados. Uma caixa na borda real da foto é rejeitada com
orientação de reenquadramento; fruta cortada não é aprovada artificialmente.

Nada disso cria calibração ou a declara validada. O arquivo provisório permanece
provisório. A mensagem de falha identifica o problema de recorte ou calibração e
pode ser lida por inteiro no painel Detalhes [I].

## Acompanhamento das avaliações pela Web API

Contrato: `GET /api/device/samples/{sample_id}/evaluations`, com a credencial do
equipamento e `X-Inspection-Lease` da sessão de origem. A consulta não agenda Gemini,
não consome a fila e não altera resultados; `/claim` e `/result` não são usados para isso.

- **Associação**: a amostra é ligada à captura em `sample_status.photo_id` e à sessão em
  `camera_sample_outbox.session_id`. A resposta só é aceita se `sample_id` e
  `inspection_id` coincidirem com esse vínculo e os campos respeitarem o contrato.
- **Sem consulta**: amostra enviada pelo site ou captura de revisão sem sessão original
  conhecida. O painel orienta acompanhar no site.
- **Execução**: no máximo uma consulta por ciclo de manutenção, em segundo plano, com
  timeout curto; câmera, captura e interface não aguardam a resposta.
- **Intervalos**: 15 s enquanto a amostra ou o job Gemini estiver em andamento e 120 s
  nos demais casos ainda abertos (sem job, o site ainda pode agendar um).
- **Falhas**: sem internet, 401, 429, 5xx ou resposta incompatível mantêm a última resposta
  válida e usam backoff de até 10 min, respeitando `Retry-After`.
- **Encerramento**: job Gemini e amostra em estado terminal, ou HTTP 403, 404, 410 ou 422.
  Depois disso, uma mudança posterior (como decisão humana) só aparece no site.
- **Exibição**: o painel lê do SQLite somente os dados da amostra exibida, portanto uma
  resposta tardia de outra captura não aparece nela, e o estado volta após reiniciar.

Não instale SDK Gemini nem coloque `GEMINI_API_KEY` no Raspberry.
