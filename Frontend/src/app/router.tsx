import { Suspense } from 'react';
import { createBrowserRouter, Link as RouterLink } from 'react-router-dom';
import { Alert, Button, LinearProgress } from '@mui/material';
import { Layout } from './layout';
import type { ContentSlug } from '@/features/institutional/model/content';
import {
  Home,
  Content,
  Dashboard,
  Auth,
  Protected,
  Detail,
  Profile,
  Inspections,
  Samples,
  Devices,
  AdminPrisma,
} from './lazy_pages';
import { RouteError } from './components/RouteError';
import { AuthLayout } from './layouts/AuthLayout';
import { PrivateLayout } from './layouts/PrivateLayout';
const load = (node: React.ReactNode) => (
  <Suspense fallback={<LinearProgress aria-label="Carregando página" />}>
    {node}
  </Suspense>
);
export const router = createBrowserRouter([
  {
    path: 'admin/prisma',
    element: load(<AdminPrisma />),
    errorElement: <RouteError />,
  },
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
      {
        path: '*',
        element: (
          <Alert severity="info">
            Página não encontrada.{' '}
            <Button component={RouterLink} to="/">
              Voltar ao início
            </Button>
          </Alert>
        ),
      },
    ],
  },
  {
    element: <AuthLayout />,
    errorElement: <RouteError />,
    children: [
      { path: 'login', element: load(<Auth />) },
      { path: 'registrar', element: load(<Auth registering />) },
    ],
  },
  {
    element: load(<Protected />),
    errorElement: <RouteError />,
    children: [
      {
        element: <PrivateLayout />,
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
          { path: 'dashboard/dispositivos', element: load(<Devices />) },
        ],
      },
    ],
  },
]);
