# Como testar a Web API pelo Swagger

Este guia mostra como fazer login, obter os tokens e testar a API do OrangeVision.
Comece pelo **login de usuário**. A credencial do Raspberry só é necessária para
testar as rotas do equipamento.

## 1. Abrir o Swagger

| Ambiente                                 | Endereço                                              |
| ---------------------------------------- | ----------------------------------------------------- |
| API publicada no Render                  | <https://orangevision-rs9g.onrender.com/docs>         |
| API local, quando iniciada na porta 8001 | <http://127.0.0.1:8001/docs>                          |
| Contrato OpenAPI publicado               | <https://orangevision-rs9g.onrender.com/openapi.json> |

Para iniciar a API local, com as dependências e o banco já configurados, execute
na raiz do projeto:

```powershell
python -m uvicorn web_api.main:app --host 127.0.0.1 --port 8001 --reload
```

Os requisitos completos de execução estão no [README da Web API](../web_api/README.md).

**Importante sobre a origem:** login e cadastro exigem que a origem do navegador
esteja na configuração `WEB_ALLOWED_ORIGINS` da API. Origem é somente protocolo,
host e porta, sem `/docs`.

- Para o Swagger do Render: `https://orangevision-rs9g.onrender.com`.
- Para o Swagger local acima: `http://127.0.0.1:8001`.

O padrão local permite os frontends na porta 5173, mas não inclui a porta 8001.
Se necessário, acrescente a origem do Swagger às origens já utilizadas. Exemplo
para desenvolvimento local em `web_api/.env`:

```dotenv
WEB_ALLOWED_ORIGINS=http://127.0.0.1:5173,http://localhost:5173,http://127.0.0.1:8001
```

Reinicie a API após alterar a configuração. No Render, a configuração fica nas
variáveis de ambiente do serviço e as origens de produção devem usar HTTPS.

## 2. Entender os três tipos de credencial

| Nome                   | Para que serve                                                                       | Como obter                                                     |
| ---------------------- | ------------------------------------------------------------------------------------ | -------------------------------------------------------------- |
| `orangevision_session` | Identifica o usuário autenticado; é um cookie, não um JWT                            | O servidor envia no login e o navegador guarda automaticamente |
| `csrf_token`           | Confirma operações como logout e início/encerramento de inspeção, junto com o cookie | Vem no JSON do login e de `GET /api/auth/session`              |
| `DeviceCredential`     | Autentica o dispositivo/Raspberry nas rotas próprias do equipamento                  | É emitida pela ferramenta administrativa de provisionamento    |

**Não use o `csrf_token` como Bearer.** Ele não substitui o cookie nem a credencial
do dispositivo.

## 3. Criar uma conta, se ainda não tiver

Se você já tem conta, vá para a próxima seção.

1. Abra **`POST /api/auth/register`**.
2. Clique em **Try it out**.
3. Preencha o corpo com seus dados. Exemplo fictício:

   ```json
   {
     "name": "Pessoa de Teste",
     "email": "pessoa@example.com",
     "password": "Exemplo-Senha-123!"
   }
   ```

4. Clique em **Execute**.

**Resultado esperado:** HTTP **201** com uma mensagem de confirmação.

Use um e-mail de teste próprio e uma senha própria, com **12 a 128 caracteres**.
O cadastro cria uma conta no banco configurado e não faz login automaticamente.

## 4. Fazer login e obter a sessão

1. Abra **`POST /api/auth/login`**.
2. Clique em **Try it out**.
3. Informe o e-mail e a senha cadastrados:

   ```json
   {
     "email": "pessoa@example.com",
     "password": "Exemplo-Senha-123!"
   }
   ```

4. Clique em **Execute**.

**Resultado esperado:** HTTP **200**, com uma resposta semelhante a esta:

```json
{
  "user": {
    "id": "11111111-1111-4111-8111-111111111111",
    "name": "Pessoa de Teste",
    "email": "pessoa@example.com"
  },
  "csrf_token": "VALOR_GERADO_PELA_API"
}
```

