import { lazy } from 'react';

export const Home = lazy(() => import('@/features/institutional/HomePage'));
export const Content = lazy(
  () => import('@/features/institutional/ContentPage'),
);
export const Auth = lazy(() => import('@/features/auth/pages/AuthPage'));
export const Profile = lazy(() => import('@/features/auth/pages/ProfilePage'));
export const Dashboard = lazy(
  () => import('@/features/dashboard/pages/DashboardPage'),
);
export const Detail = lazy(
  () => import('@/features/dashboard/pages/AnalysisDetailPage'),
);
export const Inspections = lazy(
  () => import('@/features/inspection/pages/InspectionPage'),
);
export const Samples = lazy(() => import('@/features/samples/SamplesPage'));
