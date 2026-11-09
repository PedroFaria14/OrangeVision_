import { useState } from 'react';
import { ZodError } from 'zod';
import {
  Alert,
  Box,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  Paper,
  Stack,
  TextField,
  Typography,
} from '@mui/material';
import { ApiError } from '@/shared/api/client';
import { Page } from '@/shared/ui/Page';
import { formatDate } from '@/shared/lib/format';
import { useSession } from '@/features/auth/hooks/useSession';
import { useDevices } from '../hooks/useDevices';
import type { UserDevice } from '../api/devices';
import { IssuedCredentialPanel } from '../components/IssuedCredentialPanel';
import { RaspberryConnectionGuide } from '../components/RaspberryConnectionGuide';

function DevicesWorkspace({ userId, csrf }: { userId: string; csrf: string }) {
  const {
    listing,
    name,
    setName,
    fieldError,
    busy,
    error,
    uncertain,
    issued,
    register,
    rotate,
    retry,
    clearIssued,
  } = useDevices(userId, csrf);
  const [rotating, setRotating] = useState<UserDevice | null>(null);
  const data = listing.data;
  const atLimit = !!data && data.managed_count >= data.max_devices;
  const blocked = busy || uncertain || !!issued;
  return (
    <Page
      title="Equipamentos"
      eyebrow="SEUS DISPOSITIVOS"
      description="Cadastre seus equipamentos e prepare a conexão com o Raspberry. Cadastrar não inicia a câmera ou uma inspeção."
      action={
        <Button disabled={busy} onClick={() => void listing.refetch()}>
          Atualizar equipamentos
        </Button>
      }
    >
      {listing.isPending && (
        <Typography role="status">Consultando seus equipamentos…</Typography>
      )}
      {listing.isError && (
        <Alert
          severity="error"
          action={
            <Button onClick={() => void listing.refetch()}>
              Tentar novamente
            </Button>
          }
        >
          {listing.error instanceof ApiError && listing.error.status === 404
            ? 'O cadastro de equipamentos ainda não foi publicado na Web API. Atualize o serviço no Render.'
            : listing.error instanceof ZodError
              ? 'A resposta da API é incompatível com esta versão do cadastro.'
              : 'Não foi possível consultar seus equipamentos. A lista não foi confirmada.'}
        </Alert>
      )}
      {error && <Alert severity="error">{error}</Alert>}
      {uncertain && (
        <Alert
          severity="warning"
          action={
            <Button disabled={busy} onClick={() => void retry()}>
              Tentar confirmar operação
            </Button>
          }
        >
          Existe uma operação sem confirmação. A tentativa mantém o mesmo
          identificador para evitar duplicação.
        </Alert>
      )}
      {issued && (
        <IssuedCredentialPanel
          key={issued.device.id}
          issued={issued}
          baseUrl={data?.api_base_url}
          close={clearIssued}
        />
      )}
      {data && (
        <>
          {!data.items.length && !listing.isError && (
            <Alert severity="info">
              Você ainda não tem equipamentos vinculados. Cadastre um Raspberry
              abaixo para começar.
            </Alert>
          )}
          {!data.registration_enabled && (
            <Alert severity="warning">
              O cadastro ainda não foi ativado neste ambiente. O responsável
              deve revisar e aplicar a migration 006 na Web API.
            </Alert>
          )}
          <Paper
            component="section"
            aria-labelledby="register-device-title"
            variant="outlined"
            sx={{ p: { xs: 2, sm: 3 } }}
          >
            <Stack
              component="form"
              spacing={2}
              noValidate
              onSubmit={(event) => {
                event.preventDefault();
                void register();
              }}
              aria-busy={busy}
            >
              <Typography
                id="register-device-title"
                component="h2"
                variant="h6"
              >
                {data.items.length
                  ? 'Cadastrar outro equipamento'
                  : 'Cadastrar equipamento'}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {data.managed_count} de {data.max_devices} cadastros próprios
                utilizados. Equipamentos anteriores ou compartilhados continuam
                disponíveis conforme seus vínculos.
              </Typography>
              {atLimit && (
                <Alert severity="info">
                  O limite de equipamentos cadastrados por esta conta foi
                  atingido.
                </Alert>
              )}
              <TextField
                label="Nome do equipamento"
                value={name}
                onChange={(event) => setName(event.target.value)}
                required
                disabled={
                  blocked ||
                  atLimit ||
                  !data.registration_enabled ||
                  listing.isError
                }
                error={!!fieldError}
                helperText={
                  fieldError ||
                  'De 2 a 100 caracteres. Exemplo: Raspberry Bancada 1.'
                }
                slotProps={{ htmlInput: { maxLength: 100 } }}
                sx={{ maxWidth: 480 }}
              />
              <Button
                type="submit"
                variant="contained"
                disabled={
                  blocked ||
                  atLimit ||
                  !data.registration_enabled ||
                  listing.isError
                }
                sx={{ alignSelf: 'flex-start' }}
              >
                {busy ? 'Confirmando…' : 'Cadastrar equipamento'}
              </Button>
            </Stack>
          </Paper>
          <RaspberryConnectionGuide />
          <Box
            sx={{
              display: 'grid',
              gridTemplateColumns: {
                xs: 'minmax(0, 1fr)',
                md: 'repeat(2, minmax(0, 1fr))',
              },
              gap: 2,
            }}
          >
            {data.items.map((device) => (
              <Paper
                component="article"
                variant="outlined"
                key={device.id}
                sx={{ p: { xs: 2, sm: 3 }, minWidth: 0 }}
              >
                <Stack spacing={2}>
                  <Typography
                    component="h2"
                    variant="h6"
                    sx={{ overflowWrap: 'anywhere' }}
                  >
                    {device.name}
                  </Typography>
                  <Typography variant="body2" sx={{ overflowWrap: 'anywhere' }}>
                    ID do equipamento (DEVICE_ID): {device.id}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Cadastrado em: {formatDate(device.created_at)}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Cadastro não confirma contato do executor, câmera disponível
                    ou inspeção ativa.
                  </Typography>
                  {device.can_manage_credentials ? (
                    <Button
                      variant="outlined"
                      disabled={
                        blocked || !data.registration_enabled || listing.isError
                      }
                      onClick={() => setRotating(device)}
                    >
                      Gerar nova credencial
                    </Button>
                  ) : (
                    <Typography variant="body2" color="text.secondary">
                      Equipamento vinculado ou de cadastro anterior. A gestão da
                      credencial depende da confirmação administrativa do
                      proprietário.
                    </Typography>
                  )}
                </Stack>
              </Paper>
            ))}
          </Box>
        </>
      )}
      <Dialog
        open={!!rotating}
        onClose={() => setRotating(null)}
        aria-labelledby="rotate-credential-title"
      >
        <DialogTitle id="rotate-credential-title">
          Gerar nova credencial?
        </DialogTitle>
        <DialogContent>
          <DialogContentText>
            A credencial anterior de {rotating?.name} será revogada. Atualize o
            .env do Raspberry com a nova credencial para retomar as
            solicitações. O dispositivo e seu histórico serão preservados.
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setRotating(null)}>Cancelar</Button>
          <Button
            onClick={() => {
              const device = rotating;
              setRotating(null);
              if (device) void rotate(device.id);
            }}
          >
            Confirmar nova credencial
          </Button>
        </DialogActions>
      </Dialog>
    </Page>
  );
}

export default function DevicesPage() {
  const { session } = useSession();
  return session ? (
    <DevicesWorkspace
      key={session.user.id}
      userId={session.user.id}
      csrf={session.csrf_token}
    />
  ) : null;
}
