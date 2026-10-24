OrangeVision — Especificação de desenvolvimento do frontend
Versão: 1.0 — 24/10/2026
Destinatário: equipe responsável pelo frontend
Projeto: OrangeVision — triagem visual de laranjas com Raspberry Pi 4 (modelo ainda a confirmar)
1. Objetivo
Construir um site React + TypeScript responsivo para apresentar o projeto e permitir que operadores autorizados acompanhem capturas, detecções, análises e o estado do dispositivo. O processamento da câmera, YOLOX-Nano, OpenCV e eventual MobileNetV3-Small acontece no backend/Raspberry Pi, não no navegador.

O frontend deve funcionar inicialmente com dados fictícios identificados como demonstração e depois consumir a API FastAPI. Não inventar análises reais ou acurácia de modelos.
2. Stack recomendada
- React + TypeScript + Vite.
- Material UI (MUI) para componentes e responsividade.
- React Router para rotas.
- TanStack Query ou hooks simples para buscar dados da API.
- Recharts (opcional) para gráficos, somente quando houver dados.
- fetch ou Axios para comunicação com o backend.
Cores: laranja #F97316, verde #15803D, títulos #111827, texto secundário #374151. Priorizar layout claro, acessível e utilizável em celular.
3. Telas a desenvolver
Prioridade	Rota sugerida	Tela	Responsabilidade
P0	/login	Login	Formulário de e-mail e senha, validação e mensagens de erro; autenticação real dependerá de backend
P0	/cadastro	Cadastro	Nome, e-mail, senha, confirmação, termos quando aplicável; backend deverá autorizar criação de usuários
P0	/	Página inicial	Explicar problema, solução, fluxo, ODS 2, tecnologias e equipe
P0	/dashboard	Dashboard	Totais, categorias, últimas capturas e estado da conexão, sem inventar métricas
P0	/amostras	Amostras/capturas	Fotos experimentais, data, operador, estado da detecção e estado de avaliação
P1	/captura	Captura assistida	Abrir câmera disponível, posicionar fruta, capturar, enviar e acompanhar processamento
P1	/amostras/:id	Detalhe da amostra	Foto original, região detectada, confiança, métricas, status, mensagens e versão do modelo
P1	/historico	Histórico de inspeções	Somente registros que cumpriram critérios de avaliação e autorização
P1	/dispositivos	Dispositivos	Nome, modelo, estado e última conexão do Raspberry
P1	/perfil	Perfil	Dados básicos do operador e encerramento de sessão
P2	/planejamento	Planejamento	Etapas, 5W2H e cronograma
P2	/desenvolvimento	Desenvolvimento	Arquitetura, hardware, software, visão computacional e testes
P2	/resultados	Resultados	Evidências, metodologia e métricas reais quando disponíveis


Nota: rotas e nomes são sugestões; ajustar à organização do repositório existente. Login/cadastro não existem automaticamente por já haver Neon: a autenticação deve ser implementada e testada no backend antes de liberar uso real.
4. Descrição das telas operacionais
4.1 Login — simples, primeira entrega
- Logo OrangeVision, título "Entrar", campos e-mail e senha.
- Botão entrar, opção mostrar/ocultar senha, link para cadastro.
- Estados: carregando, credenciais inválidas, indisponibilidade de rede.
- Não guardar senha em localStorage; usar sessão/autenticação implementada no backend.
4.2 Cadastro — simples, primeira entrega
- Nome, e-mail, senha e confirmação; validações visuais.
- Mensagens de sucesso/erro; link de volta ao login.
- Em produção, considerar convite/aprovação de operadores para impedir cadastros não autorizados.
4.3 Dashboard
- Cards: total de inspeções válidas, aprovadas, atenção, revisar e taxa de aprovação.
- Últimas análises com data, miniatura e classificação.
- Estado do Raspberry e último sincronismo.
- Gráficos por período somente quando houver registros suficientes.
- Estado vazio: "Ainda não existem inspeções registradas".
- Separar amostras experimentais de inspeções válidas.
4.4 Captura assistida
- Botões: Abrir câmera, Capturar, Enviar para análise, Tentar novamente.
- Pré-visualização da câmera ou imagem capturada.
- Orientação de posicionamento da fruta.
- Estados: aguardando, enviando, na fila local, processando, concluído, falhou.
- Quando o Raspberry controlar a câmera, o frontend deve solicitar captura à API; getUserMedia só serve quando a câmera é do dispositivo que abre o navegador.
- Exibir um identificador único da captura para evitar duplicidade em reenvios.
4.5 Amostras e detalhe
- Lista de capturas experimentais com filtros por data e status.
- Mostrar imagem original e, se fornecida pelo backend, imagem com a caixa da detecção.
- Campos distintos:
  - Detecção: ENCONTRADA, NAO_ENCONTRADA, INCERTA.
  - Avaliação: AVALIADA, AGUARDANDO_AVALIACAO, NAO_AVALIAVEL.
  - Classificação: APROVADA, ATENCAO, REVISAR apenas quando avaliada.
