# Frontend — personalização somente após o login

React + TypeScript + React Router + TanStack Query + Zod.
Páginas públicas, login e cadastro usam HTML básico. A área `/dashboard` tem
layout personalizado, incluindo histórico, detalhes, perfil, inspeções e amostras.
Sem MUI, Emotion, Recharts, fontes externas ou estilos inline.

Mantidos: autenticação, validação, expiração/logout, isolamento por conta, filtros
com horário de Brasília, paginação, indicadores, comparação de períodos, séries
diárias, histórico/detalhe, perfil em consulta, pareamento/encerramento e amostras
privadas (upload, fila, contato do executor, máscara, métricas e detecção).

Os dados dos gráficos são apresentados em tabelas acessíveis. A região detectada
continua disponível por suas coordenadas junto da foto/máscara; não há overlay
posicionado por CSS. A janela OpenCV do dispositivo é independente do frontend
web e foi copiada como estava.

```powershell
yarn install --frozen-lockfile
yarn dev
```

Abra **http://127.0.0.1:5174**. O proxy `/api` usa
**https://orangevision.onrender.com** por padrão. `API_PROXY_TARGET` permite
configurar o destino do gateway local; `VITE_API_BASE_URL` permanece `/api`.
`.env` nunca deve conter senha do banco ou credencial do dispositivo.
Swagger: https://orangevision.onrender.com/docs.

`app/DashboardShell.tsx` é carregado depois de validar a sessão.
`shared/ui/dashboard.module.css` aplica estilos apenas dentro desse shell,
sem reset global: voltar para o site ou sair da conta restaura o HTML básico,
mesmo quando a folha já foi carregada. Formulários e tabelas continuam nativos,
com foco visível, menu móvel expansível e regiões de tabela roláveis por teclado.

```powershell
yarn build
yarn lint
yarn format:check
yarn test:proxy
yarn test:e2e --workers=2
```

`tests/functional.spec.ts` valida fluxos, HTML público sem personalização,
login → dashboard → logout, isolamento dos estilos após navegação SPA,
responsividade de 320 a 1440 px e acessibilidade automática. Screenshots em
`test-results` usam fixtures de teste, sem gravar dados na conta real.
Instruções do gateway: [Frontends e API Render](../Docs/FRONTENDS_API_RENDER.md).
