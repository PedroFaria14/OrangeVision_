import { useEffect, useRef, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { ApiError } from '@/shared/api/client';
import {
  listDevices,
  registerDevice,
  rotateDeviceCredential,
  type IssuedCredential,
} from '../api/devices';
import { deviceNameSchema } from '../model/validation';

type Attempt =
  | { requestId: string; operation: 'create'; name: string }
  | { requestId: string; operation: 'rotate'; deviceId: string };

function operationError(error: unknown) {
  if (error instanceof ApiError) {
    if (error.status === 409)
      return 'Limite de equipamentos atingido ou comando em conflito. Atualize a lista.';
    if (error.status === 404 || error.status === 403)
      return 'Você não tem autorização para gerenciar esse equipamento.';
    if (error.status === 429)
      return 'Muitas emissões de credencial. Aguarde 15 minutos.';
    if (error.status === 422) return 'Confira os dados do equipamento.';
  }
  return 'Não foi possível confirmar a operação. Tente confirmar o mesmo comando, sem criar outro cadastro.';
}

export function useDevices(userId: string, csrf: string) {
  const client = useQueryClient();
  const listing = useQuery({
    queryKey: ['private', userId, 'devices'],
    queryFn: ({ signal }) => listDevices(signal),
    retry: false,
  });
  const [name, setName] = useState('');
  const [fieldError, setFieldError] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [uncertain, setUncertain] = useState(false);
  const [issued, setIssued] = useState<IssuedCredential | null>(null);
  const attempt = useRef<Attempt | null>(null);
  const lock = useRef(false);
  const active = useRef(true);
  useEffect(() => {
    active.current = true;
    return () => {
      active.current = false;
    };
  }, []);

  async function execute(command: Attempt) {
    if (lock.current) return;
    lock.current = true;
    attempt.current = command;
    setBusy(true);
    setError('');
    try {
      const result =
        command.operation === 'create'
          ? await registerDevice(command.name, command.requestId, csrf)
          : await rotateDeviceCredential(
              command.deviceId,
              command.requestId,
              csrf,
            );
      if (!active.current) return;
      // Segredo apenas neste estado transitório; nunca no cache, URL ou storage.
      setIssued(result);
      setUncertain(false);
      attempt.current = null;
      if (command.operation === 'create') setName('');
      await client.invalidateQueries({ queryKey: ['private', userId] });
    } catch (failure) {
      if (!active.current) return;
      const definitive =
        failure instanceof ApiError &&
        [400, 401, 403, 404, 409, 422, 429].includes(failure.status);
      if (definitive) attempt.current = null;
      setUncertain(!definitive);
      setError(operationError(failure));
    } finally {
      lock.current = false;
      if (active.current) setBusy(false);
    }
  }

  async function register() {
    if (lock.current || attempt.current || issued) return;
    const parsed = deviceNameSchema.safeParse(name);
    if (!parsed.success) {
      setFieldError('Informe um nome de 2 a 100 caracteres.');
      return;
    }
    setFieldError('');
    await execute({
      operation: 'create',
      name: parsed.data,
      requestId: crypto.randomUUID(),
    });
  }
  async function rotate(deviceId: string) {
    if (lock.current || attempt.current || issued) return;
    await execute({
      operation: 'rotate',
      deviceId,
      requestId: crypto.randomUUID(),
    });
  }
  async function retry() {
    if (attempt.current) await execute(attempt.current);
  }

  return {
    listing,
    name,
    setName,
    fieldError,
    busy,
    error,
    uncertain,
    issued,
    register,
    rotate,
    retry,
    clearIssued: () => setIssued(null),
  };
}
