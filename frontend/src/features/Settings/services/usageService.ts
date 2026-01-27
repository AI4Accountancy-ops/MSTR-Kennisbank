import { getJson, postJson } from '~/services/http';
import {
  simulateNetworkDelay,
  usageFixture,
  perUserUsageFixture,
  thresholdSettingsFixture,
} from '../fixtures';
import type { UsageMetric, UserUsageData, UsagePeriod, ThresholdSettings } from '../types';

export const usageService = {
  async getUsage(): Promise<ReadonlyArray<UsageMetric>> {
    if (import.meta.env.DEV) {
      await simulateNetworkDelay();
      return usageFixture;
    }
    return getJson<UsageMetric[]>('/api/usage');
  },

  async getPerUserUsage(period: UsagePeriod): Promise<ReadonlyArray<UserUsageData>> {
    if (import.meta.env.DEV) {
      await simulateNetworkDelay();
      return perUserUsageFixture;
    }
    return getJson<UserUsageData[]>(`/api/usage/per-user?period=${period}`);
  },

  async getThresholdSettings(): Promise<ThresholdSettings> {
    if (import.meta.env.DEV) {
      await simulateNetworkDelay();
      return thresholdSettingsFixture;
    }
    return getJson<ThresholdSettings>('/api/usage/thresholds');
  },

  async updateThresholdSettings(thresholds: ThresholdSettings): Promise<ThresholdSettings> {
    if (import.meta.env.DEV) {
      await simulateNetworkDelay();
      return thresholds;
    }
    return postJson<ThresholdSettings, ThresholdSettings>('/api/usage/thresholds', thresholds);
  },
};

export type UsageService = typeof usageService;
