import { PlanTier } from './types';
import { planPriceIds } from './constants';

export function getPriceIdForTier(tier: PlanTier): string | null {
  const value = planPriceIds[tier];
  if (typeof value === 'string' && value.length > 0) {
    return value;
  }
  return null;
}

export function normalizePlanNameToTier(name: string): PlanTier | null {
  const lower = name.trim().toLowerCase();
  if (lower === 'instap') return 'instap';
  if (lower === 'groei') return 'groei';
  if (lower === 'pro') return 'pro';
  if (lower === 'enterprise') return 'enterprise';
  return null;
}

/**
 * Resolve a tier by a Stripe price ID string.
 */
export function getTierByPriceId(priceId: string | null | undefined): PlanTier | null {
  if (!priceId) return null;
  const entries: Array<[PlanTier, string | undefined]> = [
    ['instap', planPriceIds.instap],
    ['groei', planPriceIds.groei],
    ['pro', planPriceIds.pro],
    ['enterprise', planPriceIds.enterprise],
  ];
  const match = entries.find(([, id]) => typeof id === 'string' && id === priceId);
  return match ? match[0] : null;
}