Copie o **`csrf_token` retornado de verdade** para usar nas operações que o exigem.
Os valores acima são apenas exemplos.

O servidor também envia o cookie **`orangevision_session`** pelo header
`Set-Cookie`. O token da sessão não aparece no JSON. No Swagger da mesma origem
da API, o navegador guarda e envia esse cookie automaticamente nas chamadas `/api`.

**Para esse fluxo, não é necessário preencher o botão Authorize.**
O cookie é HttpOnly: não é necessário nem esperado acessá-lo por JavaScript.

## 5. Confirmar que está autenticado e testar uma consulta

### Conferir a sessão

Execute **`GET /api/auth/session`** no mesmo navegador e na mesma origem do login.

**Resultado esperado:** HTTP **200**, com seu usuário e o `csrf_token` atual.
Se retornar **401**, faça login novamente e confira se o cookie foi armazenado.

### Consultar análises

1. Abra **`GET /api/analyses`**.
2. Clique em **Try it out**.
3. Use `limit = 20` e `offset = 0`; deixe os filtros opcionais vazios inicialmente.
4. Clique em **Execute**.

**Resultado esperado:** HTTP **200**, com a página de análises autorizadas para a conta.
Uma conta nova pode receber uma lista vazia; isso não significa falha no login.

Você também pode testar **`GET /api/metrics/summary`** sem preencher filtros.

## 6. Usar o token CSRF e fazer logout

Para fazer logout pelo Swagger:

1. Copie o `csrf_token` do login ou de `GET /api/auth/session`.
2. Abra **`POST /api/auth/logout`** e clique em **Try it out**.
3. Cole o valor no campo **`X-CSRF-Token`**.
4. Clique em **Execute**.

**Resultado esperado:** HTTP **204**, sem corpo de resposta.
Depois disso, `GET /api/auth/session` deve retornar **401**.

Iniciar ou encerrar uma inspeção também exige cookie, origem permitida e CSRF.
No código atual, algumas dessas rotas validam o header sem expor seu campo no
Swagger. Para enviá-lo manualmente, use o Postman conforme a próxima seção.

## 7. Testar pelo Postman

Crie estas variáveis na sua coleção ou ambiente:

| Variável     | Exemplo para o Render                    |
| ------------ | ---------------------------------------- |
| `base_url`   | `https://orangevision-rs9g.onrender.com` |
| `origem`     | `https://orangevision-rs9g.onrender.com` |
| `csrf_token` | Preencha após fazer login                |

O valor de `origem` precisa estar permitido em `WEB_ALLOWED_ORIGINS` no ambiente
consultado. Para uma API local, adapte os endereços à configuração local.

### Login

- Método: **POST**.
- URL: `{{base_url}}/api/auth/login`.
- Em **Headers**, adicione `Origin: {{origem}}`.
- Em **Body → raw → JSON**, informe o e-mail e a senha como na seção 4.
- Envie a requisição.

O Postman deve guardar o cookie recebido em seu gerenciador de cookies.
Mantenha o cookie habilitado e use o mesmo host nas chamadas seguintes.
Copie o `csrf_token` da resposta para a variável de mesmo nome.

### Conferir a sessão

- Método: **GET**.
- URL: `{{base_url}}/api/auth/session`.
- Não é necessário adicionar Bearer; o Postman envia o cookie armazenado.

### Logout ou outra operação de usuário que exige CSRF

Exemplo de logout:

- Método: **POST**.
- URL: `{{base_url}}/api/auth/logout`.
- Headers:

  ```text
  Origin: {{origem}}
  X-CSRF-Token: {{csrf_token}}
  ```

- Envie sem corpo e espere HTTP **204**.

Depois de um novo login, atualize o CSRF: a sessão e o token são renovados.

## 8. Obter o Bearer do dispositivo/Raspberry

Esta parte é necessária somente para testar rotas do equipamento, como
`/api/device/...` e `POST /api/ingest/analyses`.

