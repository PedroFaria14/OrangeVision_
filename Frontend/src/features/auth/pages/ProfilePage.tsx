import { Page } from '@/shared/ui/Page';
import { useSession } from '../hooks/useSession';

export default function ProfilePage() {
  const { session } = useSession();
  if (!session) return null;
  return (
    <Page
      title="Meu perfil"
      description="Dados da sua conta, em modo de consulta."
    >
      <p>
        <label htmlFor="profile-name">Nome completo</label>{' '}
        <input id="profile-name" readOnly value={session.user.name} />
      </p>
      <p>
        <label htmlFor="profile-email">E-mail</label>{' '}
        <input id="profile-email" readOnly value={session.user.email} />
      </p>
      <p>
        Edição de perfil e alteração de senha não estão disponíveis nesta etapa.
      </p>
    </Page>
  );
}