- Mostrar confiança da detecção, nome/versão do detector, tempo de processamento e motivo de recusa quando disponíveis.
- Métricas: cor média, regiões anormais, circularidade, assimetria, score visual, com explicações e unidades quando definidas.
- Não mostrar "Aprovada" quando apenas a detecção da laranja foi bem-sucedida.
4.6 Histórico de inspeções
- Tabela com ID, data/hora, dispositivo, classificação e score visual.
- Busca e filtros por categoria e período.
- Paginação e estados vazio/erro/carregamento.
- O histórico de inspeções não deve receber automaticamente toda captura de teste.
4.7 Dispositivos e perfil
- Estado do dispositivo: online, offline, manutencao.
- Exibir horário da última conexão; não presumir "online" sem dado atualizado.
- Perfil: nome/e-mail do operador e botão sair.
5. Fluxo visual
Login / Cadastro
      ↓
Dashboard ─────→ Histórico de inspeções
      │
      ├────────→ Amostras ─────→ Detalhe da amostra
      │
      ├────────→ Captura assistida
      │                 ↓
      │          API FastAPI / Raspberry
      │                 ↓
      │       Detecção YOLOX-Nano
      │                 ↓
      │         Métricas OpenCV
      │                 ↓
      │      IA de qualidade (opcional)
      │                 ↓
      │        Resultado / pendência
      │
      └────────→ Dispositivos / Perfil
