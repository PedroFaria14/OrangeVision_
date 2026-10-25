import { useRef, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Page, QueryFeedback } from '@/shared/ui/Page';
import { ApiError } from '@/shared/api/client';
import { formatDate, formatNumber, formatRatio } from '@/shared/lib/format';
import { useSession } from '@/features/auth/hooks/useSession';
import {
  listSamples,
  queueSample,
  sampleDevices,
  samplesConfig,
  sampleStates,
  uploadSample,
  type Sample,
} from './api';

type Executor = Awaited<ReturnType<typeof sampleDevices>>[number];

function errorMessage(error: unknown) {
  if (error instanceof ApiError) {
    if (error.status === 413) return 'Imagem acima do limite de 5 MiB.';
    if (error.status === 422)
      return 'Use JPEG, PNG ou WebP estático, legível e com até 16 milhões de pixels.';
    if (error.status === 403)
      return 'Sem autorização. Confira a sessão e o equipamento.';
    if (error.status === 409)
      return 'Conflito: confira a reserva de processamento e o limite de amostras.';
  }
  return 'Não foi possível concluir a operação. Atualize e tente novamente.';
}

function ExecutorStatus({ item }: { item: Executor }) {
  return (
    <section>
      <h3>{item.name}</h3>
      <p>
        {!item.last_seen_at
          ? 'Nenhum contato do executor foi registrado. Inicie o consumidor no equipamento.'
          : !item.executor_recent
            ? `Sem contato recente. Último contato: ${formatDate(item.last_seen_at)}.`
            : `Contato recente: ${formatDate(item.last_seen_at)}.`}
      </p>
      <p>
        Estado informado: {item.executor_state || 'Não informado'}.{' '}
        {item.executor_message || ''}
      </p>
      <p>Modelo: {item.model_version || 'Nenhum modelo de IA informado'}.</p>
    </section>
  );
}