O login do usuário **não emite essa credencial**. Ela é criada por uma ferramenta
administrativa, usando o banco configurado na API. A migration 002 precisa estar
aplicada; o procedimento completo está em
[Sessões de inspeção e preparação do Raspberry](Raspberry_Sessoes_Inspecao.md).

Na raiz do projeto, este comando apenas mostra o plano:

```powershell
python -m web_api.provision_device
```

Para criar um equipamento de teste e autorizar sua conta, substitua
`UUID_DA_SUA_CONTA` pelo `user.id` retornado em `/api/auth/session`:

```powershell
python -m web_api.provision_device --name "Dispositivo de teste" --user "UUID_DA_SUA_CONTA" --apply
```

**Esse comando grava no banco configurado:** cria um equipamento, uma credencial e
o vínculo com a conta. Para emitir uma credencial para um equipamento existente,
informe também `--device "UUID_DO_EQUIPAMENTO"` em vez de criar outro.

A ferramenta retorna:

```text
DEVICE_ID=...
CREDENTIAL_ID=...
DEVICE_INGEST_CREDENTIAL=...
```

O segredo `DEVICE_INGEST_CREDENTIAL` é exibido uma única vez. Guarde-o em ambiente
privado; não coloque credenciais reais neste guia nem no Git.

### Usar no Swagger

1. Clique em **Authorize**.
2. Localize **DeviceCredential**.
3. Cole somente o valor de `DEVICE_INGEST_CREDENTIAL`, **sem escrever `Bearer`**.
4. Confirme em **Authorize**.

O Swagger monta o header:

```http
Authorization: Bearer VALOR_DA_CREDENCIAL
```

No Postman, use **Authorization → Bearer Token** e cole o mesmo valor.

O Bearer identifica o equipamento, mas não substitui pareamento, IDs e headers
adicionais de cada operação. Algumas rotas exigem `X-Inspection-Lease` ou
`X-Sample-Lease`. Para inspeções, confira primeiro `GET /api/inspections/config`
com a sessão do usuário: o recurso é desligado por padrão.

## 9. Erros comuns

| Resultado                                        | O que conferir                                                                                                           |
| ------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------ |
| **401** em rota de usuário                       | Faça login e confira o cookie. Não misture `localhost`, `127.0.0.1` e Render entre login e consulta.                     |
| **401** em rota do dispositivo                   | Confira se o Bearer é a credencial do equipamento, está válido e não foi revogado.                                       |
| **403 — Origem não autorizada**                  | Confira `WEB_ALLOWED_ORIGINS`. No Postman, envie `Origin`; no navegador, a origem é definida automaticamente.            |
| **403 — Não foi possível validar esta operação** | Envie `X-CSRF-Token` da sessão atual junto com o cookie.                                                                 |
| **403** em operação de inspeção                  | Confira se a conta tem autorização para o equipamento/operação.                                                          |
| **404** em consulta de um registro               | Confira o ID e se o registro pertence ao conjunto autorizado para a conta.                                               |
| **409** no cadastro                              | Confira se o e-mail já está cadastrado.                                                                                  |
| **422**                                          | Confira os campos obrigatórios, e-mail, UUIDs e senha com 12 a 128 caracteres.                                           |
| **429**                                          | Aguarde o prazo indicado em `Retry-After` antes de repetir.                                                              |
| **503**                                          | Confira a disponibilidade da API, banco e migrations. Em rotas de inspeção, confira também se o recurso está habilitado. |

Se o Swagger nem abrir, consulte `/health` no mesmo host. Uma resposta de saúde
confirma que o processo está ativo, mas não garante que o banco esteja disponível.

## Resumo rápido

```text
Testar consultas do usuário:
login → cookie automático → GET /api/auth/session → GET /api/analyses

Testar operações do usuário com CSRF:
cookie + origem permitida + X-CSRF-Token da sessão atual

Testar rotas do equipamento:
provisionar credencial → Authorize / DeviceCredential → preencher dados da operação
```
