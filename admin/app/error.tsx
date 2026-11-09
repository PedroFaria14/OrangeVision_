'use client';

export default function ErrorPage({ reset }: { reset: () => void }) {
  return <main className="login-page"><section className="login-panel">
    <h1>Painel indisponível</h1>
    <p role="alert">Não foi possível carregar a visualização. Tente novamente.</p>
    <button className="primary-button" onClick={reset}>Tentar novamente</button>
  </section></main>;
}
