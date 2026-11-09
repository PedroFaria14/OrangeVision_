import { useRef, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import {
  Alert,
  Box,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  MenuItem,
  Paper,
  Stack,
  TextField,
  Typography,
} from '@mui/material';
import { ApiError } from '@/shared/api/client';
import { formatDate } from '@/shared/lib/format';
import {
  adoptDecision,
  requestGemini,
  sampleStates,
  type DecisionCommand,
  type Evaluation,
  type Sample,
} from './api';

const labels = { APROVADA: 'Aprovada', ATENCAO: 'Atenção', REVISAR: 'Revisar' };
const jobLabels = {
  queued: 'Aguardando worker Gemini',
  running: 'Gemini em processamento',
  retry_wait: 'Gemini aguardando nova tentativa',
  completed: 'Avaliação Gemini recebida',
  failed: 'Gemini não concluiu a avaliação',
};
const errorLabels: Record<string, string> = {
  daily_limit:
    'Limite diário de chamadas atingido; trabalho preservado para o próximo período.',
  provider_credentials:
    'A chave ou as permissões precisam ser verificadas no servidor.',
  model_unavailable: 'O modelo configurado não está disponível.',
  provider_request_invalid:
    'A configuração da requisição ao Gemini precisa ser conferida no servidor.',
  response_invalid: 'O provedor não devolveu uma avaliação válida.',
  network_uncertain:
    'Sem confirmação da chamada externa. A nova tentativa respeita o limite de consumo.',
  lease_exhausted:
    'O processamento foi interrompido e atingiu o limite de tentativas.',
};
type Attempt =
  | { kind: 'gemini'; requestId: string }
  | { kind: 'decision'; command: DecisionCommand };

export function DualEvaluations({
  item,
  csrf,
  userId,
  enabled,
  geminiEnabled,
  canAdopt,
}: {
  item: Sample;
  csrf: string;
  userId: string;
  enabled: boolean;
  geminiEnabled: boolean;
  canAdopt: boolean;
}) {
  const client = useQueryClient();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [uncertain, setUncertain] = useState(false);
  const [dialog, setDialog] = useState<{
    evaluation: Evaluation | null;
  } | null>(null);
  const [category, setCategory] =
    useState<DecisionCommand['classification']>('REVISAR');
  const [reason, setReason] = useState('');
  const lock = useRef(false);
  const attempt = useRef<Attempt | null>(null);
  const job = item.gemini_job;
  const activeJob =
    !!job && ['queued', 'running', 'retry_wait'].includes(job.state);
  const blocked = busy || uncertain;

  async function execute(command: Attempt) {
    if (lock.current) return;
    lock.current = true;
    attempt.current = command;
    setBusy(true);
    setError('');
    try {
      if (command.kind === 'gemini')
        await requestGemini(item.id, command.requestId, csrf);
      else await adoptDecision(item.id, command.command, csrf);
      attempt.current = null;
      setUncertain(false);
      await client.invalidateQueries({ queryKey: ['private', userId] });
    } catch (failure) {
      const definitive =
        failure instanceof ApiError &&
        [400, 401, 403, 404, 409, 422, 429].includes(failure.status);
      if (definitive) attempt.current = null;
      setUncertain(!definitive);
      setError(
        failure instanceof ApiError && failure.status === 409
          ? command.kind === 'gemini'
            ? 'Já existe uma avaliação Gemini em andamento. Atualize para acompanhar o trabalho.'
            : 'A avaliação ou decisão mudou, ou a captura não possui origem autorizada. Atualize e confira antes de confirmar.'
          : failure instanceof ApiError && failure.status === 429
            ? 'Limite da fila atingido. Aguarde os trabalhos existentes.'
            : 'Operação não confirmada. Confira a ativação do serviço; em falha de comunicação, confirme o mesmo comando para evitar duplicação.',
      );
      if (definitive)
        await client.invalidateQueries({
          queryKey: ['private', userId, 'samples'],
        });
    } finally {
      lock.current = false;
      setBusy(false);
    }
  }
  const canValidate =
    enabled && canAdopt && !blocked && !!item.source_inspection_id;
  const suggestions = item.evaluations.filter(
    (value) => value.state === 'completed' && value.classification,
  );
  function quickValidate(classification: DecisionCommand['classification']) {
    // Usa a avaliação existente só quando ela já indica a mesma categoria;
    // caso contrário, registra uma decisão humana de validação visual.
    const match = suggestions.find(
      (value) => value.classification === classification,
    );
    void execute({
      kind: 'decision',
      command: {
        request_id: crypto.randomUUID(),
        expected_revision: item.decision?.revision || 0,
        evaluation_id: match?.id || null,
        classification,
        reason: match
          ? `Validação visual no site: confirmou a avaliação ${match.origin === 'local' ? 'local' : 'Gemini'}.`
          : 'Validação visual no site pelo operador.',
      },
    });
  }
  function openDecision(evaluation: Evaluation | null) {
    setDialog({ evaluation });
    setCategory(
      evaluation?.classification || item.decision?.classification || 'REVISAR',
    );
    setReason('');
  }
  return (
    <Stack spacing={2}>
      <Box
        sx={{
          display: 'grid',
          gridTemplateColumns: {
            xs: 'minmax(0,1fr)',
            sm: 'repeat(2,minmax(0,1fr))',
          },
          gap: 1.5,
        }}
      >
        {(['local', 'gemini'] as const).map((origin) => {
          const evaluation = item.evaluations.find(
            (value) => value.origin === origin,
          );
          return (
            <Paper
              key={origin}
              variant="outlined"
              component="section"
              aria-label={`Avaliação ${origin === 'local' ? 'local' : 'Gemini'} de ${item.filename}`}
              sx={{ p: 1.5, minWidth: 0 }}
            >
              <Stack spacing={1}>
                <Typography component="h3" variant="subtitle2">
                  {origin === 'local'
                    ? 'Avaliação local · Raspberry'
                    : 'Segunda opinião · Gemini'}
                </Typography>
                <Typography variant="body2">
                  {origin === 'local' ? 'Estado local: ' : ''}
                  {evaluation
                    ? sampleStates[evaluation.state]
                    : origin === 'local'
                      ? sampleStates[item.state]
                      : job
                        ? 'Acompanhando a execução no servidor'
                        : 'Ainda não solicitada'}
                </Typography>
                <Typography variant="body2">
                  <strong>
                    {evaluation?.classification
                      ? labels[evaluation.classification]
                      : origin === 'local' && item.classification
                        ? labels[item.classification]
                        : 'Sem categoria concluída'}
                  </strong>
                </Typography>
                <Typography variant="body2" sx={{ overflowWrap: 'anywhere' }}>
                  {evaluation?.reason ||
                    (origin === 'local'
                      ? 'Acompanhe o motivo e as métricas desta tentativa no cartão.'
                      : 'Avaliação visual experimental da mesma foto. Não substitui medições locais nem confirma qualidade interna.')}
                </Typography>
                {evaluation && (
                  <Typography
                    variant="caption"
                    sx={{ overflowWrap: 'anywhere' }}
                  >
                    Critérios: {evaluation.criteria_version} · Modelo/algoritmo:{' '}
                    {evaluation.model_version || 'Não informado'} ·{' '}
                    {formatDate(evaluation.created_at)}
                  </Typography>
                )}
                {origin === 'gemini' && job && (
                  <Typography variant="body2" role="status">
                    {jobLabels[job.state]} · {job.attempts} tentativa(s).{' '}
                    {job.error_code &&
                      (errorLabels[job.error_code] ||
                        'Consulte o diagnóstico do worker.')}
                  </Typography>
                )}
                {evaluation?.classification && (
                  <Button
                    disabled={
                      !canAdopt || blocked || !item.source_inspection_id
                    }
                    onClick={() => openDecision(evaluation)}
                  >
                    {origin === 'local'
                      ? 'Adotar avaliação local'
                      : 'Adotar sugestão Gemini'}
                  </Button>
                )}
                {origin === 'gemini' && (
                  <Button
                    disabled={!geminiEnabled || blocked || activeJob}
                    onClick={() =>
                      void execute({
                        kind: 'gemini',
                        requestId: crypto.randomUUID(),
                      })
                    }
                  >
                    {job ? 'Avaliar novamente com Gemini' : 'Solicitar Gemini'}
                  </Button>
                )}
              </Stack>
            </Paper>
          );
        })}
      </Box>
      {!enabled && (
        <Typography variant="body2">
          As avaliações independentes precisam da migration 008. O processamento
          local existente continua disponível.
        </Typography>
      )}
      {enabled && !geminiEnabled && (
        <Typography variant="body2">
          Gemini desativado no servidor. O responsável deve conferir
          WEB_GEMINI_ENABLED e a configuração do worker.
        </Typography>
      )}
      <Typography variant="body2">
        {item.comparison === 'agreement'
          ? 'As categorias das duas avaliações concordam. Isso não comprova acurácia.'
          : item.comparison === 'divergence'
            ? 'Avaliações divergentes. Revise a foto e confirme qual resultado adotar.'
            : item.comparison === 'inconclusive'
              ? 'Comparação inconclusiva: uma avaliação não produziu categoria.'
              : !job &&
                  !item.evaluations.some((value) => value.origin === 'gemini')
                ? 'Segunda opinião opcional: use “Solicitar Gemini” se quiser comparar com outra IA.'
                : 'Comparação aguardando as duas avaliações concluídas.'}
      </Typography>
      {item.decision && (
        <Alert severity="info">
          Resultado adotado: {labels[item.decision.classification]} · origem{' '}
          {item.decision.origin} · revisão {item.decision.revision}.{' '}
          {item.decision.reason}
        </Alert>
      )}
      {!item.decision && item.analysis_id && (
        <Typography variant="body2">
          Resultado local registrado automaticamente. Uma segunda opinião não
          altera os gráficos sem confirmação.
        </Typography>
      )}
      {!item.decision && (
        <Paper
          variant="outlined"
          component="section"
          aria-label={`Validação visual de ${item.filename}`}
          sx={{ p: 1.5 }}
        >
          <Stack spacing={1}>
            <Typography component="h3" variant="subtitle2">
              Validar esta laranja
            </Typography>
            <Typography variant="body2">
              Olhe a foto e escolha a categoria. A sua escolha entra no
              histórico e nos gráficos, uma única vez por captura.
            </Typography>
            <Stack direction="row" sx={{ gap: 1, flexWrap: 'wrap' }}>
              {(Object.keys(labels) as DecisionCommand['classification'][]).map(
                (value) => (
                  <Button
                    key={value}
                    variant="outlined"
                    disabled={!canValidate}
                    onClick={() => quickValidate(value)}
                  >
                    Validar como {labels[value]}
                  </Button>
                ),
              )}
            </Stack>
            {!item.source_inspection_id && (
              <Typography variant="caption">
                Esta foto não veio de uma sessão de inspeção e não pode entrar
                nos gráficos.
              </Typography>
            )}
          </Stack>
        </Paper>
      )}
      <Button
        disabled={
          !enabled || !canAdopt || blocked || !item.source_inspection_id
        }
        onClick={() => openDecision(null)}
      >
        {item.decision
          ? 'Corrigir resultado com justificativa'
          : 'Confirmar ou corrigir resultado'}
      </Button>
      <Typography variant="caption">
        O Gemini pode demorar ou ficar indisponível; a avaliação local é
        independente. Novas solicitações podem consumir a cota paga do servidor.
      </Typography>
      {error && <Alert severity="error">{error}</Alert>}
      {uncertain && (
        <Button
          disabled={busy}
          onClick={() => attempt.current && void execute(attempt.current)}
        >
          Confirmar o mesmo comando
        </Button>
      )}
      <Dialog
        open={!!dialog}
        onClose={() => setDialog(null)}
        aria-labelledby={`decision-${item.id}`}
        fullWidth
        maxWidth="sm"
      >
        <Box
          component="form"
          onSubmit={(event) => {
            event.preventDefault();
            if (reason.trim().length < 5) return;
            const command: DecisionCommand = {
              request_id: crypto.randomUUID(),
              expected_revision: item.decision?.revision || 0,
              evaluation_id: dialog?.evaluation?.id || null,
              classification: category,
              reason: reason.trim(),
            };
            setDialog(null);
            void execute({ kind: 'decision', command });
          }}
        >
          <DialogTitle id={`decision-${item.id}`}>
            Confirmar resultado adotado
          </DialogTitle>
          <DialogContent>
            <Stack spacing={2} sx={{ pt: 1 }}>
              <Typography variant="body2">
                A decisão será registrada com sua conta e justificativa. A mesma
                captura continuará contando uma única vez nos gráficos.
              </Typography>
              <TextField
                select
                label="Categoria adotada"
                value={category}
                disabled={!!dialog?.evaluation}
                onChange={(event) =>
                  setCategory(
                    event.target.value as DecisionCommand['classification'],
                  )
                }
              >
                {Object.entries(labels).map(([value, label]) => (
                  <MenuItem key={value} value={value}>
                    {label}
                  </MenuItem>
                ))}
              </TextField>
              <TextField
                label="Justificativa da decisão"
                value={reason}
                onChange={(event) => setReason(event.target.value)}
                required
                multiline
                minRows={2}
                helperText="De 5 a 1000 caracteres. Registre por que confirmou ou corrigiu a avaliação."
                slotProps={{ htmlInput: { minLength: 5, maxLength: 1000 } }}
              />
            </Stack>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setDialog(null)}>Cancelar</Button>
            <Button type="submit" disabled={reason.trim().length < 5}>
              Confirmar decisão
            </Button>
          </DialogActions>
        </Box>
      </Dialog>
    </Stack>
  );
}
