# Amostras de imagens e estados no site

> A extensão de IA, contato do executor e captura integrada está descrita em
> `Docs/IA_Captura_Integrada.md`. Para a versão atual, aplicar também a migration
> 004 após a 003. O consumidor aceita `--ai` e o script `Start-OrangeVision.ps1`
> inicia os serviços locais necessários.

## O que está implementado

Página privada **Amostras**, em `/dashboard/amostras`, para enviar JPEG/PNG/WebP
da pasta local, inclusive fotos salvas pela webcam. Não exige uma fruta física
nem sessão de inspeção pareada para experimentar arquivos. O processamento exige
um equipamento provisionado e autorizado para a conta.

As imagens são amostras de teste/calibração: **não são inseridas em `analises`**,
não entram no dashboard de aprovação e não herdam o operador de quem estiver
logado em outro momento. O proprietário é quem fez o upload autenticado.

## Como testar agora, sem laranja

Na raiz `OrangeVision`, inicie/reinicie a API em um terminal:

```powershell
.\web_api\.venv-web\Scripts\python.exe -m uvicorn web_api.main:app --host 127.0.0.1 --port 8001 --reload
```

Em outro terminal, na pasta `OrangeVision\Frontend`:

```powershell
yarn dev --host 127.0.0.1 --port 5173 --strictPort
```

1. Abra `http://127.0.0.1:5173`, entre na conta e escolha **Amostras** no menu.
2. Selecione um arquivo, por exemplo `calibracao-local\Laranja-Seleta.webp`, e
   clique em **Enviar imagem**. A foto deve aparecer como **Imagem recebida**.
3. Selecione o equipamento autorizado e clique **Enviar para análise local**.
   O estado passa para **Aguardando análise**.
4. No PC configurado (ou no Raspberry com o mesmo código e sua credencial própria),
   execute o consumidor. No Windows, a partir da raiz:

```powershell
.\backend\.venv-device\Scripts\python.exe -m backend.device samples --loop
```

Sem calibração, ele verifica a aquisição do arquivo e devolve **Aguardando avaliação**,
sem fabricar métricas/categoria. O site atualiza a lista a cada 5 segundos enquanto
a aba está ativa; **Atualizar amostras** consulta imediatamente. O estado **Em análise**
pode durar menos que esse intervalo e não aparecer em todas as execuções rápidas.

Não precisa abrir a câmera ou a ferramenta `lab` para processar arquivos da fila.
O comando usa `DEVICE_ID`, `DEVICE_INGEST_CREDENTIAL`, `WEB_API_BASE_URL` e a
autorização HTTP local explícita já configurados no `.env` do dispositivo.
Não copia senha/cookie do usuário para o equipamento e não modifica a sessão de inspeção.
`Ctrl+C` interrompe o consumidor.

## Extrair máscara e métricas com um rascunho

Se já coletou amostras F/O/D na bancada e salvou com G:

```powershell
.\backend\.venv-device\Scripts\python.exe -m backend.device samples --loop --draft "calibracao-local\calibracao-SEU_ARQUIVO.json"
```

Use o nome real exibido pela bancada. Após ajustar o rascunho, pare o consumidor,
reinicie com o arquivo atualizado e clique **Analisar novamente** na amostra.

- A máscara HSV, quando utilizável, aparece abaixo da imagem no site.
- Cor laranja/regiões anormais permanecem indisponíveis sem amostras O/D.
- Resultado de rascunho é **Aguardando avaliação**, sem score/categoria.
- Faixa inválida, contorno insuficiente ou tocando a borda resultam em
  **Não foi possível avaliar**, nunca na categoria Revisar.
- A seleção manual B/GrabCut é um auxílio da bancada; ela não é salva como
  calibração geral nem é automaticamente reproduzida pelo consumidor HSV.

Somente com calibração de fato revisada e validada:

```powershell
.\backend\.venv-device\Scripts\python.exe -m backend.device samples --loop --calibration "CAMINHO_DA_CALIBRACAO_VALIDADA.json"
```

Nesse caso uma amostra pode ficar **Concluída** com categoria e métricas
experimentais. Isso não transforma a amostra em inspeção real nem comprova acurácia.
Não mudar `validated` para true apenas para fazer a categoria aparecer.

## Estados e significado

| Estado no site | Significado |
|---|---|
| Imagem recebida | A API armazenou a imagem normalizada. |
| Aguardando análise | O proprietário destinou a amostra a um equipamento autorizado. |
| Em análise | O equipamento reservou o arquivo por até 5 minutos. |
| Aguardando avaliação | Aquisição/métricas disponíveis, mas categoria não validada. |
| Concluída | Resultado experimental completo com calibração validada declarada pelo dispositivo confiável. |
| Não foi possível avaliar | A aquisição/segmentação não produziu dados utilizáveis. |
| Falha no processamento | Erro técnico do executor, sem converter erro em categoria. |

