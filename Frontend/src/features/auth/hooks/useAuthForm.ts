import { useRef, useState, type FormEvent } from 'react';
import { ApiError } from '@/shared/api/client';
import {
  validateAuthForm,
  type AuthFormErrors,
  type AuthFormValues,
} from '../model/form_validation';

export function useAuthForm(
  registering: boolean,
  submit: (data: AuthFormValues) => Promise<void>,
) {
  const lock = useRef(false);
  const [busy, setBusy] = useState(false);
  const [show, setShow] = useState(false);
  const [error, setError] = useState('');
  const [fields, setFields] = useState<AuthFormErrors>({});

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (lock.current) return;
    const form = event.currentTarget;
    const validation = validateAuthForm(new FormData(form), registering);
    setError('');
    setFields(validation.success ? {} : validation.errors);
    if (!validation.success) return;
    lock.current = true;
    setBusy(true);
    try {
      await submit(validation.data);
    } catch (failure) {
      setError(
        failure instanceof ApiError && failure.status === 401
          ? 'E-mail ou senha inválidos.'
          : failure instanceof ApiError && failure.status === 409
            ? 'Não foi possível cadastrar com os dados informados.'
            : failure instanceof ApiError
              ? failure.message
              : 'Serviço indisponível. Tente novamente.',
      );
    } finally {
      form
        .querySelectorAll<HTMLInputElement>(
          'input[name="password"], input[name="confirmation"]',
        )
        .forEach((input) => {
          input.value = '';
        });
      lock.current = false;
      setBusy(false);
    }
  }

  return {
    busy,
    show,
    error,
    fields,
    toggleVisibility: () => setShow((value) => !value),
    handleSubmit,
  };
}
