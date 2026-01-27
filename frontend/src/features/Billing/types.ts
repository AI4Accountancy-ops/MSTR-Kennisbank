export type PlanTier = 'instap' | 'groei' | 'pro' | 'enterprise';

export interface PlanPriceIds {
  readonly instap?: string;
  readonly groei?: string;
  readonly pro?: string;
  readonly enterprise?: string;
}
