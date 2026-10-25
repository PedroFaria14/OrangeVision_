import { Link, Navigate, useNavigate, useSearchParams } from 'react-router-dom';
import { Page } from '@/shared/ui/Page';
import { login, register } from '../api/session';
import { useSession } from '../hooks/useSession';
import { useAuthForm } from '../hooks/useAuthForm';

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
    <p>
      <label htmlFor={`auth-${name}`}>{label}</label>{' '}
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
      {form.fields[name] && (
        <span id={`error-${name}`} role="alert">
          {' '}
          {form.fields[name]}
        </span>
      )}
    </p>
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
          <p>De 12 a 128 caracteres. Frases são permitidas.</p>
          {registering &&
            field(
              'confirmation',
              'Confirmar senha',
              form.show ? 'text' : 'password',
              'new-password',
            )}
          <button type="button" onClick={form.toggleVisibility}>
            {form.show ? 'Ocultar senha' : 'Mostrar senha'}
          </button>{' '}
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
