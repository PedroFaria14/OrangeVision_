'use client';

import dynamic from 'next/dynamic';

const Studio = dynamic(() => import('./studio-view'), {
  ssr: false,
  loading: () => <p role="status" className="studio-loading">Carregando visualização do banco…</p>,
});

export function StudioPanel() { return <Studio />; }
