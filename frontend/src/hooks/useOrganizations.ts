import { useQuery } from '@tanstack/react-query';
import { organizationService } from '~/services/organizationService';

export const useOrganizations = (userId: string) => {
  return useQuery({
    queryKey: ['organizations', 'mine', userId],
    queryFn: () => organizationService.listMyOrganizations({ user_id: userId }),
    enabled: userId.length > 0,
    staleTime: 60_000,
    refetchOnMount: 'always',
  });
};
