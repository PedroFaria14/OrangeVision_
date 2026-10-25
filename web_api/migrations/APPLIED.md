# Registro da migration de autenticação

## 20/10/2026 — `001_web_auth.sql`

Aplicação autorizada explicitamente pelo responsável, no Neon configurado no ambiente da
API. Credenciais, host, nome do usuário e URL de conexão não são registrados neste arquivo.

### Inspeção anterior

- Tabelas existentes: `public.analises`, `public.dispositivos`, `public.eventos_sistema`.
- Não havia tabelas de autenticação identificadas no inventário.
- IDs de análise/dispositivo: UUID; data/hora de análise: timestamp com timezone.
- Permissão de criação de schema confirmada para a conexão configurada.

### Alteração aplicada

Criado o schema `orangevision_web`, contendo:

- `users`: usuário e hash de senha, com e-mail único.
- `sessions`: identificador protegido, CSRF e expiração, associado ao usuário.
- `device_access`: vínculos explícitos entre usuários e dispositivos.
- `auth_attempts`: contadores compartilhados de tentativas de autenticação.

SQL executado em transação com limites de espera/execução. Confirmadas as quatro tabelas
após o commit. Não foram alteradas definições ou dados das três tabelas originais.

### Verificação de integração

Pipeline HTTP da API exercitado com PostgreSQL real, usando uma conta temporária:

| Fluxo                                  | Resultado               |
| -------------------------------------- | ----------------------- |
| Cadastro                               | 201                     |
| Cadastro duplicado                     | 409                     |
| Senha inválida                         | 401                     |
| Login e consulta de sessão             | 200                     |
| Histórico, resumo e série sem vínculos | 200, sem dados privados |
| Detalhe sem acesso                     | 404                     |
| Logout sem CSRF                        | 403                     |
| Logout válido                          | 204                     |
| Sessão revogada/expirada               | 401                     |

Hash Argon2id e cookie HttpOnly conferidos. As escritas de teste foram revertidas por
rollback, e a ausência da conta, sessões e contadores temporários foi confirmada depois.
Nenhuma conta administrativa ou liberação automática de dispositivos foi criada.

### Limites

O teste não comprova calibração/qualidade da visão computacional, acesso a imagens privadas,
carga/concorrência ou deploy no Render. As unidades das métricas legadas ainda precisam ser
confirmadas com o processamento físico. Usuários novos precisam de vínculo explícito para
consultar dispositivos existentes.
