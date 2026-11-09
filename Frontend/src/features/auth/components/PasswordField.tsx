import { IconButton, InputAdornment, TextField } from '@mui/material';
import { Icon } from '@/shared/ui/Icon';

type Props = {
  name: 'password' | 'confirmation';
  label: string;
  visible: boolean;
  toggle: () => void;
  error?: string;
  helperText?: string;
  autoComplete: 'current-password' | 'new-password';
  disabled?: boolean;
};
export function PasswordField({
  name,
  label,
  visible,
  toggle,
  error,
  helperText,
  autoComplete,
  disabled = false,
}: Props) {
  return (
    <TextField
      name={name}
      label={label}
      type={visible ? 'text' : 'password'}
      autoComplete={autoComplete}
      disabled={disabled}
      required
      error={!!error}
      helperText={error || helperText}
      slotProps={{
        htmlInput: { maxLength: 128 },
        input: {
          startAdornment: (
            <InputAdornment position="start">
              <Icon name="lock" sx={{ fontSize: 19, color: '#8794A3' }} />
            </InputAdornment>
          ),
          endAdornment: (
            <InputAdornment position="end">
              <IconButton
                aria-label={`${visible ? 'Ocultar' : 'Mostrar'} ${name === 'confirmation' ? 'confirmação de senha' : 'senha'}`}
                aria-pressed={visible}
                disabled={disabled}
                onClick={toggle}
                edge="end"
                size="small"
              >
                <Icon name={visible ? 'eyeOff' : 'eye'} sx={{ fontSize: 20 }} />
              </IconButton>
            </InputAdornment>
          ),
        },
      }}
    />
  );
}
