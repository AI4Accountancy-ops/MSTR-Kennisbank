import { useQuery } from '@tanstack/react-query';
import { getUsageSummary, type UsageSummary } from '~/services/organizationService';

export function useUsageSummary(userId: string | null | undefined, organizationId?: string) {
  const enabled = typeof userId === 'string' && userId.length > 0;
  const query = useQuery<UsageSummary>({
    queryKey: ['usage', organizationId ?? 'active', userId],
    queryFn: () => getUsageSummary({ user_id: userId as string, organization_id: organizationId }),
    enabled,
    staleTime: 30_000,
  });

  const monthlyPercent = (() => {
    const used = query.data?.monthly_used ?? 0;
    const quota = query.data?.monthly_quota ?? 0;
    if (quota <= 0) return 0;
    return Math.min(100, Math.round((used / quota) * 100));
  })();

  const dailyPercent = (() => {
    const used = query.data?.daily_used ?? 0;
    const quota = query.data?.daily_quota ?? 0;
    if (quota <= 0) return 0;
    return Math.min(100, Math.round((used / quota) * 100));
  })();

  return { ...query, monthlyPercent, dailyPercent } as const;
}

export type { UsageSummary };
