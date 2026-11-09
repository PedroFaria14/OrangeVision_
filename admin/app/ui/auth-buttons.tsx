'use client';

import { signIn, signOut } from 'next-auth/react';
import { useState } from 'react';

export function LoginButton() {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(false);
  return <>
    <button className="primary-button" disabled={busy} onClick={async () => {
      setBusy(true); setError(false);
      try { await signIn('github', { callbackUrl: '/' }); }
      catch { setError(true); setBusy(false); }
    }}>{busy ? 'Abrindo GitHub…' : 'Entrar com GitHub'}</button>
    {error && <p role="alert" className="notice">Falha ao iniciar o login. Tente novamente.</p>}
  </>;
}

export function LogoutButton() {
  return <button className="secondary-button" onClick={() => void signOut({ callbackUrl: '/login' })}>Sair</button>;
}
