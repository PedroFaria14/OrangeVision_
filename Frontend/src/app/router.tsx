import { Suspense } from 'react';
import { createBrowserRouter, Link } from 'react-router-dom';
import { Layout, ProtectedLayout, RouteError } from './layout';
import type { ContentSlug } from '@/features/institutional/content';
import {
  Home,
  Content,
  Auth,
  Profile,
  Dashboard,
  Detail,
  Inspections,
  Samples,
} from './lazy_pages';
const load = (node: React.ReactNode) => (
  <Suspense fallback={<p role="status">Carregando página…</p>}>{node}</Suspense>
);

export const router = createBrowserRouter([
  {
    element: <Layout />,
    errorElement: <RouteError />,
    children: [
      { index: true, element: load(<Home />) },
      ...(
        [
          'projeto',
          'planejamento',
          'desenvolvimento',
          'resultados',
          'equipe',
          'referencias',
        ] satisfies ContentSlug[]
      ).map((slug) => ({ path: slug, element: load(<Content slug={slug} />) })),
      { path: 'login', element: load(<Auth />) },
      { path: 'registrar', element: load(<Auth registering />) },
      {
        element: <ProtectedLayout />,
        children: [
          { path: 'dashboard', element: load(<Dashboard />) },
          {
            path: 'dashboard/historico',
            element: load(<Dashboard historyOnly />),
          },
          { path: 'dashboard/analises/:id', element: load(<Detail />) },
          { path: 'dashboard/perfil', element: load(<Profile />) },
          { path: 'dashboard/inspecoes', element: load(<Inspections />) },
          { path: 'dashboard/amostras', element: load(<Samples />) },
        ],
      },
      {
        path: '*',
        element: (
          <section>
            <h1>Página não encontrada</h1>
            <Link to="/">Voltar ao início</Link>
          </section>
        ),
      },
    ],
  },
]);
