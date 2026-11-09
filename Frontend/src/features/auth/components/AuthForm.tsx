import { Alert, Button, InputAdornment, Stack, TextField } from '@mui/material';
import { useAuthForm } from '../hooks/useAuthForm';
import type { AuthFormValues } from '../model/form_validation';
import { Icon } from '@/shared/ui/Icon';
import { PasswordField } from './PasswordField';

type Props = {
  registering: boolean;
  submit: (data: AuthFormValues) => Promise<void>;
};
export function AuthForm({ registering, submit }: Props) {
  const { busy, show, error, fields, handleSubmit, toggleVisibility } =
    useAuthForm(registering, submit);

  return (
    <Stack
      component="form"
      noValidate
      spacing={2.5}
      aria-busy={busy}
      onSubmit={(event) => void handleSubmit(event)}
    >
      {error && <Alert severity="error">{error}</Alert>}
      {registering && (
        <TextField
          name="name"
          label="Nome"
          autoComplete="name"
          disabled={busy}
          required
          error={!!fields.name}
          helperText={fields.name}
          slotProps={{
            htmlInput: { maxLength: 100 },
            input: {
              startAdornment: (
                <InputAdornment position="start">
                  <Icon name="user" sx={{ fontSize: 19, color: '#8794A3' }} />
                </InputAdornment>
              ),
            },
          }}
        />
      )}
      <TextField
        name="email"
        label="E-mail"
        type="email"
        autoComplete="username"
        disabled={busy}
        required
        error={!!fields.email}
        helperText={fields.email}
        slotProps={{
          htmlInput: { maxLength: 254 },
          input: {
            startAdornment: (
              <InputAdornment position="start">
                <Icon name="mail" sx={{ fontSize: 19, color: '#8794A3' }} />
              </InputAdornment>
            ),
          },
        }}
      />
      <PasswordField
        name="password"
        label="Senha"
        visible={show}
        toggle={toggleVisibility}
        autoComplete={registering ? 'new-password' : 'current-password'}
        error={fields.password}
        helperText="De 12 a 128 caracteres. Frases são permitidas."
        disabled={busy}
      />
      {registering && (
        <PasswordField
          name="confirmation"
          label="Confirmar senha"
          visible={show}
          toggle={toggleVisibility}
          autoComplete="new-password"
          error={fields.confirmation}
          disabled={busy}
        />
      )}
      <Button
        variant="contained"
        type="submit"
        disabled={busy}
        endIcon={!busy && <Icon name="arrow" sx={{ fontSize: 18 }} />}
        sx={{ minHeight: 48 }}
      >
        {busy ? 'Enviando…' : registering ? 'Criar conta' : 'Entrar'}
      </Button>
    </Stack>
  );
}
