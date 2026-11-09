import { useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  MenuItem,
  Paper,
  Stack,
  TextField,
  Typography,
} from '@mui/material';
import { Page } from '@/shared/ui/Page';
import { Icon } from '@/shared/ui/Icon';
import { formatDate } from '@/shared/lib/format';
import { Link as RouterLink } from 'react-router-dom';
import { useSession } from '@/features/auth/hooks/useSession';
import { useInspection } from '../hooks/useInspection';

function InspectionWorkspace() {
  const {
    config,
    enabled,
    devices,
    current,
    device,
    setDevice,
    busy,
    error,
    issued,
    hasAttempt,
    begin,
    end,
    sessions,
  } = useInspection();
  // Encerrar uma sessão ativa derruba a bancada até novo pareamento: pedir confirmação.
  const [confirmClose, setConfirmClose] = useState<string | null>(null);
  // Só a atualização pedida pela pessoa mostra "Atualizando…"; consultas em
  // segundo plano não fazem o botão piscar.
  const [refreshing, setRefreshing] = useState(false);
  async function refresh() {
    setRefreshing(true);
    try {
      await Promise.allSettled([
        config.refetch(),
        ...(enabled ? [devices.refetch(), current.refetch()] : []),
      ]);
    } finally {
      setRefreshing(false);
    }
  }
  return (
    <Page
      title="Inspeções"
      eyebrow="OPERAÇÃO AUTORIZADA"
      description="Identifique o operador e pareie uma sessão com o equipamento da bancada."
      action={
        <Button
          startIcon={<Icon name="refresh" />}
          loading={refreshing}
          loadingPosition="start"
          disabled={busy}
          onClick={() => void refresh()}
        >
          {refreshing ? 'Atualizando…' : 'Atualizar sessões'}
        </Button>
      }
    >
      {config.isPending && (
        <Typography role="status">
          Verificando disponibilidade do recurso opcional…
        </Typography>
      )}
      {config.isError && (
        <Alert severity="error">
          Não foi possível consultar a configuração de inspeções.
        </Alert>
      )}
      {config.data && !config.data.enabled && (
        <Alert severity="info">
          Inspeções são opcionais e estão desativadas neste ambiente. Login,
          histórico e dashboard continuam disponíveis. A ativação exige a
          migration e o provisionamento do equipamento.
        </Alert>
      )}
      {enabled && (
        <>
          <Alert severity="info">
            Uma sessão pertence à sua conta, não a quem estiver logado no
            momento da sincronização. Parear não abre a câmera remotamente.
          </Alert>
          <Paper
            variant="outlined"
            component="section"
            aria-labelledby="inspection-how-to"
            sx={{ p: { xs: 2, sm: 3 } }}
          >
            <Stack spacing={1}>
              <Typography id="inspection-how-to" component="h2" variant="h6">
                Como iniciar
              </Typography>
              <Box component="ol" sx={{ m: 0, pl: 3 }}>
                {[
                  'Selecione o equipamento autorizado e clique em “Iniciar inspeção”. O código temporário vale 5 minutos.',
                  'No Raspberry, abra a câmera (./start.sh) e aperte [P] para informar o código, ou use ./start.sh parear.',
                  'Com a sessão pareada, posicione uma laranja por vez, inteira e com fundo liso. Capture com [C] e confirme com [U].',
                  'Acompanhe em Amostras: quando a avaliação local e o Gemini concordam, ou só um deles dá categoria, o resultado entra sozinho no gráfico. Divergências aguardam sua validação.',
                  'Ao terminar, use “Encerrar inspeção”.',
                ].map((step) => (
                  <Typography key={step} component="li" variant="body2">
                    {step}
                  </Typography>
                ))}
              </Box>
            </Stack>
          </Paper>
          {error && <Alert severity="error">{error}</Alert>}
          {(devices.isError || current.isError) && (
            <Alert severity="error">
              Não foi possível consultar equipamentos/sessões. Verifique a
              conexão e tente atualizar as sessões.
            </Alert>
          )}
          <Paper variant="outlined" sx={{ p: { xs: 2, sm: 3 } }}>
            <Stack spacing={2}>
              <Typography component="h2" variant="h6">
                Iniciar uma inspeção
              </Typography>
              {devices.isPending ? (
                <Typography role="status">
                  Consultando equipamentos autorizados…
                </Typography>
              ) : devices.isError ? (
                <Typography color="text.secondary">
                  A lista de equipamentos não está disponível. Atualize as
                  sessões para tentar novamente.
                </Typography>
              ) : devices.data?.length === 0 ? (
                <Alert
                  severity="info"
                  action={
                    <Button component={RouterLink} to="/dashboard/dispositivos">
                      Equipamentos
                    </Button>
                  }
                >
                  Nenhum equipamento foi liberado para esta conta. O responsável
                  pode confirmar vínculos anteriores, ou você pode cadastrar um
                  equipamento novo em Equipamentos.
                </Alert>
              ) : (
                <>
                  <TextField
                    select
                    label="Equipamento autorizado"
                    value={device}
                    onChange={(event) => setDevice(event.target.value)}
                    disabled={busy || hasAttempt}
                    sx={{ maxWidth: 480 }}
                  >
                    <MenuItem value="">Selecione um equipamento</MenuItem>
                    {devices.data?.map((item) => (
                      <MenuItem key={item.id} value={item.id}>
                        {item.name}
                      </MenuItem>
                    ))}
                  </TextField>
                  <Button
                    variant="contained"
                    startIcon={<Icon name="device" />}
                    onClick={() => void begin()}
                    aria-describedby="inspection-start-help"
                    disabled={
                      busy ||
                      current.isPending ||
                      current.isError ||
                      !device ||
                      (!hasAttempt &&
                        sessions.some((item) => item.device_id === device))
                    }
                    sx={{ alignSelf: 'flex-start' }}
                  >
                    {busy
                      ? 'Confirmando…'
                      : hasAttempt
                        ? 'Tentar confirmar início'
                        : 'Iniciar inspeção'}
                  </Button>
                  <Typography
                    variant="body2"
                    color="text.secondary"
                    role="status"
                    id="inspection-start-help"
                  >
                    {current.isPending
                      ? 'Aguarde a consulta das sessões existentes.'
                      : current.isError
                        ? 'Atualize as sessões antes de iniciar uma inspeção.'
                        : busy
                          ? 'Aguarde a confirmação da operação.'
                          : hasAttempt
                            ? 'Existe uma tentativa pendente. Confirme seu início antes de trocar de equipamento.'
                            : !device
                              ? 'Selecione um equipamento autorizado para iniciar.'
                              : sessions.some(
                                    (item) => item.device_id === device,
                                  )
                                ? 'Este equipamento já possui uma sessão. Conclua seu encerramento antes de iniciar outra.'
                                : 'Após iniciar, informe o código temporário no executor local. A câmera é necessária para capturar; periféricos adicionais dependem da bancada.'}
                  </Typography>
                </>
              )}
            </Stack>
          </Paper>
          {current.isPending && (
            <Typography role="status">Consultando suas sessões…</Typography>
          )}
          {sessions.map((item) => (
            <Paper
              key={item.id}
              variant="outlined"
              sx={{ p: { xs: 2, sm: 3 } }}
            >
              <Stack spacing={2}>
                <Stack
                  direction="row"
                  sx={{
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    gap: 2,
                    flexWrap: 'wrap',
                  }}
                >
                  <Typography component="h2" variant="h6">
                    Operador: {item.operator_name}
                  </Typography>
                  <Chip
                    label={
                      {
                        pending: 'Aguardando pareamento',
                        active: 'Pareada',
                        closing: 'Encerramento pendente',
                        closed: 'Encerrada',
                        expired: 'Expirada',
                      }[item.state]
                    }
                    size="small"
                    variant="outlined"
                  />
                </Stack>
                <Typography variant="body2" sx={{ overflowWrap: 'anywhere' }}>
                  Sessão: {item.id}
                </Typography>
                <Typography variant="body2" sx={{ overflowWrap: 'anywhere' }}>
                  Equipamento:{' '}
                  {devices.data?.find((option) => option.id === item.device_id)
                    ?.name || item.device_id}
                </Typography>
                {item.state === 'pending' &&
                  (issued?.id === item.id ? (
                    <TextField
                      label="Código temporário de pareamento"
                      value={issued.code}
                      slotProps={{ input: { readOnly: true } }}
                      helperText={`Informe esse código no executor local do Pi. Validade: ${formatDate(item.pairing_expires_at)}. Não é uma senha de usuário.`}
                    />
                  ) : (
                    <Typography color="text.secondary" variant="body2">
                      O código não é recuperável nesta página. Se o executor já
                      tentou parear, use pair --resume no equipamento para
                      recuperar a tentativa salva. Se nenhuma tentativa foi
                      feita, cancele esta inspeção ou aguarde sua expiração
                      antes de iniciar outra com um novo código.
                    </Typography>
                  ))}
                {item.state === 'active' && (
                  <Typography variant="body2" color="text.secondary">
                    Autorização local válida até{' '}
                    {formatDate(item.authorization_expires_at)}. Isso não
                    comprova câmera online ou disponível. Se a confirmação local
                    se perdeu, use pair --resume no equipamento antes de tentar
                    criar outra sessão.
                  </Typography>
                )}
                {item.state === 'active' && (
                  <Alert severity="warning">
                    Sem internet, o equipamento pode continuar capturando até o
                    vencimento da autorização local. Um pedido de encerramento
                    remoto só será observado quando ele consultar a API
                    novamente. O operador deve encerrar localmente antes de
                    trocar de pessoa.
                  </Alert>
                )}
                {item.state === 'closing' && (
                  <Alert severity="info">
                    Sessão antiga aguardando o equipamento. Encerre agora para
                    liberar o equipamento e iniciar outra inspeção. Os registros
                    anteriores continuam com o operador original.
                  </Alert>
                )}
                <Box>
                  <Button
                    variant="outlined"
                    disabled={
                      busy || ['closed', 'expired'].includes(item.state)
                    }
                    onClick={() =>
                      item.state === 'active' || item.state === 'closing'
                        ? setConfirmClose(item.id)
                        : void end(item.id)
                    }
                  >
                    {item.state === 'pending'
                      ? 'Cancelar pareamento'
                      : 'Encerrar inspeção'}
                  </Button>
                </Box>
              </Stack>
            </Paper>
          ))}
        </>
      )}
      <Dialog
        open={confirmClose !== null}
        onClose={() => setConfirmClose(null)}
        aria-labelledby="confirm-close-title"
      >
        <DialogTitle id="confirm-close-title">
          Encerrar esta inspeção?
        </DialogTitle>
        <DialogContent>
          <DialogContentText>
            A sessão é encerrada na hora: o Raspberry para de enviar fotos desta
            sessão e pede novo pareamento [P] em alguns segundos. Fotos tiradas
            antes do encerramento continuam valendo e ficam no histórico.
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setConfirmClose(null)}>Manter sessão</Button>
          <Button
            color="warning"
            onClick={() => {
              const id = confirmClose;
              setConfirmClose(null);
              if (id) void end(id);
            }}
          >
            Encerrar inspeção
          </Button>
        </DialogActions>
      </Dialog>
    </Page>
  );
}

export default function InspectionPage() {
  const { session } = useSession();
  return session ? <InspectionWorkspace key={session.user.id} /> : null;
}
