import { useRef, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Alert,
  Box,
  Button,
  Chip,
  MenuItem,
  Paper,
  Stack,
  TextField,
  Typography,
} from '@mui/material';
import { Page } from '@/shared/ui/Page';
import { ApiError } from '@/shared/api/client';
import { formatDate, formatNumber, formatRatio } from '@/shared/lib/format';
import { useSession } from '@/features/auth/hooks/useSession';
import { Link as RouterLink } from 'react-router-dom';
import { authorizedDeviceId } from '@/shared/lib/device_selection';
import { DualEvaluations } from './DualEvaluations';
import {
  listSamples,
  queueSample,
  publishSample,
  sampleDevices,
  samplesConfig,
  sampleStates,
  uploadSample,
  type Sample,
} from './api';

function executorStateLabel(state?: string | null) {
  const labels: Record<string, string> = {
    starting: 'Iniciando',
    ready: 'Pronto',
    error: 'Erro',
    stopped: 'Encerrado',
  };
  return state ? (labels[state] ?? state) : 'Não informado';
}

function sampleError(error: unknown) {
  if (error instanceof ApiError) {
    if (error.status === 413)
      return 'A imagem excede o limite de tamanho. Envie um arquivo de até 5 MiB.';
    if (error.status === 422)
      return 'Use uma imagem estática JPEG, PNG ou WebP, legível e com até 16 milhões de pixels.';
    if (error.status === 409)
      return 'Operação em conflito: confira o estado da amostra, a reserva de processamento e o limite de 200 arquivos por conta.';
    if (error.status === 403)
      return 'Acesso não autorizado. Confira a sessão e o equipamento selecionado.';
  }
  return 'Não foi possível concluir a operação. Atualize a consulta e tente novamente.';
}

