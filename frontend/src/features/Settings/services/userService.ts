import { getJson } from '~/services/http';

import { simulateNetworkDelay, userFixture } from '../fixtures';
import type { User } from '../types';

export const userService = {
  async getCurrentUser(): Promise<User> {
    if (import.meta.env.DEV) {
      await simulateNetworkDelay();
      return userFixture;
    }
    return getJson<User>('/api/user/current');
  },
};
