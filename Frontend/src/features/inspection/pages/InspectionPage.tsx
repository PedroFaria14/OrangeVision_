import { Page } from '@/shared/ui/Page';
import { formatDate } from '@/shared/lib/format';
import { useInspection } from '../hooks/useInspection';

const states = {
  pending: 'Aguardando pareamento',
  active: 'Pareada',
  closing: 'Aguardando encerramento local',
  closed: 'Encerrada',
  expired: 'Expirada',
};

export default function InspectionPage() {
  const value = useInspection();
  const refresh = () => {
    void value.config.refetch();
    if (value.enabled) {
      void value.devices.refetch();
      void value.current.refetch();
    }
  };
  const blocked =
    value.busy ||
    value.current.isPending ||
    value.current.isError ||
    !value.device ||
    (!value.hasAttempt &&
      value.sessions.some((item) => item.device_id === value.device));
  return (
    <Page
      title="Inspeções"
      description="Identifique o operador e pareie o equipamento autorizado."
    >
      <button onClick={refresh}>Atualizar sessões</button>
      {value.config.isPending && (
        <p role="status">Consultando disponibilidade…</p>
      )}
      {value.config.isError && (
        <p role="alert">
          Não foi possível consultar a configuração de inspeções.
        </p>
      )}
      {value.config.data && !value.enabled && (
        <p>
          Inspeções estão desativadas neste ambiente. Dashboard, histórico e
          conta continuam disponíveis.
        </p>
      )}
      {value.enabled && (
        <>
          <p>
            A sessão pertence ao operador que iniciou a inspeção. Parear não
            abre a câmera remotamente.
          </p>
          {value.error && <p role="alert">{value.error}</p>}
          {(value.devices.isError || value.current.isError) && (
            <p role="alert">
              Não foi possível consultar equipamentos ou sessões. Atualize antes
              de iniciar.
            </p>
          )}
          <section>
            <h2>Iniciar uma inspeção</h2>
            {value.devices.isPending ? (
              <p role="status">Consultando equipamentos autorizados…</p>
            ) : value.devices.isError ? (
              <p>Lista de equipamentos indisponível.</p>
            ) : value.devices.data?.length === 0 ? (
              <p>
                Nenhum equipamento foi liberado para esta conta. O responsável
                precisa provisionar e vincular o equipamento.
              </p>
            ) : (
              <>
                <p>
                  <label htmlFor="inspection-device">
                    Equipamento autorizado
                  </label>{' '}
                  <select
                    id="inspection-device"
                    value={value.device}
                    onChange={(event) => value.setDevice(event.target.value)}
                    disabled={value.busy || value.hasAttempt}
                  >
                    <option value="">Selecione um equipamento</option>
                    {value.devices.data?.map((item) => (
                      <option key={item.id} value={item.id}>
                        {item.name}
                      </option>
                    ))}
                  </select>
                </p>
                <button
                  disabled={blocked}
                  onClick={() => void value.begin()}
                  aria-describedby="inspection-help"
                >
                  {value.busy
                    ? 'Confirmando…'
                    : value.hasAttempt
                      ? 'Tentar confirmar início'
                      : 'Iniciar inspeção'}
                </button>
                <p id="inspection-help">
                  {!value.device
                    ? 'Selecione um equipamento para iniciar.'
                    : value.current.isPending
                      ? 'Aguarde a consulta das sessões.'
                      : value.current.isError
                        ? 'Atualize as sessões antes de iniciar.'
                        : value.sessions.some(
                              (item) => item.device_id === value.device,
                            ) && !value.hasAttempt
                          ? 'Equipamento com sessão existente: conclua seu encerramento antes de iniciar outra.'
                          : 'Informe o código temporário no executor local após iniciar.'}
                </p>
              </>
            )}
          </section>
          {value.current.isPending && <p role="status">Consultando sessões…</p>}
          {value.sessions.map((item) => (
            <section key={item.id}>
              <h2>Operador: {item.operator_name}</h2>
              <p>Estado: {states[item.state]}</p>
              <p>Sessão: {item.id}</p>
              <p>
                Equipamento:{' '}
                {value.devices.data?.find(
                  (option) => option.id === item.device_id,
                )?.name || item.device_id}
              </p>
              {item.state === 'pending' &&
                (value.issued?.id === item.id ? (
                  <>
                    <p>
                      <label htmlFor={`code-${item.id}`}>
                        Código temporário de pareamento
                      </label>{' '}
                      <input
                        id={`code-${item.id}`}
                        readOnly
                        value={value.issued.code}
                        size={34}
                      />
                    </p>
                    <p>
                      Validade: {formatDate(item.pairing_expires_at)}. Não é
                      senha nem ID do equipamento.
                    </p>
                  </>
                ) : (
                  <p>
                    O código não pode ser recuperado nesta página. Se já tentou
                    parear, use pair --resume no equipamento; caso contrário,
                    cancele esta inspeção ou aguarde a expiração.
                  </p>
                ))}
              {item.state === 'active' && (
                <>
                  <p>
                    Autorização até {formatDate(item.authorization_expires_at)}.
                    Isso não comprova câmera online.
                  </p>
                  <p>
                    Sem internet, o executor pode continuar até o vencimento da
                    autorização. O encerramento remoto só será observado ao
                    consultar a API novamente.
                  </p>
                </>
              )}
              {item.state === 'closing' && (
                <p>
                  Aguarde confirmação do executor local. Registros anteriores
                  mantêm o operador original.
                </p>
              )}
              <button
                disabled={
                  value.busy ||
                  item.state === 'closing' ||
                  item.state === 'closed' ||
                  item.state === 'expired'
                }
                onClick={() => void value.end(item.id)}
              >
                {item.state === 'pending'
                  ? 'Cancelar pareamento'
                  : 'Solicitar encerramento'}
              </button>
            </section>
          ))}
        </>
      )}
    </Page>
  );
}
