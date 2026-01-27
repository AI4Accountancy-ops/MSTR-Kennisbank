import { useQuery } from '@tanstack/react-query';

import { userService } from '../services/userService';

export function useCurrentUser() {
  return useQuery({
    queryKey: ['currentUser'],
    queryFn: userService.getCurrentUser,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}
