# Prompt — configuração inicial do OrangeVision no Raspberry

Copie o texto abaixo para o agente que trabalha na cópia do backend do Raspberry.
Os requisitos descrevem uma implementação futura no executor; não indicam que
essa configuração inicial já esteja implementada.

---

Implemente um assistente de configuração inicial no programa OrangeVision que
roda no Raspberry, seguindo os padrões e testes existentes no projeto.

## Contexto e objetivo

O usuário cadastra um equipamento no site, pelo login normal, na página
`/dashboard/dispositivos`. A Web API gera um novo UUID e uma credencial aleatória,
vinculando o equipamento à conta. O site mostra três valores:

- `DEVICE_ID`: UUID do equipamento gerado pelo site.
- `WEB_API_BASE_URL`: origem HTTPS da API, sem `/api` ou `/docs`.
- `DEVICE_INGEST_CREDENTIAL`: credencial privada exibida apenas na primeira
  resposta; a API armazena somente o hash. Para recuperar acesso, o proprietário
  gera uma nova credencial no site, revogando a anterior.

O programa local deve pedir esses valores quando ainda não estiver configurado,
salvá-los com segurança e reutilizá-los nas próximas inicializações. O usuário
não deve precisar editar manualmente um arquivo `.env`.

Não cadastrar outro equipamento a partir do Raspberry, gerar um UUID local ou
reutilizar senha/cookie da conta web. O equipamento já foi criado pelo site.
O ID sozinho não autoriza nada; a autenticação usa `Authorization: Bearer`.

## Primeiro, confirme a estrutura desta cópia

Na versão usada como referência, a pessoa copiou somente a pasta `backend/` para
o Raspberry. A raiz local pode conter diretamente `device/`, e os comandos são
`python -m device ...`. Não presumir que existe uma pasta `backend/` adicional.

Pontos de entrada conhecidos no projeto completo:

- `backend/device/config.py`: `DeviceSettings.load()`, configuração via
  `device/.env` e variáveis de ambiente.
- `backend/device/api.py`: `DeviceApi`, `Offline` e `ApiFailure`.
- `backend/device/__main__.py`: comandos `pair`, `run`, `samples`, `sync`, etc.
- `backend/device/inspect.py`: inspeção local; verificar seu fluxo de inicialização.
- `backend/device/storage.py`: SQLite, sessões, tentativas e outbox existentes.

Confirme quais arquivos realmente existem nesta cópia e preserve os fluxos atuais.
Use a interface local já existente, se houver; caso seja somente CLI, implemente
o assistente interativo no terminal, sem criar servidor web ou dependências de UI.

## Comportamento esperado

1. **Configuração ausente ou incompleta:** explicar que é preciso cadastrar o
   equipamento no site; solicitar os três valores com rótulos claros e ajuda.
   O segredo deve ser digitado/colado sem eco no terminal, ou mascarado numa UI.
   Permitir cancelar sem gravar um arquivo parcial.
2. **Configuração completa:** carregar normalmente, sem repetir o assistente
   nem substituir valores existentes silenciosamente. Preservar a precedência
   atual das variáveis de ambiente sobre `.env` e explicar conflitos.
3. **Validação:** UUID válido, origem HTTPS sem path/query/fragment/userinfo e
   formato da credencial compatível com o contrato atual. Não fixar o domínio
   nem imprimir a credencial. Não permitir que quebras de linha nos valores
   injetem outras variáveis no arquivo.
4. **Persistência:** usar arquivo local privado compatível com `DeviceSettings`,
   preservar as outras configurações (câmera, modelo, SQLite, calibração) e fazer
   gravação atômica. Em Linux, arquivo novo com permissão 0600, inclusive durante
   sua criação. Falha/cancelamento não pode destruir configuração anterior.
5. **Sem rede, timeout, TLS inválido ou API indisponível:** distinguir as causas,
   preservar os valores e permitir tentar novamente. Nunca pedir outro cadastro
   ou rotacionar uma credencial automaticamente por falta de conectividade.
   Não desabilitar a verificação TLS para contornar um erro.
6. **HTTP 401:** informar que a credencial não foi aceita; oferecer atualizar
   a credencial usando o valor gerado no site. Atualizar explicitamente, sem
   trocar UUID, apagar histórico ou criar outro equipamento. Um 403, 404, 429 ou
   503 não deve ser tratado automaticamente como credencial inválida.
7. **Reconfiguração explícita:** disponibilizar uma ação/comando coerente com
   a CLI atual para corrigir URL ou credencial. Mudança de DEVICE_ID exige
   confirmação e reconciliação com sessões/outbox; não atribuir dados pendentes
   de um equipamento a outro. Identidade diferente não é simples rotação.
8. **Execução automática:** em ambiente sem terminal interativo (serviço/CI),
   não bloquear esperando input. Retornar diagnóstico claro sobre configuração
   ausente e orientar executar o assistente no terminal.
9. **Próximos passos:** ao concluir, explicar como iniciar o modo escolhido.
   Não iniciar câmera, parear inspeção nem consumir trabalhos de amostras apenas
   para testar a configuração. Código temporário de inspeção e credencial
   permanente são valores diferentes.

## Verificação real de conexão: respeitar o contrato existente

Inspecione `DeviceApi` e o contrato publicado antes de escolher uma requisição
de validação. Na versão de referência não existe um endpoint genérico, sem
efeitos colaterais, que retorne a identidade do equipamento autenticado.

- `/health` só comprova disponibilidade do serviço: não valida a credencial nem
  a correspondência com `DEVICE_ID`.
- Existe `POST /api/device/samples/heartbeat`, usado pelo executor de amostras;
  depende da disponibilidade desse recurso, registra presença e sua resposta
  contém `last_seen_at`, não `device_id`. Não usá-lo como prova de identidade nem
  marcar `ready` sem o executor estar pronto.
- O pareamento é uma operação real de inspeção e não deve ser disparado como
  teste de conectividade; tampouco consumir uma amostra para testar login.

Se a API atual não permitir uma verificação segura e suficiente, implemente a
configuração local e os estados honestos de verificação pendente. Registre a
necessidade de um endpoint autenticado de identidade no projeto web para uma
próxima integração, sem inventar uma rota ou afirmar sucesso usando `/health`.
Mantenha a verificação de identidade nos fluxos legítimos já existentes.

## Validação e entrega

Crie testes com dados sintéticos, sem Neon, dispositivo real ou câmera, cobrindo:

- primeiro uso, configuração parcial, cancelamento e configuração já existente;
- UUID/URL/credencial inválidos, segredo oculto e ausência de secrets em logs;
- gravação atômica, preservação das outras chaves e permissões do arquivo;
- precedência de ambiente e execução sem TTY;
- falha de rede, credencial recusada, indisponibilidade e resposta incompatível;
- reconfiguração sem apagar SQLite/outbox/sessões nem trocar identidade
  silenciosamente; regressão dos modos de execução existentes.

Ao concluir, informe arquivos alterados, testes executados e comandos exatos
para configurar, atualizar uma credencial e iniciar o executor nesta cópia.
Documente separadamente configuração salva, comunicação disponível e identidade
autenticada. Não faça commit, deploy, migração ou alteração da API online.
