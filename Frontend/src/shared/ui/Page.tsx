import type { ReactNode } from 'react';

export function Page({
  title,
  description,
  children,
}: {
  title: string;
  description?: string;
  children: ReactNode;
}) {
  return (
    <section>
      <h1>{title}</h1>
      {description && <p>{description}</p>}
      {children}
    </section>
  );
}

export function QueryFeedback({
  pending,
  error,
  retry,
}: {
  pending: boolean;
  error: unknown;
  retry?: () => void;
}) {
  if (pending) return <p role="status">Carregando…</p>;
  if (!error) return null;
  return (
    <div role="alert">
      <p>
        Não foi possível consultar os dados. Isso não significa ausência de
        registros.
      </p>
      {retry && (
        <button type="button" onClick={retry}>
          Tentar novamente
        </button>
      )}
    </div>
  );
}
