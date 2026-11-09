import { useState } from 'react';
import {
  Alert,
  Button,
  Paper,
  Stack,
  TextField,
  Typography,
} from '@mui/material';
import type { IssuedCredential } from '../api/devices';
import { apiOrigin } from '../model/validation';

export function IssuedCredentialPanel({
  issued,
  baseUrl,
  close,
}: {
  issued: IssuedCredential;
  baseUrl?: string | null;
  close: () => void;
}) {
  const [origin, setOrigin] = useState(
    baseUrl || (location.protocol === 'https:' ? location.origin : ''),
  );
  const [visible, setVisible] = useState(false);
  const [copied, setCopied] = useState(false);
  const [copyError, setCopyError] = useState(false);
  const validOrigin = apiOrigin(origin);
  async function copyConfig() {
    if (!issued.credential || !validOrigin) return;
    try {
      await navigator.clipboard.writeText(
        `DEVICE_ID=${issued.device.id}\nWEB_API_BASE_URL=${validOrigin}\nDEVICE_INGEST_CREDENTIAL=${issued.credential}\n`,
      );
      setCopied(true);
      setCopyError(false);
    } catch {
      setCopyError(true);
    }
  }
  return (
    <Paper
      component="section"
      aria-labelledby="issued-credential-title"
      variant="outlined"
      sx={{ p: { xs: 2, sm: 3 } }}
    >
      <Stack spacing={2}>
        <Typography id="issued-credential-title" component="h2" variant="h6">
          Dados para conectar o Raspberry
        </Typography>
        <Typography variant="body2">
          Equipamento: <strong>{issued.device.name}</strong>. A operação foi
          confirmada no site; a conexão do Raspberry ainda precisa ser
          verificada no programa local.
        </Typography>
        {!issued.credential ? (
          <Alert severity="warning">
            Operação já confirmada. Por segurança, o segredo não é reenviado.
            Feche esta confirmação e use Gerar nova credencial se não guardou a
            primeira resposta.
          </Alert>
        ) : (
          <>
            <Alert severity="warning">
              Copie esta configuração agora. A credencial só fica nesta tela;
              sair, atualizar ou encerrar a sessão descarta sua exibição. Não
              compartilhe prints ou publique esse segredo.
            </Alert>
            <TextField
              label="ID do equipamento"
              value={issued.device.id}
              helperText="DEVICE_ID — identifica este cadastro. Preserve o mesmo ID ao atualizar a credencial."
              slotProps={{ input: { readOnly: true } }}
            />
            <TextField
              label="URL da Web API"
              value={origin}
              onChange={(event) => {
                setOrigin(event.target.value);
                setCopied(false);
              }}
              error={!validOrigin}
              helperText="WEB_API_BASE_URL — endereço usado pelo Raspberry. Somente a origem HTTPS, sem /api ou /docs. O domínio publicado do site também encaminha as chamadas à API."
            />
            <TextField
              label="Credencial de conexão"
              type={visible ? 'text' : 'password'}
              value={issued.credential}
              autoComplete="off"
              helperText="DEVICE_INGEST_CREDENTIAL — chave privada do equipamento. Não é sua senha do site nem o código temporário de uma inspeção."
              slotProps={{ input: { readOnly: true } }}
            />
            <Stack direction="row" sx={{ gap: 1, flexWrap: 'wrap' }}>
              <Button onClick={() => setVisible((value) => !value)}>
                {visible ? 'Ocultar credencial' : 'Mostrar credencial'}
              </Button>
              <Button
                variant="contained"
                disabled={!validOrigin}
                onClick={() => void copyConfig()}
              >
                Copiar configuração do Raspberry
              </Button>
            </Stack>
            {copied && (
              <Typography role="status" color="success.main">
                Configuração copiada. Informe os valores na configuração inicial
                do programa, se disponível, ou cole em device/.env no Raspberry.
              </Typography>
            )}
            {copyError && (
              <Alert severity="error">
                Não foi possível copiar automaticamente. Use os campos acima
                para preencher o arquivo privado.
              </Alert>
            )}
          </>
        )}
        <Button onClick={close} sx={{ alignSelf: 'flex-start' }}>
          {issued.credential ? 'Já guardei a credencial' : 'Fechar confirmação'}
        </Button>
      </Stack>
    </Paper>
  );
}
