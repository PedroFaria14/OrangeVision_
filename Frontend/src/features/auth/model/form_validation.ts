import { z } from 'zod';

const credentialsSchema = z.object({
  email: z.string().email('Informe um e-mail válido.').max(254),
  password: z
    .string()
    .min(12, 'Use pelo menos 12 caracteres.')
    .max(128, 'Use até 128 caracteres.'),
});

export type AuthFormValues = { name: string; email: string; password: string };
export type AuthFormErrors = Record<string, string>;
type ValidationResult =
  | { success: true; data: AuthFormValues }
  | { success: false; errors: AuthFormErrors };

// Somente UX. A API repete as verificações indispensáveis antes de autenticar/gravar.
export function validateAuthForm(
  data: FormData,
  registering: boolean,
): ValidationResult {
  const parsed = credentialsSchema.safeParse({
    email: data.get('email'),
    password: data.get('password'),
  });
  const errors: AuthFormErrors = {};
  if (!parsed.success) {
    for (const issue of parsed.error.issues)
      errors[String(issue.path[0])] = issue.message;
  }
  const name = String(data.get('name') || '').trim();
  if (registering && (name.length < 2 || name.length > 100))
    errors.name = 'Informe um nome entre 2 e 100 caracteres.';
  if (registering && data.get('password') !== data.get('confirmation'))
    errors.confirmation = 'As senhas não coincidem.';
  if (!parsed.success || Object.keys(errors).length)
    return { success: false, errors };
  return { success: true, data: { name, ...parsed.data } };
}