O site não mostra “aguardando envio” de uma foto ainda desconhecida da API.
Estado da tarefa é separado de Aprovada/Atenção/Revisar. Uma casca verde, nome de
arquivo ou imagem de doença não determina automaticamente a categoria.

## Reserva, permissões e recuperação

- Cada conta lista/lê/enfileira somente as próprias amostras.
- O executor recebe apenas filas destinadas ao seu equipamento e cujo dono
  ainda possui vínculo de uso. Downloads/resultados exigem Bearer e reserva.
- Revogar o vínculo impede o executor de acessar/confirmar a amostra.
- Retry de upload usa o mesmo request_id enquanto o arquivo selecionado não muda.
- Retry da mesma claim/token recupera a reserva; retry do mesmo resultado é
  idempotente. Resultado divergente ou de reserva anterior não sobrescreve o atual.
- Se a rede cair ou o executor reiniciar, o arquivo continua na API. Após 5 minutos,
  outra reserva pode reprocessá-lo. O cálculo pode se repetir, mas não há atuação
  física nem criação de análises oficiais duplicadas.
- Com `--loop`, falhas transitórias são retomadas. Credencial recusada ou erro
  permanente exige correção operacional; não há bypass de autorização.
- Enquanto o processamento estiver reservado, reenvio manual da amostra fica
  bloqueado. Se a reserva venceu, a API permite reenfileirar; atualize a lista.

## Armazenamento e limites

Migration `003_image_samples.sql`: tabela privada `orangevision_web.image_samples`.
Neste MVP, JPEG normalizado e máscara binária PNG são bytea privados no PostgreSQL;
não há diretório público de uploads nem dependência de disco efêmero do Render.
Até **200 amostras por conta**, arquivo de até **5 MiB**, entrada estática de até
**16 MP**, imagem normalizada até **1600 px** no maior lado. EXIF/orientação são
tratados, metadados removidos e transparência composta sobre branco.

As métricas usam a imagem normalizada recebida pelo executor. Resolução e JPEG
podem alterar cores/áreas; uma calibração de outra montagem/resolução deve ser
avaliada novamente. Volume maior exige rever retenção e object storage; este
armazenamento é para a base pequena de desenvolvimento.

### Ativação em outro ambiente

Instale as dependências atualizadas da API (incluem Pillow), revise o SQL e aplique
explicitamente, após as migrations de autenticação/equipamento existentes:

```powershell
.\web_api\.venv-web\Scripts\python.exe -m pip install -r web_api/requirements.txt
.\web_api\.venv-web\Scripts\python.exe -m web_api.migrate --migration 003
.\web_api\.venv-web\Scripts\python.exe -m web_api.migrate --migration 003 --apply
```

A migration 003 foi aplicada no ambiente atual com autorização explícita do usuário.
Sem a tabela, a galeria mostra ativação pendente e não finge uma lista vazia.

## Contratos e verificação

- Contrato explicado em `contracts/samples.md`; artefato completo em
  `contracts/web-openapi.yaml`. Operações e schemas anteriormente publicados
  foram comparados antes da exportação e preservados.
- `web_api/tests/test_samples.py`: autorização, CSRF, imagem inválida, tamanho,
  idempotência, orientação/remoção de metadados e coerência de resultados.
- `backend/device/tests/test_samples.py`: arquivo sem calibração, máscara de
  rascunho, categoria somente com calibração validada, recuperação de respostas
  perdidas e continuação após desconexão.
- `Frontend/tests/samples.spec.ts`: upload/estados, CSRF, indisponibilidade,
  responsividade desktop/mobile e acessibilidade automática.
- `python -m web_api.verify_samples_sql --run`: ensaio autorizado HTTP/SQL em
  schemas aleatórios com rollback obrigatório. Validou upload idempotente,
  isolamento A/B, autorização do equipamento, máscara, ACK repetido, conflito,
  expiração/retomada de reserva e rollback após falha injetada antes do commit.
  Os schemas/fixtures foram removidos pela transação. Não mede concorrência
  PostgreSQL real entre conexões nem comprova hardware/classificação de frutas.

Os 3 testes PostgreSQL concorrentes da rodada anterior continuam exigindo banco
dedicado/Docker; o ensaio transacional não é apresentado como substituto deles.

Resultado final desta entrega: **65 testes do executor**, **79 testes da API** e
**63 testes Playwright aprovados**; os **3 testes PostgreSQL opt-in permaneceram
skipped** sem banco dedicado. Build/TypeScript, ESLint, Prettier e Ruff aprovados.
O teste de acessibilidade desktop também identificou e permitiu corrigir o nome
acessível do link de perfil no cabeçalho, preservando o texto visível.
