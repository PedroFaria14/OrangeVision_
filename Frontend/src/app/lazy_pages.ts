import { lazy } from 'react';

export const Home = lazy(
  () => import('@/features/institutional/pages/HomePage'),
);
export const Content = lazy(
  () => import('@/features/institutional/pages/ContentPage'),
);
export const Dashboard = lazy(
  () => import('@/features/dashboard/pages/DashboardPage'),
);
export const Auth = lazy(() => import('@/features/auth/pages/AuthPage'));
export const Protected = lazy(
  () => import('@/features/auth/components/ProtectedLayout'),
);
export const Detail = lazy(
  () => import('@/features/dashboard/pages/AnalysisDetailPage'),
);
export const Profile = lazy(() => import('@/features/auth/pages/ProfilePage'));
export const Inspections = lazy(
  () => import('@/features/inspection/pages/InspectionPage'),
);
export const Samples = lazy(() => import('@/features/samples/SamplesPage'));
export const Devices = lazy(
  () => import('@/features/devices/pages/DevicesPage'),
);
export const AdminPrisma = lazy(
  () => import('@/features/admin-prisma/AdminPrismaPage'),
);
