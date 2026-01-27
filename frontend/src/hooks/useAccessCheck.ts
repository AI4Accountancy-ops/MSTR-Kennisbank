import { useQuery } from '@tanstack/react-query';
import { accessService, type AccessCheckResponse } from '~/services/accessService';

export function useAccessCheck(userId: string | null | undefined) {
  const enabled = typeof userId === 'string' && userId.length > 0;
  const query = useQuery<AccessCheckResponse>({
    queryKey: ['access', 'check', userId],
    queryFn: () => accessService.checkAccess({ user_id: userId as string }),
    enabled,
    staleTime: 30_000,
  });

  const hasAccess = query.data?.status === 'success' ? query.data.has_access : false;

  return {
    ...query,
    hasAccess,
  } as const;
}
