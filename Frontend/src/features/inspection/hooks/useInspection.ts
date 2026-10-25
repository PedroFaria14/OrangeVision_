import { useRef, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { ApiError } from '@/shared/api/client';
import { useSession } from '@/features/auth/hooks/useSession';
import {
  closeInspection,
  currentInspections,
  inspectionDevices,
  startInspection,
} from '../api/inspections';
import { useInspectionConfig } from './useInspectionConfig';

type Attempt = { device_id: string; request_id: string; pairing_code: string };
function createCode() {
  return Array.from(crypto.getRandomValues(new Uint8Array(16)), (value) =>
    value.toString(16).padStart(2, '0'),
  ).join('');
}

export function useInspection() {
  const { session } = useSession();
  const config = useInspectionConfig();
  const client = useQueryClient();
  const key = ['private', session?.user.id, 'inspections'];
  const enabled = !!session && config.data?.enabled === true;
  const devices = useQuery({
    queryKey: [...key, 'devices'],
    queryFn: ({ signal }) => inspectionDevices(signal),
    enabled,
  });
  const current = useQuery({
    queryKey: [...key, 'current'],
    queryFn: ({ signal }) => currentInspections(signal),
    enabled,
    refetchInterval: 10000,
    refetchIntervalInBackground: false,
  });
  const [device, setDevice] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [issued, setIssued] = useState<{ id: string; code: string } | null>(
    null,
  );
  const [hasAttempt, setHasAttempt] = useState(false);
  const lock = useRef(false);
  const attempt = useRef<Attempt | null>(null);
  async function begin() {
    if (!session || lock.current || !device) return;
    lock.current = true;
    setBusy(true);
    setError('');
    attempt.current ??= {
      device_id: device,
      request_id: crypto.randomUUID(),
      pairing_code: createCode(),
    };
    const command = attempt.current;
    setHasAttempt(true);
    try {
      const result = await startInspection(command, session.csrf_token);
      if (result.state === 'pending')
        setIssued({ id: result.id, code: command.pairing_code });
      attempt.current = null;
      setHasAttempt(false);
      await client.invalidateQueries({ queryKey: key });
    } catch (failure) {
      if (
        failure instanceof ApiError &&
        [400, 403, 404, 409, 422].includes(failure.status)
      ) {
        attempt.current = null;
        setHasAttempt(false);
      }
      setError(
        failure instanceof ApiError && failure.status === 409
          ? 'Equipamento ocupado ou comando conflitante. Atualize a sessão antes de tentar novamente.'
          : 'Início não confirmado. Atualize as sessões ou repita o mesmo comando; nenhuma captura será iniciada automaticamente.',
      );
    } finally {
      lock.current = false;
      setBusy(false);
    }
  }
  async function end(id: string) {
    if (!session || lock.current) return;
    lock.current = true;
    setBusy(true);
    setError('');
    try {
      await closeInspection(id, session.csrf_token);
      if (issued?.id === id) setIssued(null);
      await client.invalidateQueries({ queryKey: key });
    } catch {
      setError(
        'Não foi possível confirmar o pedido de encerramento. Consulte a sessão antes de trocar de operador.',
      );
    } finally {
      lock.current = false;
      setBusy(false);
    }
  }
  return {
    config,
    enabled,
    devices,
    current,
    device,
    setDevice,
    busy,
    error,
    issued,
    hasAttempt,
    begin,
    end,
    sessions: current.data || [],
  };
}