function SampleCard({
  item,
  queue,
  disabled,
  observedAt,
  executor,
  publish,
  publishDisabled,
  evaluationContext,
}: {
  item: Sample;
  queue: () => void;
  disabled: boolean;
  observedAt: number;
  publish: () => void;
  publishDisabled: boolean;
  evaluationContext: {
    userId: string;
    csrf: string;
    enabled: boolean;
    geminiEnabled: boolean;
    canAdopt: boolean;
  };
  executor?: {
    last_seen_at?: string | null;
    executor_recent?: boolean;
    executor_state?: string | null;
  };
}) {
  const [imageFailed, setImageFailed] = useState(false);
  const [maskFailed, setMaskFailed] = useState(false);
  const expiredReservation =
    item.state === 'processing' &&
    item.claim_expires_at !== null &&
    Date.parse(item.claim_expires_at) <= observedAt;
  return (
    <Paper component="article" variant="outlined" sx={{ p: 2, minWidth: 0 }}>
      <Stack spacing={2}>
        <Typography
          component="h2"
          variant="h6"
          sx={{ overflowWrap: 'anywhere' }}
        >
          {item.filename}
        </Typography>
        <Stack direction="row" sx={{ gap: 1, flexWrap: 'wrap' }}>
          <Chip
            label={sampleStates[item.state]}
            variant="outlined"
            sx={{ maxWidth: '100%' }}
          />
          {!item.decision &&
            !item.analysis_id &&
            item.source_inspection_id &&
            evaluationContext.enabled && (
              <Chip
                label="Aguardando sua validação"
                color="warning"
                sx={{ maxWidth: '100%' }}
              />
            )}
          {!item.decision &&
            !!item.analysis_id &&
            item.comparison === 'divergence' &&
            evaluationContext.enabled && (
              <Chip
                label="Gemini discorda — confira"
                color="secondary"
                variant="outlined"
                sx={{ maxWidth: '100%' }}
              />
            )}
        </Stack>
        {imageFailed ? (
          <Alert severity="warning">
            Não foi possível carregar a imagem privada.
          </Alert>
        ) : (
          <Box sx={{ position: 'relative' }}>
            <Box
              component="img"
              src={item.image_url}
              alt={`Amostra: ${item.filename}`}
              loading="lazy"
              onError={() => setImageFailed(true)}
              sx={{
                width: '100%',
                aspectRatio: '4/3',
                objectFit: 'contain',
                bgcolor: '#F4F6F8',
                borderRadius: 1,
                display: 'block',
              }}
            />
            {item.detection?.box && (
              <Box
                component="svg"
                aria-hidden="true"
                viewBox={`0 0 ${item.width} ${item.height}`}
                sx={{
                  position: 'absolute',
                  inset: 0,
                  width: '100%',
                  height: '100%',
                  pointerEvents: 'none',
                }}
              >
                <rect
                  x={item.detection.box[0]}
                  y={item.detection.box[1]}
                  width={item.detection.box[2]}
                  height={item.detection.box[3]}
                  fill="none"
                  stroke="#15803D"
                  strokeWidth="3"
                  vectorEffect="non-scaling-stroke"
                />
              </Box>
            )}
          </Box>
        )}
        {item.detection && (
          <Box>
            <Typography variant="body2">
              <strong>Detecção:</strong>{' '}
              {item.detection.status === 'detected'
                ? 'Modelo sugere laranja'
                : item.detection.status === 'ambiguous'
                  ? `Mais de uma laranja candidata (${item.detection.count})`
                  : 'Laranja não detectada com score suficiente'}
            </Typography>
            {item.detection.score !== null && (
              <Typography variant="body2">
                Score do detector: {formatRatio(item.detection.score)} · não é
                acurácia nem qualidade.
              </Typography>
            )}
            <Typography variant="caption">
              {item.detection.model} ·{' '}
              {formatNumber(item.detection.inference_ms)} ms
            </Typography>
            {item.detection.box && (
              <Typography variant="body2" sx={{ overflowWrap: 'anywhere' }}>
                Caixa da detecção (x, y, largura, altura):{' '}
                {item.detection.box.join(', ')} px.
              </Typography>
            )}
          </Box>
        )}
        {item.source_inspection_id && (
          <Typography variant="body2" sx={{ overflowWrap: 'anywhere' }}>
            Captura da câmera · sessão: {item.source_inspection_id}
          </Typography>
        )}
        {item.review_authorization_id && (
          <Typography variant="body2">
            Foto local enviada após reconexão autorizada, preservando a origem.
          </Typography>
        )}
        {item.mask_url && (
          <Box>
            <Typography variant="body2">Máscara da região candidata</Typography>
            {maskFailed ? (
              <Alert severity="warning">Máscara indisponível.</Alert>
            ) : (
              <Box
                component="img"
                src={`${item.mask_url}?v=${encodeURIComponent(item.updated_at)}`}
                alt={`Máscara experimental: ${item.filename}`}
                loading="lazy"
                onError={() => setMaskFailed(true)}
                sx={{
                  width: '100%',
                  maxHeight: 200,
                  objectFit: 'contain',
                  bgcolor: '#F4F6F8',
                }}
              />
            )}
          </Box>
        )}
        <Typography variant="body2" color="text.secondary">
          {item.width} × {item.height} px · Recebida:{' '}
          {formatDate(item.created_at)}
        </Typography>
        {item.reason &&
          !item.evaluations.some((value) => value.origin === 'local') && (
            <Typography variant="body2" sx={{ overflowWrap: 'anywhere' }}>
              {item.reason}
            </Typography>
          )}
        <Typography variant="body2">
          <strong>Categoria:</strong>{' '}
          {item.decision
            ? `${{ APROVADA: 'Aprovada', ATENCAO: 'Atenção', REVISAR: 'Revisar' }[item.decision.classification]} (validada)`
            : item.classification
              ? {
                  APROVADA: 'Aprovada (experimental)',
                  ATENCAO: 'Atenção (experimental)',
                  REVISAR: 'Revisar (experimental)',
                }[item.classification]
              : 'Ainda não validada'}
        </Typography>
        <DualEvaluations item={item} {...evaluationContext} />
        {item.analysis_id ? (
          <Alert severity="success">
            Incluída nos gráficos e no histórico. O resultado usa a data da
            captura.
            <Button
              component={RouterLink}
              to={`/dashboard/analises/${item.analysis_id}`}
            >
              Ver análise
            </Button>
            <Button component={RouterLink} to="/dashboard">
              Ver gráficos
            </Button>
          </Alert>
        ) : item.state === 'completed' && item.source_inspection_id ? (
          <Alert severity="info">
            Classificação concluída, mas ainda não registrada nos gráficos.
            <Button disabled={publishDisabled} onClick={publish}>
              Incluir nos gráficos
            </Button>
          </Alert>
        ) : item.state === 'completed' ? (
          <Typography variant="body2">
            Amostra experimental sem sessão de captura. Não entra nos
            indicadores de inspeção.
          </Typography>
        ) : item.state === 'awaiting_review' ? (
          <Alert severity="warning">
            Ainda sem classificação de qualidade. Confira no executor a
            calibração validada e compatível com o método de segmentação.
            Detectar uma laranja não determina sua qualidade. Este resultado
            ainda não entra nos gráficos.
          </Alert>
        ) : item.state === 'not_evaluable' || item.state === 'failed' ? (
          <Alert severity="warning">
            Avaliação não concluída; o motivo aparece acima. Corrija a captura
            ou o processamento no executor antes de analisar novamente. Sem
            classificação válida, esta captura não entra nos gráficos.
          </Alert>
        ) : null}
        {item.metrics && (
          <Box
            component="dl"
            sx={{
              m: 0,
              display: 'grid',
              gridTemplateColumns: '1fr 1fr',
              gap: 1,
            }}
          >
            {[
              ['Cor laranja', formatRatio(item.metrics.orange_color_ratio)],
              [
                'Regiões anormais',
                formatRatio(item.metrics.abnormal_region_ratio),
              ],
              ['Circularidade', formatNumber(item.metrics.circularity, 3)],
              ['Assimetria', formatRatio(item.metrics.asymmetry)],
              ['Score experimental', formatNumber(item.metrics.visual_score)],
            ].map(([label, value]) => (
              <Box key={label}>
                <Typography component="dt" variant="caption">
                  {label}
                </Typography>
                <Typography component="dd" sx={{ m: 0 }}>
                  {value}
                </Typography>
              </Box>
            ))}
          </Box>
        )}
        {item.state === 'queued' && (
          <Typography variant="body2">
            {executor
              ? !executor.last_seen_at
                ? 'Nenhum contato do executor foi registrado. Inicie o consumidor de amostras no equipamento.'
                : executor.executor_state === 'error'
                  ? 'Executor informou erro. Consulte o diagnóstico do equipamento selecionado.'
                  : executor.executor_state === 'stopped'
                    ? 'Executor informou encerramento. Inicie o consumidor novamente.'
                    : !executor.executor_recent
                      ? 'Sem contato recente do executor. A imagem continua guardada na fila.'
                      : 'Executor entrou em contato recentemente. Aguardando retirada desta amostra da fila.'
              : 'Aguardando o executor do equipamento. Contato ainda não confirmado.'}
          </Typography>
        )}
        {item.state === 'processing' && item.claim_expires_at && (
          <Typography variant="body2">
            Reserva até {formatDate(item.claim_expires_at)}. Sem confirmação, o
            executor pode retomar o arquivo após o vencimento.
          </Typography>
        )}
        <Button
          variant="outlined"
          disabled={
            disabled ||
            !!item.analysis_id ||
            (item.state === 'processing' && !expiredReservation) ||
            item.state === 'queued'
          }
          onClick={queue}
        >
          {item.state === 'received'
            ? 'Enviar para análise local'
            : 'Analisar novamente'}
        </Button>
      </Stack>
    </Paper>
  );
}

