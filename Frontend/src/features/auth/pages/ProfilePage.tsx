import {
  Avatar,
  Box,
  InputAdornment,
  Paper,
  Stack,
  TextField,
  Typography,
} from '@mui/material';
import { Page } from '@/shared/ui/Page';
import { Icon } from '@/shared/ui/Icon';
import { useSession } from '../hooks/useSession';

export default function ProfilePage() {
  const { session } = useSession();
  if (!session) return null;
  return (
    <Page
      title="Meu perfil"
      description="As informações da sua conta OrangeVision."
      eyebrow="MINHA CONTA"
    >
      <Paper variant="outlined" sx={{ p: { xs: 2.5, sm: 4 }, maxWidth: 760 }}>
        <Stack direction="row" sx={{ alignItems: 'center', gap: 2, mb: 4 }}>
          <Avatar
            sx={{
              width: 54,
              height: 54,
              bgcolor: '#FFF0E5',
              color: '#A3430B',
              fontWeight: 600,
            }}
          >
            {session.user.name.slice(0, 1).toUpperCase()}
          </Avatar>
          <Box>
            <Typography component="h2" variant="h6">
              Informações da conta
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Dados informados no seu cadastro.
            </Typography>
          </Box>
        </Stack>
        <Stack spacing={3}>
          <TextField
            label="Nome completo"
            value={session.user.name}
            slotProps={{
              input: {
                readOnly: true,
                startAdornment: (
                  <InputAdornment position="start">
                    <Icon name="user" />
                  </InputAdornment>
                ),
              },
            }}
          />
          <TextField
            label="E-mail"
            value={session.user.email}
            slotProps={{
              input: {
                readOnly: true,
                startAdornment: (
                  <InputAdornment position="start">
                    <Icon name="mail" />
                  </InputAdornment>
                ),
              },
            }}
          />
        </Stack>
        <Stack direction="row" sx={{ mt: 3, gap: 1, alignItems: 'flex-start' }}>
          <Icon
            name="shield"
            sx={{ color: 'secondary.main', fontSize: 18, mt: 0.2 }}
          />
          <Typography variant="caption" color="text.secondary">
            Seus dados são exibidos em modo de consulta. A edição de perfil e a
            alteração de senha não estão disponíveis nesta etapa.
          </Typography>
        </Stack>
      </Paper>
    </Page>
  );
}