6. Integração com backend
6.1 Endpoints existentes no backend inicial
A versão inicial do backend foi planejada com endpoints como:
- GET /health
- GET /api/dashboard/resumo
- GET /api/analises
- GET /api/dispositivos
- GET /api/eventos
Validar os caminhos e formatos reais em /docs antes de integrar. Alguns endpoints podem exigir X-API-Key e não devem ser chamados diretamente de um React público com chave embutida.
6.2 Endpoints que ainda precisam ser implementados
As rotas abaixo são propostas, não recursos já disponíveis:
- POST /api/auth/login, POST /api/auth/register, POST /api/auth/logout, GET /api/auth/me.
- POST /api/capturas para iniciar/enviar captura.
- GET /api/capturas/:id para status e resultado.
- GET /api/amostras e GET /api/amostras/:id.
- GET /api/inspecoes para histórico validado.
- GET /api/dispositivos/:id/status para estado de hardware.
6.3 Contrato ilustrativo de resultado (a combinar com backend)
{
  "id": "uuid-da-captura",
  "data_hora": "2026-10-24T12:00:00Z",
  "imagem_url": null,
  "deteccao": {
    "status": "ENCONTRADA",
    "classe": "orange",
    "confianca": 0.92,
    "bbox": [120, 80, 320, 290],
    "modelo": "yolox-nano",
    "versao": "a-definir"
  },
  "avaliacao": {
    "status": "AGUARDANDO_AVALIACAO",
    "classificacao": null,
    "score_visual": null,
    "metricas": null,
    "motivo": "Calibracao ainda nao validada"
  },
  "sincronizacao": "PENDENTE"
}
Os valores acima são fictícios, apenas para exemplificar o formato. O frontend deve tolerar null, falhas e campos opcionais.
7. Segurança e configuração
- Nunca colocar DATABASE_URL, API_KEY do backend ou chaves de IA no código React ou em variáveis VITE_*.
- VITE_API_BASE_URL pode conter somente um endereço público da API, sem credenciais.
- Para o site hospedado, usar autenticação de sessão e um backend seguro; configurar CORS para os domínios reais.
- O React não acessa Neon PostgreSQL diretamente.
- Imagens privadas devem ser disponibilizadas via URLs autorizadas/temporárias ou endpoint autenticado.
- Tratar permissões do navegador para câmera, falhas de rede e reenvio sem duplicar capturas.
8. Estrutura sugerida de pastas
src/
├── app/
│   ├── App.tsx
│   └── routes.tsx
├── components/
│   ├── Layout.tsx
│   ├── Sidebar.tsx
│   ├── StatusBadge.tsx
│   ├── MetricCard.tsx
│   ├── CapturePreview.tsx
│   └── EmptyState.tsx
├── pages/
│   ├── Login.tsx
│   ├── Register.tsx
│   ├── Home.tsx
│   ├── Dashboard.tsx
│   ├── Samples.tsx
│   ├── SampleDetails.tsx
│   ├── Capture.tsx
│   ├── History.tsx
│   ├── Devices.tsx
│   └── Profile.tsx
├── services/
│   ├── api.ts
│   ├── auth.ts
│   └── captures.ts
├── types/
│   └── orangevision.ts
├── mocks/
│   └── demoData.ts
└── theme/
    └── theme.ts
9. Ordem de implementação e divisão de tarefas
Etapa A — ideal para quem está começando
1. Criar o projeto Vite + React + TypeScript e configurar MUI.
2. Criar tema e componentes reutilizáveis.
3. Implementar Login, Cadastro e Perfil apenas visualmente, com validações.
4. Implementar a Home e navegação responsiva.
5. Testar layout no celular e no desktop.
Etapa B — intermediária
1. Criar Dashboard e Histórico usando dados demonstrativos claramente identificados.
2. Criar Amostras e Detalhe da amostra, com estados de detecção/avaliação.
3. Integrar endpoints de leitura que o backend já disponibiliza.
4. Implementar tratamento de loading, erro, lista vazia e perda de conexão.
Etapa C — integração avançada
1. Implementar autenticação real em conjunto com o backend.
2. Integrar captura de imagem, upload e acompanhamento assíncrono.
3. Exibir caixas de detecção e métricas fornecidas pelo Raspberry.
4. Diferenciar amostras de inspeções validadas.
5. Testar autorização, reenvio, conectividade intermitente e responsividade.
10. Critérios de aceite
- Navegação funciona em desktop e celular, sem rolagem horizontal indevida.
- Login/cadastro validam campos; quando sem backend, informar claramente "modo demonstração".
- Não há chaves secretas no bundle React.
- Dashboard não apresenta números falsos como se fossem resultados reais.
- Detecção e classificação aparecem separadamente.
- Ausência de fruta ou detecção incerta não gera aprovação.
- AGUARDANDO_AVALIACAO é exibido quando não houver calibração validada.
- Fotos e resultados mantêm o mesmo ID de captura durante reenvios.
- Todos os fluxos têm estados de carregamento, vazio e erro.
- Testes básicos em Chrome/Edge e dispositivo móvel.
11. O que NÃO é responsabilidade do frontend
- Treinar YOLOX-Nano ou MobileNetV3-Small.
- Processar OpenCV no navegador.
- Controlar GPIO, servo, LEDs, buzzer ou sensor IR diretamente.
- Conectar ao PostgreSQL Neon com senha.
- Definir sozinho os critérios de qualidade da fruta.
Resumo para a equipe: primeiro construir as telas e a navegação; depois integrar as consultas do FastAPI; por fim implementar a captura e a visualização de detecção/análise, respeitando autorização e o estado de calibração.