function SampleItem({
  item,
  device,
  executor,
  busy,
  observedAt,
  enqueue,
}: {
  item: Sample;
  device: string;
  executor?: Executor;
  busy: boolean;
  observedAt: number;
  enqueue: () => void;
}) {
  const [imageFailed, setImageFailed] = useState(false);
  const [maskFailed, setMaskFailed] = useState(false);
  const reserved =
    item.state === 'processing' &&
    (!item.claim_expires_at || Date.parse(item.claim_expires_at) > observedAt);
  return (
    <article>
      <h2>{item.filename}</h2>
      <p>
        <strong>Estado:</strong> <span>{sampleStates[item.state]}</span>
      </p>
      {imageFailed ? (
        <p role="alert">Imagem privada indisponível.</p>
      ) : (
        <img
          src={item.image_url}
          alt={`Amostra: ${item.filename}`}
          width={280}
          loading="lazy"
          onError={() => setImageFailed(true)}
        />
      )}
      {item.mask_url && (
        <section>
          <h3>Máscara da região candidata</h3>
          {maskFailed ? (
            <p>Máscara indisponível.</p>
          ) : (
            <img
              src={`${item.mask_url}?v=${encodeURIComponent(item.updated_at)}`}
              alt={`Máscara experimental: ${item.filename}`}
              width={280}
              loading="lazy"
              onError={() => setMaskFailed(true)}
            />
          )}
        </section>
      )}
      <p>
        {item.width} × {item.height} px · Recebida:{' '}
        {formatDate(item.created_at)}
      </p>
      {item.detection && (
        <section>
          <h3>Detecção</h3>
          <p>
            {item.detection.status === 'detected'
              ? 'Modelo sugere laranja'
              : item.detection.status === 'ambiguous'
                ? `Mais de uma candidata (${item.detection.count})`
                : 'Laranja não detectada com score suficiente'}
          </p>
          <p>
            Score do detector: {formatRatio(item.detection.score)}. Não é
            acurácia nem qualidade.
          </p>
          {item.detection.box && (
            <p>
              Região na imagem (x, y, largura, altura):{' '}
              {item.detection.box.join(', ')}.
            </p>
          )}
          <p>
            Modelo: {item.detection.model} ·{' '}
            {formatNumber(item.detection.inference_ms)} ms
          </p>
        </section>
      )}
      {item.reason && <p>{item.reason}</p>}
      <p>
        <strong>Categoria:</strong>{' '}
        {item.classification
          ? {
              APROVADA: 'Aprovada (experimental)',
              ATENCAO: 'Atenção (experimental)',
              REVISAR: 'Revisar (experimental)',
            }[item.classification]
          : 'Ainda não validada'}
      </p>
      {item.metrics && (
        <dl>
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
            <div key={label}>
              <dt>{label}</dt>
              <dd>{value}</dd>
            </div>
          ))}
        </dl>
      )}
      {item.source_inspection_id && (
        <p>Captura da câmera · sessão: {item.source_inspection_id}</p>
      )}
      {item.review_authorization_id && (
        <p>
          Foto local enviada após reconexão autorizada, preservando a origem.
        </p>
      )}
      {item.state === 'queued' && (
        <p>
          {!executor
            ? 'Aguardando o executor. Contato ainda não confirmado.'
            : !executor.last_seen_at
              ? 'Nenhum contato do executor foi registrado. Inicie o consumidor de amostras.'
              : executor.executor_state === 'error'
                ? 'O executor informou erro. Confira seu diagnóstico.'
                : !executor.executor_recent
                  ? 'Sem contato recente do executor. A imagem continua guardada na fila.'
                  : 'Executor entrou em contato recentemente. Aguardando retirada da amostra.'}
        </p>
      )}
      {item.state === 'processing' && (
        <p>
          Reserva até {formatDate(item.claim_expires_at)}. Sem confirmação, o
          executor pode retomar após o vencimento.
        </p>
      )}
      <button
        disabled={busy || !device || reserved || item.state === 'queued'}
        onClick={enqueue}
      >
        {item.state === 'received'
          ? 'Enviar para análise local'
          : 'Analisar novamente'}
      </button>
    </article>
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
  const [file, setFile] = useState<File | null>(null);
  const [device, setDevice] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const requestId = useRef(crypto.randomUUID());
  const lock = useRef(false);
  const devices = useQuery({
    queryKey: [...key, 'devices'],
    queryFn: ({ signal }) => sampleDevices(signal),
    enabled,
    retry: false,
    refetchInterval: 5000,
    refetchIntervalInBackground: false,
  });
  const listing = useQuery({
    queryKey: [...key, 'list', offset],
    queryFn: ({ signal }) => listSamples(offset, signal),
    enabled,
    retry: false,
    refetchInterval: 5000,
    refetchIntervalInBackground: false,
  });
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
      setOffset(0);
      setSuccess('Imagem recebida. Selecione o equipamento para enfileirar.');
      await client.invalidateQueries({ queryKey: key });
    } catch (failure) {
      setError(errorMessage(failure));
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
      setSuccess('Amostra enfileirada. Aguarde o executor local.');
      await client.invalidateQueries({ queryKey: key });
    } catch (failure) {
      setError(errorMessage(failure));
    } finally {
      lock.current = false;
      setBusy(false);
    }
  }
  function refresh() {
    void config.refetch();
    if (enabled) {
      void devices.refetch();
      void listing.refetch();
    }
  }
  return (
    <Page
      title="Amostras"
      description="Imagens privadas para teste e calibração, separadas das inspeções reais."
    >
      <p>
        Estas amostras não entram nas estatísticas do dashboard. Estado de
        processamento não é categoria de qualidade.
      </p>
      <button onClick={refresh}>Atualizar amostras</button>
      <QueryFeedback
        pending={config.isPending}
        error={config.error}
        retry={() => void config.refetch()}
      />
      {config.data && !enabled && (
        <p role="alert">
          A galeria ainda não foi ativada neste ambiente. A API exige as
          migrations de amostras 003, 004 e 005.
        </p>
      )}
      {enabled && (
        <>
          {error && <p role="alert">{error}</p>}
          {success && <p role="status">{success}</p>}
          <section>
            <h2>Enviar uma imagem</h2>
            <p>
              JPEG, PNG ou WebP estático · até 5 MiB e 16 milhões de pixels. A
              API normaliza para até 1600 px e remove metadados.
            </p>
            <p>
              <label htmlFor="sample-file">Selecionar imagem de amostra</label>{' '}
              <input
                id="sample-file"
                type="file"
                accept="image/jpeg,image/png,image/webp"
                disabled={busy}
                onChange={(event) => {
                  setFile(event.target.files?.[0] || null);
                  requestId.current = crypto.randomUUID();
                  setError('');
                  setSuccess('');
                }}
              />
            </p>
            <button disabled={!file || busy} onClick={() => void upload()}>
              {busy ? 'Aguarde…' : 'Enviar imagem'}
            </button>
          </section>
          <section>
            <h2>Equipamento de processamento</h2>
            <QueryFeedback
              pending={devices.isPending}
              error={devices.error}
              retry={() => void devices.refetch()}
            />
            {devices.data?.length === 0 && (
              <p>
                Nenhum equipamento autorizado para esta conta. Você pode guardar
                imagens; o processamento exige vínculo.
              </p>
            )}
            {devices.data && devices.data.length > 0 && (
              <p>
                <label htmlFor="sample-device">Equipamento autorizado</label>{' '}
                <select
                  id="sample-device"
                  value={device}
                  disabled={busy}
                  onChange={(event) => setDevice(event.target.value)}
                >
                  <option value="">Selecione um equipamento</option>
                  {devices.data.map((item) => (
                    <option value={item.id} key={item.id}>
                      {item.name}
                    </option>
                  ))}
                </select>
              </p>
            )}
            {devices.data
              ?.filter((item) => item.id === device)
              .map((item) => (
                <ExecutorStatus item={item} key={item.id} />
              ))}
            <p>
              No equipamento configurado:{' '}
              <code>python -m backend.device samples --loop --ai</code>. Sem
              calibração validada, a categoria aguarda avaliação.
            </p>
          </section>
          <QueryFeedback
            pending={listing.isPending}
            error={listing.error}
            retry={() => void listing.refetch()}
          />
          {listing.data?.total === 0 && (
            <p role="status">
              Você ainda não enviou amostras. Escolha uma imagem para começar.
            </p>
          )}
          {listing.data?.items.map((item) => (
            <SampleItem
              key={item.id}
              item={item}
              device={device}
              executor={devices.data?.find(
                (option) => option.id === item.device_id,
              )}
              busy={busy || devices.isError || devices.isPending}
              observedAt={listing.dataUpdatedAt}
              enqueue={() => void enqueue(item)}
            />
          ))}
          {listing.data && listing.data.total > 0 && (
            <nav aria-label="Paginação de amostras">
              <button
                disabled={!offset || listing.isFetching}
                onClick={() => setOffset(Math.max(0, offset - 20))}
              >
                Anterior
              </button>{' '}
              Página {Math.floor(offset / 20) + 1} · {listing.data.total}{' '}
              amostras{' '}
              <button
                disabled={
                  offset + 20 >= listing.data.total || listing.isFetching
                }
                onClick={() => setOffset(offset + 20)}
              >
                Próxima
              </button>
            </nav>
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
