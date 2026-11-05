import { Link, Navigate, useNavigate, useSearchParams } from 'react-router-dom';
import { Page } from '@/shared/ui/Page';
import { login, register } from '../api/session';
import { useSession } from '../hooks/useSession';
import { useAuthForm } from '../hooks/useAuthForm';
import styles from '@/shared/ui/public.module.css';

export default function AuthPage({
  registering = false,
}: {
  registering?: boolean;
}) {
  const auth = useSession();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const requested = params.get('next') || '/dashboard';
  const destination = /^\/dashboard(?:\/|\?|$)/.test(requested)
    ? requested
    : '/dashboard';
  const form = useAuthForm(registering, async ({ name, email, password }) => {
    if (registering) {
      await register(name, email, password);
      navigate('/login?registered=1');
    } else {
      await auth.replace(await login(email, password));
      navigate(destination, { replace: true });
    }
  });
  if (auth.pending) return <p role="status">Consultando sessão…</p>;
  if (auth.error)
    return (
      <div role="alert">
        <p>Não foi possível consultar a sessão.</p>
        <button onClick={auth.retry}>Tentar novamente</button>
      </div>
    );
  if (auth.session) return <Navigate to={destination} replace />;
  const field = (
    name: 'name' | 'email' | 'password' | 'confirmation',
    label: string,
    type: string,
    autocomplete: string,
  ) => (
    <div className={styles.field}>
      <label htmlFor={`auth-${name}`}>{label}</label>

      <div className={styles.inputWrapper}>
        <input
          id={`auth-${name}`}
          name={name}
          type={type}
          autoComplete={autocomplete}
          required
          maxLength={name === 'email' ? 254 : name === 'name' ? 100 : 128}
          aria-invalid={!!form.fields[name]}
          aria-describedby={form.fields[name] ? `error-${name}` : undefined}
        />

        {(name === 'password' || name === 'confirmation') && (
          <button
            className={styles.passwordToggle}
            type="button"
            onClick={form.toggleVisibility}
            aria-label={`${form.show ? 'Ocultar' : 'Mostrar'} ${
              name === 'confirmation' ? 'confirmação de senha' : 'senha'
            }`}
            title={form.show ? 'Ocultar senha' : 'Mostrar senha'}
            aria-controls={`auth-${name}`}
          >
            <svg
              width="22"
              height="22"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.8"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
              focusable="false"
            >
              <path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12Z" />
              <circle cx="12" cy="12" r="3" />
              {form.show && <path d="m3 3 18 18" />}
            </svg>
          </button>
        )}
      </div>

      {form.fields[name] && (
        <span id={`error-${name}`} role="alert">
          {form.fields[name]}
        </span>
      )}
    </div>
  );
  return (
    <Page title={registering ? 'Criar conta' : 'Entrar'}>
      {params.get('registered') === '1' && (
        <p role="status">Conta criada. Entre para continuar.</p>
      )}
      <form
        noValidate
        aria-busy={form.busy}
        onSubmit={(event) => void form.handleSubmit(event)}
      >
        {form.error && <p role="alert">{form.error}</p>}
        <fieldset disabled={form.busy}>
          <legend>{registering ? 'Cadastro' : 'Acesso à conta'}</legend>
          {registering && field('name', 'Nome', 'text', 'name')}
          {field('email', 'E-mail', 'email', 'username')}
          {field(
            'password',
            'Senha',
            form.show ? 'text' : 'password',
            registering ? 'new-password' : 'current-password',
          )}
          {registering && <p>De 12 a 128 caracteres. Frases são permitidas.</p>}
          {registering &&
            field(
              'confirmation',
              'Confirmar senha',
              form.show ? 'text' : 'password',
              'new-password',
            )}

          <button type="submit">
            {form.busy ? 'Enviando…' : registering ? 'Criar conta' : 'Entrar'}
          </button>
        </fieldset>
      </form>
      <p>
        <Link to={registering ? '/login' : '/registrar'}>
          {registering ? 'Fazer login' : 'Criar uma conta'}
        </Link>
      </p>
    </Page>
  );
}