function Workspace({ userId, csrf }: { userId: string; csrf: string }) {
  const client = useQueryClient();
  const key = ['private', userId, 'samples'];
  const config = useQuery({
    queryKey: [...key, 'config'],
    queryFn: ({ signal }) => samplesConfig(signal),
    retry: false,
  });
  const enabled = config.data?.enabled === true;
  const [offset, setOffset] = useState(0);
  const devices = useQuery({
    queryKey: [...key, 'devices'],
    queryFn: ({ signal }) => sampleDevices(signal),
    enabled,
    refetchInterval: 5000,
    refetchIntervalInBackground: false,
    retry: false,
  });
  const listing = useQuery({
    queryKey: [...key, 'list', offset],
    queryFn: ({ signal }) => listSamples(offset, signal),
    enabled,
    refetchInterval: 5000,
    refetchIntervalInBackground: false,
    retry: false,
  });
  const [file, setFile] = useState<File | null>(null);
  const [selection, setDevice] = useState<string | null>(null);
  const device = authorizedDeviceId(selection, devices.data);
  const selectedExecutor = devices.data?.find((item) => item.id === device);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const requestId = useRef(crypto.randomUUID());
  const lock = useRef(false);
  async function upload() {
    if (!file || lock.current) return;
    if (file.size > (config.data?.max_upload_bytes || 5242880)) {
      setError('Envie uma imagem de até 5 MiB.');
      return;
    }
    lock.current = true;
    setBusy(true);
    setError('');
    setSuccess('');
    try {
      await uploadSample(file, requestId.current, csrf);
      setSuccess(
        'Imagem recebida. Selecione o equipamento e envie a amostra para análise local.',
      );
      setOffset(0);
      await client.invalidateQueries({ queryKey: key });
    } catch (failure) {
      setError(sampleError(failure));
    } finally {
      lock.current = false;
      setBusy(false);
    }
  }
  async function enqueue(item: Sample) {
    if (!device || lock.current) return;
    lock.current = true;
    setBusy(true);
    setError('');
    setSuccess('');
    try {
      await queueSample(item.id, device, csrf);
      setSuccess(
        'Amostra enfileirada. O executor local fará o processamento quando estiver disponível.',
      );
      await client.invalidateQueries({ queryKey: key });
    } catch (failure) {
      setError(sampleError(failure));
    } finally {
      lock.current = false;
      setBusy(false);
    }
  }
  async function publish(item: Sample) {
    if (lock.current) return;
    lock.current = true;
    setBusy(true);
    setError('');
    setSuccess('');
    try {
      await publishSample(item.id, csrf);
      setSuccess(
        'Captura incluída no histórico e nos gráficos. Confira o período da captura no dashboard.',
      );
      await client.invalidateQueries({ queryKey: ['private', userId] });
    } catch (failure) {
      setError(
        failure instanceof ApiError && failure.status === 503
          ? 'A integração ainda não está ativa. O responsável deve aplicar a migration 007 e ativar inspeções na Web API.'
          : failure instanceof ApiError && failure.status === 409
            ? 'Esta captura não atende aos requisitos de publicação. Confira a sessão de origem, a classificação e a versão do algoritmo.'
            : sampleError(failure),
      );
    } finally {
      lock.current = false;
      setBusy(false);
    }
  }
  return (
    <Page
      title="Amostras"
      eyebrow="TESTE E CALIBRAÇÃO"
      description="Envie imagens e acompanhe o processamento local, mesmo sem uma laranja disponível."
      action={
        <Button
          onClick={() => {
            void config.refetch();
            if (enabled) {
              void listing.refetch();
              void devices.refetch();
            }
          }}
        >
          Atualizar amostras
        </Button>
      }
    >
      <Alert severity="info">
        Capturas de uma sessão de inspeção entram automaticamente nos gráficos
        quando possuem classificação válida e a integração está ativa. Imagens
        enviadas sem sessão continuam experimentais. O score do detector e o
        estado de processamento não são a categoria da fruta.
      </Alert>
      {enabled && config.data?.dashboard_enabled === false && (
        <Alert severity="warning">
          A integração com gráficos ainda não foi ativada.{' '}
          {config.data.dashboard_status === 'permissions_missing'
            ? 'O usuário do banco da API não possui todos os acessos necessários. O responsável deve executar o diagnóstico de permissões.'
            : config.data.dashboard_status === 'inspections_disabled'
              ? 'A API em execução não está com inspeções ativas. Confira a variável de ambiente e conclua o redeploy.'
              : 'O responsável deve conferir a migration 007 no mesmo banco utilizado pela API.'}{' '}
          As imagens continuam disponíveis nesta galeria.
        </Alert>
      )}
      {config.isPending && (
        <Typography role="status">
          Verificando disponibilidade da galeria…
        </Typography>
      )}
      {config.isError && (
        <Alert severity="error">
          Não foi possível consultar a disponibilidade das amostras. Tente
          atualizar.
        </Alert>
      )}
      {config.data && !enabled && (
        <Alert severity="warning">
          A galeria ainda não foi ativada neste ambiente. O responsável deve
          aplicar as migrations de amostras privadas (003, 004 e 005) e
          atualizar esta página.
        </Alert>
      )}
      {enabled && (
        <>
          {error && <Alert severity="error">{error}</Alert>}
          {success && <Alert severity="success">{success}</Alert>}
          <Paper variant="outlined" sx={{ p: { xs: 2, sm: 3 } }}>
            <Stack spacing={2}>
              <Typography component="h2" variant="h6">
                Enviar uma imagem
              </Typography>
              <Typography variant="body2">
                JPEG, PNG ou WebP estático · até 5 MiB e 16 milhões de pixels. A
                API remove metadados e reduz para até 1600 px no maior lado.
              </Typography>
              <Box
                component="input"
                aria-label="Selecionar imagem de amostra"
                type="file"
                accept="image/jpeg,image/png,image/webp"
                disabled={busy}
                sx={{
                  maxWidth: '100%',
                  minHeight: 44,
                  font: 'inherit',
                  '&::file-selector-button': {
                    minHeight: 44,
                    px: 1.5,
                    mr: 1,
                    border: '1px solid',
                    borderColor: 'divider',
                    borderRadius: 1,
                    bgcolor: 'background.paper',
                    cursor: 'pointer',
                  },
                }}
                onChange={(event) => {
                  setFile(event.target.files?.[0] || null);
                  requestId.current = crypto.randomUUID();
                  setError('');
                  setSuccess('');
                }}
              />
              <Button
                variant="contained"
                disabled={!file || busy}
                onClick={() => void upload()}
                sx={{ alignSelf: 'flex-start' }}
              >
                {busy ? 'Aguarde…' : 'Enviar imagem'}
              </Button>
            </Stack>
          </Paper>
          <Paper variant="outlined" sx={{ p: { xs: 2, sm: 3 } }}>
            <Stack spacing={2}>
              <Typography component="h2" variant="h6">
                Equipamento de processamento
              </Typography>
              {devices.isPending ? (
                <Typography role="status">Consultando equipamentos…</Typography>
              ) : devices.isError ? (
                <Alert severity="error">
                  Não foi possível consultar os equipamentos autorizados.
                </Alert>
              ) : devices.data?.length === 0 ? (
                <Alert
                  severity="info"
                  action={
                    <Button component={RouterLink} to="/dashboard/dispositivos">
                      Equipamentos
                    </Button>
                  }
                >
                  Nenhum equipamento autorizado para esta conta. Você pode
                  guardar as imagens; cadastre um equipamento em Equipamentos ou
                  solicite a confirmação de um vínculo anterior.
                </Alert>
              ) : (
                <TextField
                  select
                  label="Equipamento autorizado"
                  value={device}
                  disabled={busy}
                  onChange={(event) => setDevice(event.target.value)}
                  sx={{ maxWidth: 480 }}
                >
                  <MenuItem value="">Selecione um equipamento</MenuItem>
                  {devices.data?.map((item) => (
                    <MenuItem key={item.id} value={item.id}>
                      {item.name}
                    </MenuItem>
                  ))}
                </TextField>
              )}
              {selectedExecutor && (
                <Alert
                  severity={
                    selectedExecutor.executor_state === 'error'
                      ? 'error'
                      : selectedExecutor.executor_recent &&
                          selectedExecutor.executor_state === 'ready'
                        ? 'success'
                        : 'warning'
                  }
                >
                  {!selectedExecutor.last_seen_at
                    ? 'Nenhum contato do executor foi registrado. Inicie o consumidor no equipamento.'
                    : !selectedExecutor.executor_recent
                      ? `Sem contato recente do executor. Último contato: ${formatDate(selectedExecutor.last_seen_at)}.`
                      : `Contato recente registrado: ${formatDate(selectedExecutor.last_seen_at)}.`}{' '}
                  {selectedExecutor.executor_message || ''}{' '}
                  {selectedExecutor.model_version
                    ? `Modelo: ${selectedExecutor.model_version}.`
                    : 'Nenhum modelo de IA informado.'}
                  <Typography component="p" variant="body2" sx={{ mt: 1 }}>
                    Estado informado pelo executor:{' '}
                    {executorStateLabel(selectedExecutor.executor_state)}.
                  </Typography>
                </Alert>
              )}
              <Typography variant="body2" color="text.secondary">
                Selecione o equipamento antes de enfileirar. No PC ou Raspberry
                configurado, execute{' '}
                <Box component="code">
                  python -m backend.device samples --loop --ai
                </Box>
                . Sem calibração, o resultado ficará aguardando avaliação.
              </Typography>
            </Stack>
          </Paper>
          {listing.isPending && (
            <Typography role="status">Carregando suas amostras…</Typography>
          )}
          {listing.isError && (
            <Alert severity="error">
              Não foi possível atualizar a galeria. Resultados já carregados
              podem estar desatualizados.
            </Alert>
          )}
          {listing.data?.total === 0 && (
            <Alert severity="info">
              Você ainda não enviou amostras. Escolha uma imagem para começar.
            </Alert>
          )}
          <Box
            sx={{
              display: 'grid',
              gridTemplateColumns: {
                xs: 'minmax(0,1fr)',
                md: 'repeat(2,minmax(0,1fr))',
                xl: 'repeat(3,minmax(0,1fr))',
              },
              gap: 2,
            }}
          >
            {listing.data?.items.map((item) => (
              <SampleCard
                key={item.id}
                item={item}
                queue={() => void enqueue(item)}
                publish={() => void publish(item)}
                publishDisabled={
                  busy || config.data?.dashboard_enabled === false
                }
                evaluationContext={{
                  userId,
                  csrf,
                  enabled: config.data?.evaluations_enabled === true,
                  geminiEnabled: config.data?.gemini_enabled === true,
                  canAdopt: config.data?.dashboard_enabled === true,
                }}
                observedAt={listing.dataUpdatedAt}
                executor={devices.data?.find(
                  (executor) => executor.id === item.device_id,
                )}
                disabled={
                  busy || !device || devices.isError || devices.isPending
                }
              />
            ))}
          </Box>
          {listing.data && listing.data.total > 0 && (
            <Stack
              component="nav"
              aria-label="Paginação das amostras"
              direction="row"
              sx={{ gap: 1, alignItems: 'center', flexWrap: 'wrap' }}
            >
              <Button
                disabled={offset === 0 || listing.isFetching}
                onClick={() => setOffset(Math.max(0, offset - 20))}
              >
                Anterior
              </Button>
              <Typography variant="body2">
                Página {Math.floor(offset / 20) + 1} · {listing.data.total}{' '}
                amostras
              </Typography>
              <Button
                disabled={
                  offset + 20 >= listing.data.total || listing.isFetching
                }
                onClick={() => setOffset(offset + 20)}
              >
                Próxima
              </Button>
            </Stack>
          )}
        </>
      )}
    </Page>
  );
}

export default function SamplesPage() {
  const { session } = useSession();
  return session ? (
    <Workspace
      key={session.user.id}
      userId={session.user.id}
      csrf={session.csrf_token}
    />
  ) : null;
}
