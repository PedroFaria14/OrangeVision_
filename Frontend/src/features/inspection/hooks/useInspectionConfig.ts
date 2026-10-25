import { useQuery } from '@tanstack/react-query';
import { useSession } from '@/features/auth/hooks/useSession';
import { inspectionConfig } from '../api/inspections';

export function useInspectionConfig() {
  const { session } = useSession();
  return useQuery({
    queryKey: ['private', session?.user.id, 'inspections', 'config'],
    queryFn: ({ signal }) => inspectionConfig(signal),
    enabled: !!session,
    staleTime: 60000,
    retry: false,
  });
}
